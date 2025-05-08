import logging
from abc import ABC, abstractmethod

from niagads.database.session.core import DatabaseSessionManager
from niagads.exceptions.core import AbstractMethodNotImplemented
from niagads.settings.core import CustomSettings
from sqlalchemy.ext.asyncio import AsyncSession

COMMIT_AFTER: int = 5000


class Settings(CustomSettings):
    DATABASE_URI: str


class AbstractDataLoader(ABC):
    def __init__(
        self,
        databaseUri: str = None,
        commit: bool = False,
        test: int = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        self.logger: logging.Logger = logging.getLogger(__name__)
        self._debug: bool = debug
        self._test: int = test
        self._verbose: bool = verbose
        self._commitAfter: int = COMMIT_AFTER
        self._commit: bool = commit
        self._databaseSessionManager = DatabaseSessionManager(
            databaseUri if databaseUri is not None else Settings.from_env().DATABASE_URI
        )

    async def close(self):
        # reset pool
        await self._databaseSessionManager.close()

    def get_db_session(self):
        return self._databaseSessionManager()  # callable yields a session

    def set_commit_after(self, limit: int):
        self._commit_after = limit

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
                session.commit()
            else:
                self.logger.info(f"ROLLED BACK: {nTransactions} {msg}")
                session.rollback()

    @abstractmethod
    def load(
        self,
    ):
        raise AbstractMethodNotImplemented(AbstractDataLoader.load.__qualname__)
