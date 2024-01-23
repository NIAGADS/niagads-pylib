"""
helper functions for postgres database connections and transaction
management
"""

import logging
import psycopg2
import psycopg2.extras 

from os import environ
from sys import exc_info

from psycopg2 import DatabaseError
from configparser import ConfigParser as SafeConfigParser # renamed in Python 3.2

from .exceptions import IllegalArgumentError
from .sys import verify_path


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


class Database(object):
    """
    accessor for database connection info / provides database handler
    """
    def __init__(self, gusConfigFile=None, connectionString=None):
        self.__dbh = None # database handler (connection)
        self.__dsn = None
        self.__user = None
        self.__password = None
        self.__pgpassword = None # placeholder for resetting PGPASSWORD environmental var
        self.__dsnConfig = None
        self.__connectionString = connectionString

        self.__initialize_database_config(gusConfigFile, connectionString)

        
    def __initialize_database_config(self, gusConfigFile, connectionString):
        if connectionString is not None:
            self.__connectionString = connectionString
            # TODO: extract user, etc from connection string & set
            return
        
        if gusConfigFile is None:
            if not environ.get('GUS_HOME'):
                raise IllegalArgumentError("GUS_HOME environmental variable not set; must provide full path to `gus.config` file or connection string to establish a database connection")
        
            gusConfigFile = environ['GUS_HOME'] + "/config/gus.config"
            
        if not verify_path(gusConfigFile):
            raise FileNotFoundError(gusConfigFile)
        
        self.load_database_config(gusConfigFile)
        
        
    def cursor(self, cursorFactory=None):
        """
        create and return database cursor
        if dictCursor is True, return DictCursor
        """
        if cursorFactory == 'DictCursor':
            return self.__dbh.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if cursorFactory == 'RealDictCursor':
            return self.__dbh.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        return self.__dbh.cursor()


    def named_cursor(self, name, cursorFactory=None, withhold=True):
        """
        create and return database cursor
        if dictCursor is True, return DictCursor
        """
        if cursorFactory == 'DictCursor':
            return self.__dbh.cursor(name=name,cursor_factory=psycopg2.extras.DictCursor, withhold=withhold)
        if cursorFactory == 'RealDictCursor':
            return self.__dbh.cursor(name=name,cursor_factory=psycopg2.extras.RealDictCursor, withhold=withhold)

        return self.__dbh.cursor(name=name, withhold=withhold)


    def set_session(self, readonly=None, autocommit=None):
        """
        wrapper for setting  one or more parameters for
        the next transactions or statements in the current session.
        pass 'DEFAULT' as the value to reset parameter to server default
        a value of None leaves the setting unchanged
        """
        self.__dbh.set_session(readonly=readonly, autocommit=autocommit)


    def autocommit(self, status=True):
        """
        sets isolation level (auto-commit mode)
        autocommit must be on for transactions such as create database or vacuum
        default is FALSE
        """
        self.__dbh.autocommit = status


    def set_pgpassword(self):
        """
        set PGPASSWORD environmental variable 
        b/c postgres does not allow passwords through the command
        line to psql
        """
        if environ.get('PGPASSWORD'):
            self.__pgpassword = environ['PGPASSWORD']
        environ['PGPASSWORD'] = self.__password

        
    def clear_pgpassword(self):
        self.reset_pgpassword()
        
        
    def reset_pgpassword(self):
        """
        set PGPASSWORD back to original value
        """
        if self.__pgpassword is not None:
            environ['PGPASSWORD'] = self.__pgpassword
        else: # unset pgpassword environmental var
            del environ['PGPASSWORD']
            

    def name(self):
        """
        return database name
        """
        return self.__dsnConfig['dbname']

    
    def port(self):
        """
        return port
        """
        if 'port' in self.__dsnConfig:
            return self.__dsnConfig['port']
        else:
            return None

    def host(self):
        """
        return database server
        """
        if 'host' in self.__dsnConfig:
            return self.__dsnConfig['host']
        else:
            return None


    def load_database_config(self, gusConfigFile):
        """
        parse gus config file for DB connection info
        """
        config_parser = SafeConfigParser()

        with open(gusConfigFile, 'r') as fh:
            config_string = '[section]\n' + fh.read()
            config_parser.read_string(config_string)

        self.__dsn = config_parser.get('section', 'dbiDsn')
        self.__user = config_parser.get('section', 'databaseLogin')
        self.__password = config_parser.get('section', 'databasePassword')

        self.__dsn = self.__dsn.replace('dbi:Pg:', '')
        self.__dsn = self.__dsn.replace('DBI:Pg:', '')
        self.__dsnConfig = dict(param.split("=") for param in self.__dsn.split(";"))
        
        self.__build_connection_string()


    def dbh(self):
        return self.__dbh
    
    def dsn(self):
        return self.__dsn
    
    def user(self):
        return self.__user


    def __build_connection_string(self):
        self.__connectionString = "user='" + self.__user + "'"
        self.__connectionString = self.__connectionString + " password='" + self.__password + "'"
        self.__connectionString = self.__connectionString + " dbname='" + self.__dsnConfig['dbname'] + "'"
        if 'host' in self.__dsnConfig:
            self.__connectionString = self.__connectionString + " host='" + self.__dsnConfig['host'] + "'"
        if 'port' in self.__dsnConfig:
            self.__connectionString = self.__connectionString + " port='" + self.__dsnConfig['port'] + "'"
            

    def connect(self):
        """
        create database connection
        """
        self.__dbh = psycopg2.connect(self.__connectionString)


    def connected(self):
        """ test the connection; returns true if handle is connected """
        return not bool(self.__dbh.closed)


    def close(self):
        """
        close the database connection
        """
        self.__dbh.close()


    def rollback(self):
        """
        rollback any changes
        """
        self.__dbh.rollback()


    def commit(self):
        """
        commit any changes
        """
        self.__dbh.commit()


