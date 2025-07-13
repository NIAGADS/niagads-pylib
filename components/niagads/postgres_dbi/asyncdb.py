"""
helper functions for postgres database connections and transaction
management
"""

import logging

import json
from asyncpg import connect
from niagads.postgres_dbi.core import AbstractDatabase


class AsyncDatabase(AbstractDatabase):
    def __init__(self, gusConfigFile=None, connectionString=None):
        super().__init__(gusConfigFile, connectionString)

    async def __set_jsonb_codec(self):
        await self._dbh.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )

    async def connect(self):
        """
        create database connection
        """
        if not self.connected():
            self._dbh = await connect(self._connection_string)
            await self.__set_jsonb_codec()

    async def close(self):
        """
        close the database connection
        """
        if self.connected():
            # if self._pool is not None:
            #    self.close_pool()
            await self._dbh.close()

    def connected(self):
        """test the connection; returns true if handle is connected"""
        if self._dbh is None:
            return False

        return not bool(self._dbh.is_closed())

    def commit(self):
        # not yet implemented; requires transactions, not just connections
        raise NotImplementedError()

    def rollback(self):
        # not yet implemented; requires transactions, not just connections
        raise NotImplementedError()
