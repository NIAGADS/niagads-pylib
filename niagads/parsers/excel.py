import logging
import json

from os import getcwd, path
from pandas import read_excel, DataFrame
from openpyxl import Workbook as wb, load_workbook

from ..utils.sys import warning
from ..utils.string import xstr, to_snake_case
from ..utils.dict import print_dict

class ExcelFileParser:
    """
    parser for EXCEL files; mainly a pandas/openpyxl wrapper
    """
    def __init__(self, file:str, debug:bool=False):
        """
        init new ExcelFileParser

        Args:
            file (str): EXCEL file name (full path)
            debug (bool, optional): enable debug mode. Defaults to False.
        """
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__file = file
        self.__na = 'null' # missing value string representation
        
        # openpyxl data structures
        # useful for iterating over sheets
        self.__workbook = None
        self.__worksheets = None
        self.__init_workbook()
        
        
    def __init_workbook(self):
        """
        load the workbook & get list of worksheets
        initialize member variables
        (should do basic parsing & error reporting; e.g., non-ascii characters)   
        """
        # data_only=True -> values, not formulas & formatting
        self.__workbook = load_workbook(self.__file, data_only=True)
        self.__worksheets = self.__workbook.get_sheet_names()
 

    def set_na_rep(self, value:str):
        """
        set the NA (missing / null) value string representation
        suggestions: '.', 'NA', 'null', 'NULL', '\t'

        Args:
            value (str): missing / null value string
        """
        self.__na = value
        
        
    def get_workbook(self):
        """
        returns openpyxl `workbook` object
        """
        return self.__workbook
    
    
    def list_worksheets(self):
        """
        returns a list of worksheet names
        """
        return self.__worksheets
    
    
    def write_to_csv(self, outputPath:str, worksheet:str=None, sep:str=','):
        """
        converts the EXCEL file to CSV and saved to `outputPath`.  
        If `worksheet` == None, all worksheets in the file are converted
        otherwise only the specified worksheet will be converted

        output files will be named `to_snake_case(worksheet)` +'.csv'` 
        '.txt' extension will be used for space and tab delimited files
        '.csv' will be use for comma and non-standard delimiters     

        Args:
            outputPath (str): path to which the files should be written
            sep (str, optional): delimiter.  Defaults to ','
            worksheet (str, optional): worksheet name. Defaults to None.
        """
        if worksheet is None:
            for ws in self.__worksheets: self.__worksheet_to_csv(outputPath, ws, sep)
        else:
            self.__worksheet_to_csv(outputPath, worksheet, sep)
        
            
            
    def is_valid_worksheet(self, worksheet:str, raiseErr:bool=False):
        """
        checks if worksheet exists, otherwise raises error

        Args:
            worksheet (str): worksheet name
            raiseErr (boolean, optional): raise an error if False, otherwise will return False
        """
        if worksheet not in self.__worksheets:
            if raiseErr:
                msg = "Worksheet " + worksheet + " not found in " \
                    + self.__file + "; valid values are: " + xstr(self.__worksheets)
                self.logger.error(msg)
                raise ValueError(msg)
            else:
                return False
        return True
    
    
    def __worksheet_to_csv(self, outputPath:str, worksheet:str, sep:str):
        """
        internal / called by to_csv to write an worksheet to CSV

        Args:
            outputPath (str): path to which the files should be written
            sep (str): delimiter
            worksheet (str): worksheet name
        """        
        fileName = path.join(outputPath, 
                                to_snake_case(worksheet) \
                                + ('.csv' if sep == ',' else '.txt'))
        
        df = self.to_pandas_df(worksheet)
        df.to_csv(fileName, sep=sep, index=False, encoding='utf-8', na_rep=self.__na)
    
    
    def worksheet_to_json(self, worksheet, transpose=False, returnStr=False, **kwargs):
        """
        converts the EXCEL file to JSON
        
        Args:
            worksheet (str|int): worksheet name or index, starting from 0.
            transpose (bool, optional): transpose the worksheet?
            returnStr (bool, optional): return jsonStr instead of object
            **kwargs (optional): arguments to pass to `pandas` `read_excel` see
                (see https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html))
        
        Returns:
            if `returnStr` returns JSON string instead of object
        """
        ws = self.__worksheets[worksheet] if isinstance(worksheet, int) else worksheet   
        
        # orient='records' returns indexes; e.g. [index: {row data}] so need to extract the values
        jsonStr = self.to_pandas_df(ws, transpose, **kwargs).to_json(orient = 'records')
        return jsonStr if returnStr else json.loads(jsonStr)

        
    def to_pandas_df(self, worksheet: str, transpose=False, **kwargs) -> DataFrame:
        """
        _summary_

        Args:
            worksheet (str): worksheet name
            transpose (str): transpose the worksheet
            **kwargs: must match expected args for pandas.read_excel 
                (see https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)

        Returns:
            DataFrame: worksheet in data frame format
        """
        # raise error if False
        self.is_valid_worksheet(worksheet, raiseErr=True)
        df: DataFrame = read_excel(self.__file, sheet_name=worksheet, **kwargs)
        return df.T if transpose else df
        