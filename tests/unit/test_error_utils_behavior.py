import asyncio
import json
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from dotmac_shared.core.error_utils import (
    async_db_transaction,
    db_transaction,
    publish_event,
    send_ws,
    service_operation,
)
from dotmac_shared.core.exceptions import DatabaseError, ExternalServiceError, ServiceError, ValidationError


class DummySession:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class DummyAsyncSession:
    def __init__(self) -> None:
        self.committed = 0
        self.rolled_back = 0

    async def commit(self) -> None:
        self.committed += 1

    async def rollback(self) -> None:
        self.rolled_back += 1


class DummyWebSocket:
    def __init__(self, side_effect: Exception | None = None) -> None:
        self._side_effect = side_effect
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        if self._side_effect is not None:
            raise self._side_effect
        self.sent.append(text)


class DummyLogger:
    def __init__(self) -> None:
        self.exceptions: list[str] = []
        self.infos: list[str] = []

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa: ANN001
        self.exceptions.append(msg)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa: ANN001
        self.infos.append(msg)


@pytest.mark.asyncio
async def test_send_ws_serialization_error_returns_false_and_logs() -> None:
    logger = DummyLogger()
    ws = DummyWebSocket()
    # sets are not JSON serializable
    ok = await send_ws(ws, {"a", "b"}, logger=logger)
    assert ok is False
    assert any("serialize" in m for m in logger.exceptions)


@pytest.mark.asyncio
async def test_send_ws_disconnect_triggers_cleanup_and_returns_false() -> None:
    logger = DummyLogger()
    ws = DummyWebSocket(side_effect=ConnectionResetError())

    cleanup_called: list[bool] = []

    async def cleanup(socket: Any) -> None:  # noqa: ANN001
        cleanup_called.append(True)

    ok = await send_ws(ws, {"hello": "world"}, on_disconnect=cleanup, logger=logger)
    assert ok is False
    assert cleanup_called == [True]
    assert any("disconnected" in m for m in logger.infos)


@pytest.mark.asyncio
async def test_send_ws_unexpected_error_logs_and_returns_false() -> None:
    logger = DummyLogger()
    ws = DummyWebSocket(side_effect=ValueError("boom"))

    ok = await send_ws(ws, {"k": "v"}, logger=logger)
    assert ok is False
    assert any("Unexpected error" in m for m in logger.exceptions)


@pytest.mark.asyncio
async def test_publish_event_transient_transport_errors_return_false() -> None:
    class Bus:
        def __init__(self, exc: Exception) -> None:
            self.exc = exc

        async def publish(self, event: Any) -> None:  # noqa: ANN001
            raise self.exc

    logger = DummyLogger()
    for exc in (ConnectionError(), TimeoutError(), RuntimeError()):
        ok = await publish_event(Bus(exc), {"e": 1}, logger=logger)
        assert ok is False
        assert any("publish failed" in m for m in logger.infos)


@pytest.mark.asyncio
async def test_publish_event_unexpected_error_logged_and_returns_false() -> None:
    class Bus:
        async def publish(self, event: Any) -> None:  # noqa: ANN001
            raise ValueError("weird")

    logger = DummyLogger()
    ok = await publish_event(Bus(), {"e": 2}, logger=logger)
    assert ok is False
    assert any("Unexpected error" in m for m in logger.exceptions)


def test_db_transaction_success_commits() -> None:
    session = DummySession()
    with db_transaction(session):
        pass
    assert session.committed == 1
    assert session.rolled_back == 0


def test_db_transaction_sqlalchemy_error_rolls_back_and_maps() -> None:
    session = DummySession()
    with pytest.raises(DatabaseError):
        with db_transaction(session):
            raise SQLAlchemyError("db broken")
    assert session.committed == 0
    assert session.rolled_back == 1


def test_db_transaction_other_error_rolls_back_and_reraises() -> None:
    session = DummySession()
    with pytest.raises(RuntimeError):
        with db_transaction(session):
            raise RuntimeError("boom")
    assert session.committed == 0
    assert session.rolled_back == 1


@pytest.mark.asyncio
async def test_async_db_transaction_success_commits() -> None:
    session = DummyAsyncSession()
    async with async_db_transaction(session):
        pass
    assert session.committed == 1
    assert session.rolled_back == 0


@pytest.mark.asyncio
async def test_async_db_transaction_sqlalchemy_error_rolls_back_and_maps() -> None:
    session = DummyAsyncSession()
    with pytest.raises(DatabaseError):
        async with async_db_transaction(session):
            raise SQLAlchemyError("db broke")
    assert session.committed == 0
    assert session.rolled_back == 1


@pytest.mark.asyncio
async def test_async_db_transaction_other_error_rolls_back_and_reraises() -> None:
    session = DummyAsyncSession()
    with pytest.raises(RuntimeError):
        async with async_db_transaction(session):
            raise RuntimeError("boom")
    assert session.committed == 0
    assert session.rolled_back == 1


def test_service_operation_sync_mappings() -> None:
    @service_operation("svc")
    def f(kind: str) -> None:
        if kind == "sql":
            raise SQLAlchemyError("sql")
        if kind == "timeout":
            raise TimeoutError("t")
        if kind == "conn":
            raise ConnectionError("c")
        if kind == "domain":
            raise ValidationError("bad")
        if kind == "ok":
            return None
        raise ValueError("other")

    with pytest.raises(DatabaseError):
        f("sql")
    with pytest.raises(ExternalServiceError):
        f("timeout")
    with pytest.raises(ExternalServiceError):
        f("conn")
    with pytest.raises(ValidationError):
        f("domain")
    assert f("ok") is None
    with pytest.raises(ServiceError):
        f("else")


@pytest.mark.asyncio
async def test_service_operation_async_mappings() -> None:
    @service_operation("svc")
    async def af(kind: str) -> None:
        if kind == "sql":
            raise SQLAlchemyError("sql")
        if kind == "timeout":
            raise TimeoutError("t")
        if kind == "conn":
            raise ConnectionError("c")
        if kind == "domain":
            raise ValidationError("bad")
        if kind == "ok":
            return None
        raise ValueError("other")

    with pytest.raises(DatabaseError):
        await af("sql")
    with pytest.raises(ExternalServiceError):
        await af("timeout")
    with pytest.raises(ExternalServiceError):
        await af("conn")
    with pytest.raises(ValidationError):
        await af("domain")
    assert await af("ok") is None
    with pytest.raises(ServiceError):
        await af("else")

