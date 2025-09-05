"""
Shared error-handling and I/O utilities to reduce repetition.

Provides:
- map_exceptions: context manager to translate exceptions
- db_transaction / async_db_transaction: commit/rollback wrappers
- send_ws: safe websocket send with standard disconnect handling
- publish_event: best-effort event bus publish
"""

from __future__ import annotations

import json
from collections.abc import Awaitable
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable

from sqlalchemy.exc import SQLAlchemyError

try:
    # Optional imports for typing/runtime where available
    from fastapi import WebSocket
    from starlette.websockets import WebSocketDisconnect
except Exception:  # pragma: no cover - typing/runtime convenience
    WebSocket = Any  # type: ignore
    WebSocketDisconnect = Exception  # type: ignore

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session
except Exception:  # pragma: no cover
    AsyncSession = Any  # type: ignore
    Session = Any  # type: ignore

try:
    from dotmac_shared.core.exceptions import (
        DatabaseError,
        ExternalServiceError,
        ServiceError,
        ValidationError,
    )
except Exception:  # pragma: no cover - fallback

    class DatabaseError(Exception):
        pass

    class ServiceError(Exception):
        pass

    class ExternalServiceError(Exception):
        pass

    class ValidationError(Exception):
        pass


@contextmanager
def map_exceptions(
    mapping: dict[type[BaseException], type[BaseException]],
    default: type[BaseException] | None = None,
    message: str | None = None,
):
    """Translate exceptions per mapping, optionally to a default type.

    Example:
        with map_exceptions({SQLAlchemyError: DatabaseError}):
            repo_call()
    """
    try:
        yield
    except BaseException as e:  # noqa: BLE001 - translation boundary
        for src, dst in mapping.items():
            if isinstance(e, src):
                raise dst(message or str(e)) from e
        if default is not None:
            raise default(message or str(e)) from e
        raise


@asynccontextmanager
async def async_db_transaction(session: AsyncSession):
    """Async DB transaction with rollback on error; maps SQLAlchemy errors to DatabaseError."""
    try:
        yield
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise DatabaseError(str(e)) from e
    except Exception:
        await session.rollback()
        raise


@contextmanager
def db_transaction(session: Session):
    """Sync DB transaction with rollback on error; maps SQLAlchemy errors to DatabaseError."""
    try:
        yield
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError(str(e)) from e
    except Exception:
        session.rollback()
        raise


async def send_ws(
    websocket: WebSocket,
    message: Any,
    *,
    on_disconnect: Callable[[WebSocket], Awaitable[None]] | None = None,
    logger: Any | None = None,
) -> bool:
    """Safely send a message over a WebSocket.

    - Accepts str or any JSON-serializable object.
    - Handles disconnects and unexpected errors; returns False if not sent.
    - Optionally invokes on_disconnect callback to cleanup.
    """
    try:
        text = message if isinstance(message, str) else json.dumps(message)
    except (TypeError, ValueError):
        if logger:
            logger.exception("Failed to serialize websocket message")
        return False

    try:
        await websocket.send_text(text)
        return True
    except (WebSocketDisconnect, RuntimeError, ConnectionResetError):
        if logger:
            logger.info("WebSocket disconnected; scheduling cleanup")
        if on_disconnect is not None:
            try:
                await on_disconnect(websocket)
            except Exception:  # pragma: no cover - best-effort cleanup
                if logger:
                    logger.info("WebSocket cleanup raised; ignoring")
        return False
    except Exception:  # noqa: BLE001 - treat unexpected send errors uniformly
        if logger:
            logger.exception("Unexpected error sending websocket message")
        if on_disconnect is not None:
            try:
                await on_disconnect(websocket)
            except Exception:  # pragma: no cover
                if logger:
                    logger.info("WebSocket cleanup raised; ignoring")
        return False


async def publish_event(bus: Any, event: Any, logger: Any | None = None) -> bool:
    """Publish an event to a bus, swallowing transient connectivity failures.

    Returns True if publish appears successful; False if a transport failure occurred.
    """
    try:
        await bus.publish(event)
        return True
    except (ConnectionError, TimeoutError, RuntimeError):
        if logger:
            logger.info("Event bus publish failed; continuing")
        return False
    except Exception:  # noqa: BLE001 - treat unknown transport errors uniformly
        if logger:
            logger.exception("Unexpected error during event publish")
        return False


def service_operation(service_name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for service-layer operations to normalize exceptions.

    Maps common infrastructure exceptions to domain-level ones so that upstream layers
    (routers, use-cases) can handle them uniformly via standard_exception_handler.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (ServiceError, ExternalServiceError, DatabaseError, ValidationError):
                raise
            except SQLAlchemyError as e:
                raise DatabaseError(str(e)) from e
            except (TimeoutError, ConnectionError) as e:
                raise ExternalServiceError(str(e), service_name=service_name) from e
            except Exception as e:  # noqa: BLE001 - final normalization layer
                raise ServiceError(str(e)) from e

        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ServiceError, ExternalServiceError, DatabaseError, ValidationError):
                raise
            except SQLAlchemyError as e:
                raise DatabaseError(str(e)) from e
            except (TimeoutError, ConnectionError) as e:
                raise ExternalServiceError(str(e), service_name=service_name) from e
            except Exception as e:  # noqa: BLE001 - final normalization layer
                raise ServiceError(str(e)) from e

        # Detect coroutine function reliably
        try:
            from inspect import iscoroutinefunction
        except Exception:  # pragma: no cover - fallback

            def iscoroutinefunction(f):
                return callable(f) and callable(getattr(f, "__await__", None))  # type: ignore

        return async_wrapper if iscoroutinefunction(func) else sync_wrapper

    return decorator


__all__ = [
    "map_exceptions",
    "async_db_transaction",
    "db_transaction",
    "send_ws",
    "publish_event",
    "service_operation",
]
