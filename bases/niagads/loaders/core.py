import logging
from abc import ABC, abstractmethod

from niagads.database.session.core import DatabaseSessionManager
from niagads.exceptions.core import AbstractMethodNotImplemented
from niagads.settings.core import CustomSettings
from niagads.utils.logging import FunctionContextAdapter
from sqlalchemy.ext.asyncio import AsyncSession

COMMIT_AFTER: int = 5000


class Settings(CustomSettings):
    DATABASE_URI: str


class AbstractDataLoader(ABC):
    def __init__(
        self,
        databaseUri: str = None,
        commit: bool = False,
        test: bool = False,
        debug: bool = False,
        verbose: bool = False,
    ):
        self.logger: logging.Logger = FunctionContextAdapter(
            logging.getLogger(__name__), {}
        )

        self._debug: bool = debug
        self._test: bool = test
        self._verbose: bool = verbose
        self._commitAfter: int = COMMIT_AFTER
        self._commit: bool = commit
        self._databaseSessionManager = DatabaseSessionManager(
            (
                databaseUri
                if databaseUri is not None
                else Settings.from_env().DATABASE_URI
            ),
            echo=self._debug,
        )

    async def close(self):
        # reset pool
        await self._databaseSessionManager.close()

    def get_db_session(self):
        return self._databaseSessionManager()  # callable yields a session

    def set_commit_after(self, limit: int):
        self._commitAfter = limit

    async def commit(
        self,
        session: AsyncSession,
        nTransactions: int,
        msg: str = "",
        residuals: bool = False,
    ):
        """Wrapper for ending transactions.

        Commits, rolls backs or continues depending on commitAfter limit and commit flag

        Args:
            session (AsyncSession): the database session; passed b/c may be a pooled connection
            nTransactions (int): current number of transactions
            msg (str, optional): log message qualier (e.g., record type). Defaults to "".
            residuals (bool, optional): flag indicating final commit; ignores `commitAfter` limit. Defaults to False.
        """
        if (nTransactions % self._commitAfter == 0) or residuals:
            if self._commit:
                self.logger.info(f"COMMITTED: {nTransactions} {msg}")
                await session.commit()
            else:
                self.logger.info(f"ROLLED BACK: {nTransactions} {msg}")
                await session.rollback()

    @abstractmethod
    def load(self):
        """function for executing the loader"""
        raise AbstractMethodNotImplemented(AbstractDataLoader.load.__qualname__)

    @abstractmethod
    def report_status(self):
        """function for summarizing load result / status"""
        raise AbstractMethodNotImplemented(
            AbstractDataLoader.report_status.__qualname__
        )

    @abstractmethod
    def report_config(self):
        """function for summarizing load result / status"""
        raise AbstractMethodNotImplemented(
            AbstractDataLoader.report_config.__qualname__
        )

    def log_section_header(self, label: str, **kwargs):
        # TODO: abstract  out into custom logger class
        self.logger.info("=" * 40, **kwargs)
        self.logger.info(label.center(40), **kwargs)
        self.logger.info("=" * 40, **kwargs)
