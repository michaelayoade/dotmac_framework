"""
Database transaction management with automatic rollback and retry logic.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Callable, Generator, Optional, TypeVar, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from ..types import DatabaseError, TransactionError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DatabaseTransaction:
    """
    Database transaction context manager for both sync and async operations.

    Provides automatic transaction management with rollback on errors,
    nested transaction support, and comprehensive error handling.
    """

    @staticmethod
    @contextmanager
    def sync_transaction(
        session: Optional[Session] = None,
        session_maker: Optional[sessionmaker] = None,
        auto_commit: bool = True,
    ) -> Generator[Session, None, None]:
        """
        Synchronous transaction context manager.

        Args:
            session: Existing session to use
            session_maker: Session factory if no session provided
            auto_commit: Whether to auto-commit on success

        Yields:
            Database session with transaction management

        Raises:
            TransactionError: If transaction fails
        """
        if session is None:
            if session_maker is None:
                raise TransactionError(
                    "Either session or session_maker must be provided"
                )
            session = session_maker()
            should_close = True
        else:
            should_close = False

        try:
            if auto_commit and not session.in_transaction():
                session.begin()

            yield session

            if auto_commit and session.in_transaction():
                session.commit()
                logger.debug("Transaction committed successfully")

        except SQLAlchemyError as e:
            if session.in_transaction():
                session.rollback()
                logger.error(
                    f"Database transaction rolled back due to SQLAlchemy error: {e}"
                )
            raise TransactionError(f"Database transaction failed: {e}") from e

        except Exception as e:
            if session.in_transaction():
                session.rollback()
                logger.error(
                    f"Database transaction rolled back due to unexpected error: {e}"
                )
            raise TransactionError(
                f"Transaction failed with unexpected error: {e}"
            ) from e

        finally:
            if should_close:
                session.close()

    @staticmethod
    @asynccontextmanager
    async def async_transaction(
        session: Optional[AsyncSession] = None,
        session_maker: Optional[async_sessionmaker] = None,
        auto_commit: bool = True,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Asynchronous transaction context manager.

        Args:
            session: Existing async session to use
            session_maker: Async session factory if no session provided
            auto_commit: Whether to auto-commit on success

        Yields:
            Async database session with transaction management

        Raises:
            TransactionError: If transaction fails
        """
        if session is None:
            if session_maker is None:
                raise TransactionError(
                    "Either session or session_maker must be provided"
                )
            session = session_maker()
            should_close = True
        else:
            should_close = False

        try:
            if auto_commit and not session.in_transaction():
                await session.begin()

            yield session

            if auto_commit and session.in_transaction():
                await session.commit()
                logger.debug("Async transaction committed successfully")

        except SQLAlchemyError as e:
            if session.in_transaction():
                await session.rollback()
                logger.error(
                    f"Async database transaction rolled back due to SQLAlchemy error: {e}"
                )
            raise TransactionError(f"Async database transaction failed: {e}") from e

        except Exception as e:
            if session.in_transaction():
                await session.rollback()
                logger.error(
                    f"Async database transaction rolled back due to unexpected error: {e}"
                )
            raise TransactionError(
                f"Async transaction failed with unexpected error: {e}"
            ) from e

        finally:
            if should_close:
                await session.close()


class TransactionManager:
    """
    Advanced transaction manager with retry policies and nested transaction support.
    """

    def __init__(
        self,
        session_maker: Optional[Union[sessionmaker, async_sessionmaker]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize transaction manager.

        Args:
            session_maker: Session factory for creating new sessions
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            backoff_multiplier: Backoff multiplier for exponential backoff
        """
        self.session_maker = session_maker
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_multiplier = backoff_multiplier

    @contextmanager
    def transaction(
        self,
        session: Optional[Session] = None,
        auto_commit: bool = True,
        retry_on_failure: bool = False,
    ) -> Generator[Session, None, None]:
        """
        Create a synchronous transaction with optional retry logic.

        Args:
            session: Existing session to use
            auto_commit: Whether to auto-commit on success
            retry_on_failure: Whether to retry on transaction failures

        Yields:
            Database session with transaction management
        """
        if retry_on_failure:
            yield from self._transaction_with_retry(
                session, auto_commit, is_async=False
            )
        else:
            with DatabaseTransaction.sync_transaction(
                session=session,
                session_maker=self.session_maker,
                auto_commit=auto_commit,
            ) as db_session:
                yield db_session

    @asynccontextmanager
    async def async_transaction(
        self,
        session: Optional[AsyncSession] = None,
        auto_commit: bool = True,
        retry_on_failure: bool = False,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Create an asynchronous transaction with optional retry logic.

        Args:
            session: Existing async session to use
            auto_commit: Whether to auto-commit on success
            retry_on_failure: Whether to retry on transaction failures

        Yields:
            Async database session with transaction management
        """
        if retry_on_failure:
            async for db_session in self._async_transaction_with_retry(
                session, auto_commit
            ):
                yield db_session
        else:
            async with DatabaseTransaction.async_transaction(
                session=session,
                session_maker=self.session_maker,
                auto_commit=auto_commit,
            ) as db_session:
                yield db_session

    def execute_with_retry(
        self,
        operation: Callable[[Session], T],
        session: Optional[Session] = None,
    ) -> T:
        """
        Execute operation with retry logic (synchronous).

        Args:
            operation: Function that takes a session and returns a result
            session: Optional existing session

        Returns:
            Operation result

        Raises:
            TransactionError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                with self.transaction(
                    session=session, retry_on_failure=False
                ) as db_session:
                    return operation(db_session)

            except (SQLAlchemyError, TransactionError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(
                        f"Operation failed after {self.max_retries} retries: {e}"
                    )
                    break

                delay = self.retry_delay * (self.backoff_multiplier**attempt)
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                import time

                time.sleep(delay)

        raise TransactionError(
            f"Operation failed after {self.max_retries} retries"
        ) from last_exception

    async def async_execute_with_retry(
        self,
        operation: Callable[[AsyncSession], T],
        session: Optional[AsyncSession] = None,
    ) -> T:
        """
        Execute operation with retry logic (asynchronous).

        Args:
            operation: Async function that takes a session and returns a result
            session: Optional existing async session

        Returns:
            Operation result

        Raises:
            TransactionError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                async with self.async_transaction(
                    session=session, retry_on_failure=False
                ) as db_session:
                    return await operation(db_session)

            except (SQLAlchemyError, TransactionError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(
                        f"Async operation failed after {self.max_retries} retries: {e}"
                    )
                    break

                delay = self.retry_delay * (self.backoff_multiplier**attempt)
                logger.warning(
                    f"Async operation failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

        raise TransactionError(
            f"Async operation failed after {self.max_retries} retries"
        ) from last_exception

    def _transaction_with_retry(
        self,
        session: Optional[Session],
        auto_commit: bool,
        is_async: bool = False,
    ) -> Generator[Session, None, None]:
        """
        Internal method for transaction with retry logic (sync).
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                with DatabaseTransaction.sync_transaction(
                    session=session,
                    session_maker=self.session_maker,
                    auto_commit=auto_commit,
                ) as db_session:
                    yield db_session
                    return  # Success, exit retry loop

            except (SQLAlchemyError, TransactionError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(
                        f"Transaction failed after {self.max_retries} retries: {e}"
                    )
                    break

                delay = self.retry_delay * (self.backoff_multiplier**attempt)
                logger.warning(
                    f"Transaction failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                import time

                from dotmac_shared.api.exception_handlers import (
                    standard_exception_handler,
                )

                time.sleep(delay)

        raise TransactionError(
            f"Transaction failed after {self.max_retries} retries"
        ) from last_exception

    async def _async_transaction_with_retry(
        self,
        session: Optional[AsyncSession],
        auto_commit: bool,
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Internal method for async transaction with retry logic.
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                async with DatabaseTransaction.async_transaction(
                    session=session,
                    session_maker=self.session_maker,
                    auto_commit=auto_commit,
                ) as db_session:
                    yield db_session
                    return  # Success, exit retry loop

            except (SQLAlchemyError, TransactionError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(
                        f"Async transaction failed after {self.max_retries} retries: {e}"
                    )
                    break

                delay = self.retry_delay * (self.backoff_multiplier**attempt)
                logger.warning(
                    f"Async transaction failed (attempt {attempt + 1}/{self.max_retries + 1}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

        raise TransactionError(
            f"Async transaction failed after {self.max_retries} retries"
        ) from last_exception
