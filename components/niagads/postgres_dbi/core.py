"""
helper functions for postgres database connections and transaction
management
"""

import logging
from os import environ
from sys import exc_info

from abc import ABC, abstractmethod

from psycopg2 import DatabaseError, connect as db_connect
from psycopg2.extensions import QueryCanceledError
from psycopg2.extras import DictCursor, RealDictCursor
from psycopg2.pool import (
    SimpleConnectionPool,
    ThreadedConnectionPool as _ThreadedConnectionPool,
)
from threading import Semaphore

from configparser import ConfigParser as SafeConfigParser  # renamed in Python 3.2

from niagads.exceptions.core import IllegalArgumentError
from niagads.utils.sys import verify_path


def initialize_cursor(dbh, name: str = None, realDict=False, withhold=False):
    cursorFactory = RealDictCursor if realDict else None

    if name is None:
        return dbh.cursor(cursor_factory=cursorFactory)

    if name is not None and " " in name:
        raise ValueError("Invalid name " + name + " for cursor; no spaces allowed")

    return dbh.cursor(name=name, cursorFactory=cursorFactory, withhold=withhold)


def raise_pg_exception(err, returnError=False):
    """raise postgres exception"""

    # get details about the exception
    err_type, err_obj, traceback = exc_info()
    # get the line number when exception occured
    line_num = traceback.tb_lineno
    err = DatabaseError(" ".join((str(err), "on line number:", str(line_num))))
    if returnError:
        return err
    else:
        raise err


class ThreadedConnectionPool(_ThreadedConnectionPool):
    """
    adapted from https://stackoverflow.com/a/53437049
    to use semaphore blocking to limit connection attempts until
    one is available

    """

    def __init__(self, minconn, maxconn, *args, **kwargs):
        self.__semaphore = Semaphore(maxconn)
        self.__maxConnections = maxconn
        super().__init__(minconn, maxconn, *args, **kwargs)

    def getconn(self, *args, **kwargs):
        self.__semaphore.acquire()
        try:
            return super().getconn(*args, **kwargs)
        except:
            self.__semaphore.release()
            raise

    def putconn(self, *args, **kwargs):
        try:
            super().putconn(*args, **kwargs)
        finally:
            self.__semaphore.release()

    def closeall(self):
        try:
            super().closeall()
        finally:
            self.__semaphore = Semaphore(self.__maxConnections)


class AbstractDatabase(ABC):
    """
    abstract accessor for database connection info / provides database handler
    """

    def __init__(self, gus_config_file=None, connection_string=None):
        self.logger = logging.getLogger(__name__)
        self._dbh = None  # database handler (connection)
        self._URI = None
        self._user = None
        self._password = None
        self._pgpassword = (
            None  # placeholder for resetting PGPASSWORD environmental var
        )
        self._URIConfig = None
        self._connection_string = connection_string
        self._pool = None  # connection pool

        self._set_connection_string(gus_config_file, connection_string)

    @abstractmethod
    def connect(self, timeout=None):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass

    @abstractmethod
    def connected(self):
        pass

    @abstractmethod
    def close(self):
        pass

    def _set_connection_string(self, gus_config_file, connection_string):
        """initialize connection string"""
        if connection_string is not None:
            self._connection_string = connection_string
            # TODO: extract user, etc from connection string & set
        else:
            self._connection_string = self._parse_gus_config(gus_config_file)

    def _parse_gus_config(self, gus_config_file, set_member_variables=True, url=False):
        """
        parse gus config file for DB connection info and return connection string
        """
        if gus_config_file is None:
            if not environ.get("GUS_HOME"):
                raise IllegalArgumentError(
                    "GUS_HOME environmental variable not set; must provide full path to `gus.config` file or connection string to establish a database connection"
                )

            gus_config_file = environ["GUS_HOME"] + "/config/gus.config"

        if not verify_path(gus_config_file):
            raise FileNotFoundError(gus_config_file)

        config_parser = SafeConfigParser()
        with open(gus_config_file, "r") as fh:
            config_str = "[section]\n" + fh.read()
            config_parser.read_string(config_str)

        dsn = config_parser.get("section", "dbiDsn")
        user = config_parser.get("section", "databaseLogin")
        password = config_parser.get("section", "databasePassword")

        dsn = dsn.replace("dbi:Pg:", "")
        dsn = dsn.replace("DBI:Pg:", "")
        dsn_config = dict(param.split("=") for param in dsn.split(";"))

        if url:  # postgresql://[userspec:pwd@][host:port][/dbname][?paramspec]
            connection_string = "postgresql://" + user + ":" + password
            connection_string = (
                connection_string + "@" + dsn_config["host"]
                if "host" in dsn_config
                else "localhost"
            )
            connection_string = (
                connection_string + ":" + dsn_config["port"]
                if "port" in dsn_config
                else "5432"
            )
            connection_string = connection_string + "/" + dsn_config["dbname"]

        else:  # key-value pair form
            connection_string = "user='" + user + "'"
            connection_string = connection_string + " password='" + password + "'"
            connection_string = (
                connection_string + " dbname='" + dsn_config["dbname"] + "'"
            )
            if "host" in dsn_config:
                connection_string = (
                    connection_string + " host='" + dsn_config["host"] + "'"
                )
            if "port" in dsn_config:
                connection_string = (
                    connection_string + " port='" + dsn_config["port"] + "'"
                )

        if set_member_variables:
            self._URI = dsn
            self._user = user
            self._password = password
            self._URIConfig = dsn_config

        return connection_string

    def name(self):
        """
        return database name
        """
        return self._URIConfig["dbname"]

    def port(self):
        """
        return port
        """
        if "port" in self._URIConfig:
            return self._URIConfig["port"]
        else:
            return None

    def host(self):
        """
        return database server
        """
        if "host" in self._URIConfig:
            return self._URIConfig["host"]
        else:
            return None

    def connection(self):
        return self._dbh

    def dbh(self):
        return self._dbh

    def dsn(self):
        return self._URI

    def user(self):
        return self._user

    def connection_string(self):
        return self._connection_string

    @classmethod
    def connection_string_from_config(self, gusConfigFile=None, url=False):
        # have to pass 'self' b/c class is not instantiated when used
        # e.g., Database.connection_string_from_config()
        if self.__name__ == "AsyncDatabase" and not url:
            url = True  # connection string format must be a URL for asyncpg

        return self._parse_gus_config(
            self, gus_config_file=gusConfigFile, set_member_variables=False, url=url
        )

    def __exit__(self):
        self.close()


class Database(AbstractDatabase):
    """standard psycopg2 database connection"""

    def __init__(self, gus_config_file=None, connection_string=None):
        super().__init__(gus_config_file, connection_string)

    def pool(self):
        """
        get connection pool
        usage:
            see https://www.psycopg.org/docs/pool.html for more info on getconn and putconn
            db = Database()
            db.create_pool() # threaded=True for multithreading applications
            dbh = db.pool().getconn() # get a connection
            db.pool().putconn(dbh) # put away the connection
            db.pool().putconn(dbh, close=True) # close the connection
            namedDbh = db.pool().getconn(key="my-conn") # if named, using the key will retrieve the same connection
            db.pool().putconn(namedDbh, key="my-conn") # key needs to be consistent with .getconn call
            db.pool().closeall() # close all connections
        """
        return self._pool

    def create_pool(self, max_connections: int = 20, threaded=False):
        """
        create (if does not exist) and return connection pool

        Args:
            maxConnections (int, optional): maximum number of connections in the pool.  Defaults to 20.
            threaded (bool, optional): create threaded pool (for use in multi-threaded applications). Defaults to False.
        """
        if self._pool is not None:
            raise DatabaseError(
                "Connection Pool already exists; please close before creating a new pool"
            )

        if threaded:
            self._pool = ThreadedConnectionPool(
                1, max_connections, self._connection_string
            )
        else:
            self._pool = SimpleConnectionPool(
                1, max_connections, self._connection_string
            )

    def close_pool(self):
        self._pool.closeall()
        self._pool = None

    def close(self):
        """
        close the database connection
        """
        if self.connected():
            if self._pool is not None:
                self.close_pool()
            self._dbh.close()

    def cursor(self, cursorFactory=None):
        """
        create and return database cursor
        if dictCursor is True, return DictCursor
        """
        if cursorFactory == "DictCursor":
            return self._dbh.cursor(cursor_factory=DictCursor)
        if cursorFactory == "RealDictCursor":
            return self._dbh.cursor(cursor_factory=RealDictCursor)

        return self._dbh.cursor()

    def named_cursor(self, name, cursor_factory=None, withhold=True):
        """
        create and return database cursor
        if dictCursor is True, return DictCursor
        """
        if cursor_factory == "DictCursor":
            return self._dbh.cursor(
                name=name, cursor_factory=DictCursor, withhold=withhold
            )
        if cursor_factory == "RealDictCursor":
            return self._dbh.cursor(
                name=name, cursor_factory=RealDictCursor, withhold=withhold
            )

        return self._dbh.cursor(name=name, withhold=withhold)

    def set_session(self, readonly=None, autocommit=None):
        """
        wrapper for setting  one or more parameters for
        the next transactions or statements in the current session.
        pass 'DEFAULT' as the value to reset parameter to server default
        a value of None leaves the setting unchanged
        """
        self._dbh.set_session(readonly=readonly, autocommit=autocommit)

    def autocommit(self, status=True):
        """
        sets isolation level (auto-commit mode)
        autocommit must be on for transactions such as create database or vacuum
        default is FALSE
        """
        self._dbh.autocommit = status

    def set_pgpassword(self):
        """
        set PGPASSWORD environmental variable
        b/c postgres does not allow passwords through the command
        line to psql
        """
        if environ.get("PGPASSWORD"):
            self._pgpassword = environ["PGPASSWORD"]
        environ["PGPASSWORD"] = self._password

    def clear_pgpassword(self):
        self.reset_pgpassword()

    def reset_pgpassword(self):
        """
        set PGPASSWORD back to original value
        """
        if self._pgpassword is not None:
            environ["PGPASSWORD"] = self._pgpassword
        else:  # unset pgpassword environmental var
            del environ["PGPASSWORD"]

    def connect(self, timeout=None):
        """
        create database connection
        """
        if not self.connected():
            connectionString = self._connection_string
            if timeout is not None:
                connectionString += (
                    " options='-c statement_timeout=" + str(timeout) + "'"
                )
            self._dbh = db_connect(connectionString)

    def connected(self):
        """test the connection; returns true if handle is connected"""
        if self._dbh is None:
            return False

        return not bool(self._dbh.closed)

    def rollback(self):
        """
        rollback any changes
        """
        self._dbh.rollback()

    def commit(self):
        """
        commit any changes
        """
        self._dbh.commit()
