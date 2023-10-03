import logging
import time
from .exceptions import TimerError

class ExitOnExceptionHandler(logging.FileHandler):
    """
    logging exception handler that catches ERRORS and CRITICAL
    level logging and exits 
    see https://stackoverflow.com/a/48201163
    """
    def emit(self, record):
        super().emit(record)
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            raise SystemExit(-1)
        
        

class Timer:
    """class for a system timer; modified from
    modified from https://realpython.com/python-timer/#a-python-timer-class
    """
    def __init__(self):
        self.__startTime = None

    def time(self, asStr=True):
        """report elapsed time
        """
        elapsedTime = time.perf_counter() - self.__startTime
        return "{elapsedTime:0.4f} seconds" if asStr else elapsedTime


    def start(self):
        """start the timer

        Raises:
            TimerError: raise if timer is running
        """
        if self.__startTime is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it")
        self.__startTime = time.perf_counter()
        
        
    def stop(self):
        """Stop the timer, and report the elapsed time"""
        if self.__startTime is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")
        elapsedTime = self.time()
        self.__startTime = None
        return elapsedTime