"""Serialized direct-action UDP transport with acknowledgement validation."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from .const import ACK_TIMEOUT_SECONDS
from .transaction import ACTION_ACK, direct_action_datagrams

_LOGGER = logging.getLogger(__name__)


class ControllerTimeoutError(TimeoutError):
    """Raised when the controller does not acknowledge an action."""


class _Protocol(asyncio.DatagramProtocol):
    """Datagram protocol that queues inbound controller messages."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.messages: asyncio.Queue[bytes] = asyncio.Queue()
        self.error: Exception | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, _addr: tuple[str, int]) -> None:
        self.messages.put_nowait(data)

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

    async def async_send_action(self, frame: bytes, action_name: str) -> None:
        """Send one observed direct action and require its ACK3 acknowledgement.

        The original pilot prepended an unverified ``LOGICDATAOPEN`` datagram and
        waited 500 ms before the action. Recent iPad captures instead show a
        direct nine-byte action followed by ``ACK3``. Do not add a preamble,
        delayed retry, or release frame here unless separately validated.
        """
        if self._transport is None or self._protocol is None:
            raise ControllerTimeoutError("Controller transport is not initialized")
        async with self._lock:
            self._drain_messages()
            try:
                datagrams = direct_action_datagrams(frame)
            except ValueError as err:
                raise ControllerTimeoutError(str(err)) from err
            for datagram in datagrams:
                await self._async_send_and_wait(datagram, ACTION_ACK, action_name)

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
        _LOGGER.debug("Sending direct controller action %s (%d bytes)", action_name, len(frame))
        self._transport.sendto(frame)
        deadline = started + ACK_TIMEOUT_SECONDS
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                _LOGGER.warning("Controller action %s timed out waiting for ACK3", action_name)
                raise ControllerTimeoutError("Controller acknowledgement timed out")
            try:
                response = await asyncio.wait_for(self._protocol.messages.get(), remaining)
            except TimeoutError as err:
                _LOGGER.warning("Controller action %s timed out waiting for ACK3", action_name)
                raise ControllerTimeoutError("Controller acknowledgement timed out") from err
            if response.startswith(expected):
                _LOGGER.debug(
                    "Controller action %s acknowledged in %.1f ms",
                    action_name,
                    (loop.time() - started) * 1000,
                )
                return
            _LOGGER.debug(
                "Ignoring unexpected controller response while waiting for %s: %r",
                action_name,
                response[:4],
            )
