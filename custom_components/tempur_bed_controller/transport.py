"""Serialized UDP transport with acknowledgement validation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from .const import ACK_ACTION, ACK_OPEN, ACK_TIMEOUT_SECONDS, ACTION_DELAY_SECONDS, OPEN_FRAME


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

    async def async_send_action(self, frame: bytes) -> None:
        """Open a session, wait for acknowledgement, then send one action."""
        if self._transport is None or self._protocol is None:
            raise ControllerTimeoutError("Controller transport is not initialized")

        async with self._lock:
            self._drain_messages()
            await self._async_send_and_wait(OPEN_FRAME, ACK_OPEN)
            await asyncio.sleep(ACTION_DELAY_SECONDS)
            await self._async_send_and_wait(frame, ACK_ACTION)

    def _drain_messages(self) -> None:
        assert self._protocol is not None
        while not self._protocol.messages.empty():
            self._protocol.messages.get_nowait()

    async def _async_send_and_wait(self, frame: bytes, expected: bytes) -> None:
        assert self._transport is not None
        assert self._protocol is not None
        if self._protocol.error is not None:
            error = self._protocol.error
            self._protocol.error = None
            raise ControllerTimeoutError(f"UDP transport error: {error}")

        self._transport.sendto(frame)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + ACK_TIMEOUT_SECONDS
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise ControllerTimeoutError("Controller acknowledgement timed out")
            try:
                response = await asyncio.wait_for(self._protocol.messages.get(), remaining)
            except TimeoutError as err:
                raise ControllerTimeoutError("Controller acknowledgement timed out") from err
            if response.startswith(expected):
                return
