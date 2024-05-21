#!/usr/bin/env python3

import argparse
import logging
import json

from os import path

from requests import get
from requests.exceptions import HTTPError

from niagads.db.postgres import Database, PreparedStatement
from niagads.filer import FILERMetadataParser, FILERApiWrapper
from niagads.utils.logging import ExitOnExceptionHandler
from niagads.utils.dict import print_dict
from niagads.utils.list import flatten
from niagads.utils.string import xstr

from constants import URLS, SCHEMA, FILER_TABLE

LOGGER = logging.getLogger(__name__)


def read_reference_file(fileName: str, localFile:bool=False):
    """ if '/files' in file name assumes local and opens and reads.  otherwise, fetches from FILER """
    contents = None
    if localFile or '/' in fileName:
        LOGGER.info("Reading file: " + fileName)
        with open(fileName, 'r') as fh:
            contents = fh.read().splitlines() 
    
    else:
        try:
            requestUrl = URLS.filer_downloads + '/metadata/' + fileName
            LOGGER.info("Fetching file: " + requestUrl)
            
            response = get(requestUrl)
            response.raise_for_status()
            contents = response.text.split('\n')
        except Exception: # TODO: why didn't catching HTTPError work?
            LOGGER.info("Unable to fetch file: " + requestUrl + "; trying to open locally")  
            return read_reference_file(fileName, localFile=True)    

    return contents


def fetch_live_FILER_metadata(debug:bool=False):
    ''' for verifying tracks and removing any not currently available '''
    LOGGER.info("Fetching Live FILER track identifiers reference.")
    
    api = FILERApiWrapper(URLS.filer_api, debug=debug)
    
    GRCh37 = flatten([[ v for k, v in d.items() if k == '#Identifier' or k == 'Identifier'] \
        for d in api.make_request("get_metadata", {'assembly':'hg19'})])
    GRCh38 = flatten([[ v for k, v in d.items() if k == '#Identifier' or k == 'Identifier'] \
        for d in api.make_request("get_metadata", {'assembly':'hg38'})])

    LOGGER.info("Found " + str(len(GRCh37)) + " GRCh37 live tracks.")
    LOGGER.info("Found " + str(len(GRCh38)) + " GRCh38 live tracks.")
    
    return  {"GRCh37": GRCh37, "GRCh38": GRCh38}


def extract_metadata_values(track: dict):
    """
    extract & format dict values for load; catch nulls, json etc

    Args:
        track (dict): field:value pairs
    Returns:
        array of data
    """
    fields = list(track.keys())
    fields.sort() # so that order is consistent w/prepared statement
    values = []
    for f in fields:
        if isinstance(track[f], dict):
            values.append(json.dumps(track[f]))
        else: # do we need to catch nulls?
            values.append(track[f])

    return values    
    

def insert_record(track: dict):
    """
    insert record into database

    Args:
        track (dict): track info to be loaded
    """
    statement = PreparedStatement(SCHEMA, FILER_TABLE)
    with database.cursor() as cursor:
        cursor.execute(statement.insert(track), extract_metadata_values(track))
        

def initialize_metadata_cache(metadataFileName:str, test:int, debug: bool=False):
    ''' initializes FILER metadta from the metadata template file '''
    lineNum = 0
    insertCount = 0
    currentLine = None
    try:
        # initialize parser    
        parser = FILERMetadataParser(debug=debug)
        parser.set_filer_download_url(URLS.filer_downloads)
        parser.set_primary_key_label('track_id')
        parser.set_biosample_props_as_json()
        parser.set_dates_as_strings()
        parser.set_biosample_mapper(read_reference_file(args.biosampleMapping))
        
        # fetch the template file 
        metadata = read_reference_file(args.metadataTemplate)
        header = metadata.pop(0).split('\t')
        if metadata[-1] == '': metadata.pop()    # file may end with empty line
        LOGGER.info("Processing metadata for " + str(len(metadata)) + " tracks.")
       
        # query FILER metadata (for verify track availabilty)
        liveMetadata = fetch_live_FILER_metadata(debug)
        
        for line in metadata:
            lineNum += 1
            currentLine = line
        
            # parse & create Metadata object
            parser.set_metadata(dict(zip(header, line.split('\t'))))
            track = parser.parse()
            
            if track['track_id'] in liveMetadata[track['genome_build']]:
                insert_record(track)
                insertCount = insertCount + 1
            else:
                LOGGER.info("Track not found in FILER: " + currentLine)
            
            if lineNum % 10000 == 0:
                LOGGER.debug("Processed metadata for " + str(lineNum) +" tracks")
                LOGGER.debug("Inserted metadata for " + str(insertCount) +" tracks")
            
            if test is not None and lineNum == test:
                LOGGER.info("TEST LOAD - COMPLETE")
                return
        
    except HTTPError as err:
        raise HTTPError("Unable to fetch FILER metadata", err)
    except Exception as err:
        raise RuntimeError("Unable to parse FILER metadata, problem with line #: " 
                + str(lineNum), currentLine , err)
        
    return insertCount


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize FILER Track Metadata Cache", allow_abbrev=False)
    parser.add_argument("--metadataTemplate", required=True,
        help="metadata template file; if file name includes '/', assumes local otherwise assumes it will needed to be fetched from the server")
    parser.add_argument("--biosampleMapping", required=True, 
        help="biosample mapping file; if file name includes '/', assumes local otherwise assumes it will needed to be fetched from the server")
    parser.add_argument("--connectionString", help="postgres connection string", required=True)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--logFilePath", default="/logs")
    parser.add_argument("--test", type=int, help="number of test tracks to process")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        handlers=[ExitOnExceptionHandler(
            filename=path.join(args.logFilePath, 'initialize_filer_cache.log'),
            mode='w',
            encoding='utf-8',
        )],
        format='%(asctime)s %(funcName)s %(levelname)-8s %(message)s',
        level=logging.DEBUG if args.debug else logging.INFO)

    try:
        database = Database(connectionString=args.connectionString)
        database.connect()
        nInserts = initialize_metadata_cache(args.metadataTemplate, args.test, args.debug)
        LOGGER.info("INSERTED " + str(nInserts) + " rows.")
        if args.commit:
            LOGGER.info("COMMITTING")
            database.commit()
        else:
            LOGGER.info("ROLLING BACK")
            database.rollback()
            
    except Exception as err:
        LOGGER.critical(err, exc_info=True, stack_info=True)
    finally:
        database.close()
    
