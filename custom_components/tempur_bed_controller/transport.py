"""Serialized direct-action UDP transport with acknowledgement validation."""

from __future__ import annotations

import asyncio
import logging

from .const import (
    ACK_ACTION,
    ACK_OPEN,
    ACK_TIMEOUT_SECONDS,
    OPEN_FRAME,
    SESSION_ACTION_SETTLE_SECONDS,
)
from .transaction import (
    acknowledgement_matches,
    controller_source_matches,
    direct_action_datagrams,
    REPEATED_ACTION_INTERVAL_SECONDS,
    session_requires_reopen,
)

_LOGGER = logging.getLogger(__name__)


class ControllerTimeoutError(TimeoutError):
    """Raised when the controller does not acknowledge an action."""


class _Protocol(asyncio.DatagramProtocol):
    """Datagram protocol that queues inbound controller messages."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.messages: asyncio.Queue[tuple[bytes, tuple[str, int]]] = asyncio.Queue()
        self.error: Exception | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.messages.put_nowait((data, addr))

    def error_received(self, exc: Exception) -> None:
        self.error = exc


class ControllerTransport:
    """Send one complete controller action at a time."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._protocol: _Protocol | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._lock = asyncio.Lock()
        self._session_open = False
        self._last_action_ack_monotonic: float | None = None

    async def async_setup(self) -> None:
        """Create the local UDP endpoint without issuing a controller command."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            _Protocol,
            remote_addr=(self._host, self._port),
        )
        self._transport = transport
        self._protocol = protocol

    async def async_close(self) -> None:
        """Close the local UDP endpoint."""
        if self._transport is not None:
            self._transport.close()
        self._transport = None
        self._protocol = None
        self._session_open = False
        self._last_action_ack_monotonic = None

    async def async_send_action(self, frame: bytes, action_name: str) -> None:
        """Open one controller session, then send one captured direct action.

        Captures show a ``FELOGICDATAOPEN`` datagram acknowledged by ``ACKFE``
        before later direct actions. The opener is sent once per HA transport
        lifetime, never before every action. The captured iPad interval from
        ``ACKFE`` to the first action was 4.6-7.0 ms, so this integration waits
        10 ms. After every acknowledged physical action, Home Assistant holds
        its action queue for 500 ms before allowing the next explicit action.
        This does not synthesize repeats.
        """
        if self._transport is None or self._protocol is None:
            raise ControllerTimeoutError("Controller transport is not initialized")
        async with self._lock:
            self._drain_messages()
            try:
                datagrams = direct_action_datagrams(frame)
            except ValueError as err:
                raise ControllerTimeoutError(str(err)) from err
            loop = asyncio.get_running_loop()
            last_action_ack = self._last_action_ack_monotonic
            if self._session_open and session_requires_reopen(last_action_ack, loop.time()):
                assert last_action_ack is not None
                _LOGGER.debug(
                    "Controller session idle for %.1f seconds; reopening before action=%s",
                    loop.time() - last_action_ack,
                    action_name,
                )
                self._session_open = False
                self._last_action_ack_monotonic = None
            if not self._session_open:
                await self._async_open_session()
            for datagram in datagrams:
                try:
                    await self._async_send_and_wait(datagram, ACK_ACTION, action_name)
                except ControllerTimeoutError:
                    self._session_open = False
                    self._last_action_ack_monotonic = None
                    raise
                self._last_action_ack_monotonic = loop.time()
                _LOGGER.debug(
                    "Controller action=%s acknowledged; holding queue for %.0f ms",
                    action_name,
                    REPEATED_ACTION_INTERVAL_SECONDS * 1000,
                )
                await asyncio.sleep(REPEATED_ACTION_INTERVAL_SECONDS)

    async def async_reinitialize_session(self) -> None:
        """Safely re-open the controller session without sending a bed action."""
        if self._transport is None or self._protocol is None:
            raise ControllerTimeoutError("Controller transport is not initialized")
        async with self._lock:
            self._session_open = False
            self._last_action_ack_monotonic = None
            self._drain_messages()
            await self._async_open_session()

    async def _async_open_session(self) -> None:
        """Send the one-shot opener and wait for its acknowledgement."""
        self._session_open = False
        await self._async_send_and_wait(OPEN_FRAME, ACK_OPEN, "session_open")
        self._session_open = True
        _LOGGER.debug(
            "Controller session acknowledged; waiting %.1f ms before first action",
            SESSION_ACTION_SETTLE_SECONDS * 1000,
        )
        await asyncio.sleep(SESSION_ACTION_SETTLE_SECONDS)

    def _drain_messages(self) -> None:
        assert self._protocol is not None
        while not self._protocol.messages.empty():
            self._protocol.messages.get_nowait()

    async def _async_send_and_wait(self, frame: bytes, expected: bytes, action_name: str) -> None:
        assert self._transport is not None
        assert self._protocol is not None
        if self._protocol.error is not None:
            error = self._protocol.error
            self._protocol.error = None
            raise ControllerTimeoutError(f"UDP transport error: {error}")

        loop = asyncio.get_running_loop()
        started = loop.time()
        _LOGGER.debug(
            "Sending controller datagram action=%s length=%d payload=%s",
            action_name,
            len(frame),
            frame.hex(),
        )
        self._transport.sendto(frame)
        deadline = started + ACK_TIMEOUT_SECONDS
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                _LOGGER.warning(
                    "Controller datagram action=%s timed out waiting for %s",
                    action_name,
                    expected.hex(),
                )
                raise ControllerTimeoutError(
                    f"Controller acknowledgement timed out waiting for {expected.decode(errors='replace')}"
                )
            try:
                response, addr = await asyncio.wait_for(self._protocol.messages.get(), remaining)
            except TimeoutError as err:
                _LOGGER.warning(
                    "Controller datagram action=%s timed out waiting for %s",
                    action_name,
                    expected.hex(),
                )
                raise ControllerTimeoutError(
                    f"Controller acknowledgement timed out waiting for {expected.decode(errors='replace')}"
                ) from err
            if not controller_source_matches(self._host, self._port, addr):
                _LOGGER.debug(
                    "Ignoring response from unexpected source action=%s source=%s:%d",
                    action_name,
                    addr[0],
                    addr[1],
                )
                continue
            if acknowledgement_matches(response, expected):
                _LOGGER.debug(
                    "Controller datagram action=%s acknowledged in %.1f ms response=%s source_port=%d",
                    action_name,
                    (loop.time() - started) * 1000,
                    response.hex(),
                    addr[1],
                )
                return
            _LOGGER.debug(
                "Ignoring unexpected controller response action=%s expected=%s received=%s source_port=%d",
                action_name,
                expected.hex(),
                response.hex(),
                addr[1],
            )

    def _is_controller_source(self, addr: tuple[str, int]) -> bool:
        """Accept only responses from the configured controller endpoint."""
        if addr[1] != self._port:
            return False
        try:
            return ip_address(addr[0]) == ip_address(self._host)
        except ValueError:
            # A hostname may resolve to an address whose text differs from the
            # configured name. The connected UDP endpoint still restricts the
            # peer; validate the port here and let the socket enforce the host.
            return True
