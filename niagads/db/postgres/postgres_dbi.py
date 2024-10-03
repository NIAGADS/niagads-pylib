"""
helper functions for postgres database connections and transaction
management
"""

import logging
from os import environ
from sys import exc_info

from abc import ABC, abstractmethod

from psycopg2 import DatabaseError, DataError, connect as db_connect
from psycopg2.extensions import QueryCanceledError
from psycopg2.extras import DictCursor, RealDictCursor
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool as _ThreadedConnectionPool
from threading import Semaphore


from configparser import ConfigParser as SafeConfigParser # renamed in Python 3.2

from ...utils.exceptions import IllegalArgumentError, AbstractMethodNotImplemented
from ...utils.sys import verify_path


def initialize_cursor(dbh, name: str = None, realDict=False, withhold=False):    
        cursorFactory = RealDictCursor if realDict else None
        
        if name is None:
            return dbh.cursor(cursor_factory=cursorFactory)
            
        if name is not None and ' ' in name:
            raise ValueError("Invalid name " + name + " for cursor; no spaces allowed")
        
        return dbh.cursor(name=name, cursorFactory=cursorFactory, withhold=withhold)


def raise_pg_exception(err, returnError=False):
    """ raise postgres exception """

    # get details about the exception
    err_type, err_obj, traceback = exc_info()
    # get the line number when exception occured
    line_num = traceback.tb_lineno
    err = DatabaseError(' '.join((str(err), "on line number:", str(line_num))))
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
    def __init__(self, gusConfigFile=None, connectionString=None):
        self.logger = logging.getLogger(__name__)
        self._dbh = None # database handler (connection)
        self._dsn = None
        self._user = None
        self._password = None
        self._pgpassword = None # placeholder for resetting PGPASSWORD environmental var
        self._dsnConfig = None
        self._connectionString = connectionString
        self._pool = None # connection pool

        self._set_connection_string(gusConfigFile, connectionString)

    @abstractmethod
    def connect(self, timeout=None):
        raise AbstractMethodNotImplemented(AbstractDatabase.connect.__qualname__)
        
    @abstractmethod
    def commit(self):
        raise AbstractMethodNotImplemented(AbstractDatabase.commit.__qualname__)
    
    @abstractmethod
    def rollback(self):
        raise AbstractMethodNotImplemented(AbstractDatabase.rollback.__qualname__)

    @abstractmethod
    def connected(self):
        raise AbstractMethodNotImplemented(AbstractDatabase.connected.__qualname__)
    
    @abstractmethod
    def close(self):
        raise AbstractMethodNotImplemented(AbstractDatabase.close.__qualname__)        

    def _set_connection_string(self, gusConfigFile, connectionString):
        """ initialize connection string """
        if connectionString is not None:
            self._connectionString = connectionString
            # TODO: extract user, etc from connection string & set
        else:     
            self._connectionString = self._parse_gus_config(gusConfigFile)
        
        
    def _parse_gus_config(self, gusConfigFile, setMemberVariables=True, url=False):
        """
        parse gus config file for DB connection info and return connection string
        """
        if gusConfigFile is None:
            if not environ.get('GUS_HOME'):
                raise IllegalArgumentError("GUS_HOME environmental variable not set; must provide full path to `gus.config` file or connection string to establish a database connection")
        
            gusConfigFile = environ['GUS_HOME'] + "/config/gus.config"
            
        if not verify_path(gusConfigFile):
            raise FileNotFoundError(gusConfigFile)
        
        configParser = SafeConfigParser()
        with open(gusConfigFile, 'r') as fh:
            configString = '[section]\n' + fh.read()
            configParser.read_string(configString)

        dsn = configParser.get('section', 'dbiDsn')
        user = configParser.get('section', 'databaseLogin')
        password = configParser.get('section', 'databasePassword')

        dsn = dsn.replace('dbi:Pg:', '')
        dsn = dsn.replace('DBI:Pg:', '')
        dsnConfig = dict(param.split("=") for param in dsn.split(";"))
        
        if url: # postgresql://[userspec:pwd@][host:port][/dbname][?paramspec]
            connectionString = "postgresql://" + user + ':' + password
            connectionString = connectionString + '@' + dsnConfig['host'] if 'host' in dsnConfig else 'localhost' 
            connectionString = connectionString + ':' + dsnConfig['port'] if 'port' in dsnConfig else '5432'
            connectionString = connectionString + '/' + dsnConfig['dbname']
            
        else: # key-value pair form 
            connectionString = "user='" + user + "'"
            connectionString = connectionString + " password='" + password + "'"
            connectionString = connectionString + " dbname='" + dsnConfig['dbname'] + "'"
            if 'host' in dsnConfig:
                connectionString = connectionString + " host='" + dsnConfig['host'] + "'"
            if 'port' in dsnConfig:
                connectionString = connectionString + " port='" + dsnConfig['port'] + "'"
        
        if setMemberVariables:
            self._dsn = dsn
            self._user = user
            self._password = password
            self._dsnConfig = dsnConfig
            
        return connectionString
            
        
    def name(self):
        """
        return database name
        """
        return self._dsnConfig['dbname']


    def port(self):
        """
        return port
        """
        if 'port' in self._dsnConfig:
            return self._dsnConfig['port']
        else:
            return None

    def host(self):
        """
        return database server
        """
        if 'host' in self._dsnConfig:
            return self._dsnConfig['host']
        else:
            return None    
    
    def connection(self):
        return self._dbh
    
    def dbh(self):
        return self._dbh
    
    def dsn(self):
        return self._dsn
    
    def user(self):
        return self._user
     
    def connection_string(self):
        return self._connectionString
    

    @classmethod
    def connection_string_from_config(self, gusConfigFile=None, url=False):
        # have to pass 'self' b/c class is not instantiated when used
        # e.g., Database.connection_string_from_config()
        if self.__name__ == 'AsyncDatabase' and not url:    
            url = True # connection string format must be a URL for asyncpg
            
        return self._parse_gus_config(self, gusConfigFile=gusConfigFile, setMemberVariables=False, url=url)
        
    
    def __exit__(self):
        self.close()
        
        
class Database(AbstractDatabase):
    """ standard psycopg2 database connection """
    def __init__(self, gusConfigFile=None, connectionString=None):
        super().__init__(gusConfigFile, connectionString)
    
    
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


    def create_pool(self, maxConnections:int=20, threaded=False):
        """
        create (if does not exist) and return connection pool

        Args:
            maxConnections (int, optional): maximum number of connections in the pool.  Defaults to 20.
            threaded (bool, optional): create threaded pool (for use in multi-threaded applications). Defaults to False.
        """
        if self._pool is not None:
            raise DatabaseError("Connection Pool already exists; please close before creating a new pool")
        
        if threaded:
            self._pool = ThreadedConnectionPool(1, maxConnections, self._connectionString)
        else:
            self._pool = SimpleConnectionPool(1, maxConnections, self._connectionString)

                
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
        if cursorFactory == 'DictCursor':
            return self._dbh.cursor(cursor_factory=DictCursor)
        if cursorFactory == 'RealDictCursor':
            return self._dbh.cursor(cursor_factory=RealDictCursor)

        return self._dbh.cursor()


    def named_cursor(self, name, cursorFactory=None, withhold=True):
        """
        create and return database cursor
        if dictCursor is True, return DictCursor
        """
        if cursorFactory == 'DictCursor':
            return self._dbh.cursor(name=name,cursor_factory=DictCursor, withhold=withhold)
        if cursorFactory == 'RealDictCursor':
            return self._dbh.cursor(name=name,cursor_factory=RealDictCursor, withhold=withhold)

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
        if environ.get('PGPASSWORD'):
            self._pgpassword = environ['PGPASSWORD']
        environ['PGPASSWORD'] = self._password

        
    def clear_pgpassword(self):
        self.reset_pgpassword()
        
        
    def reset_pgpassword(self):
        """
        set PGPASSWORD back to original value
        """
        if self._pgpassword is not None:
            environ['PGPASSWORD'] = self._pgpassword
        else: # unset pgpassword environmental var
            del environ['PGPASSWORD']
            

    def connect(self, timeout=None):
        """
        create database connection
        """
        if not self.connected():
            connectionString = self._connectionString
            if timeout is not None:
                connectionString += " options='-c statement_timeout=" + str(timeout) + "'"
            self._dbh = db_connect(connectionString)

    def connected(self):
        """ test the connection; returns true if handle is connected """
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


