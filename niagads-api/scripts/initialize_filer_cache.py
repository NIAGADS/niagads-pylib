#!/usr/bin/env python3

import argparse
import logging

from os import path

from requests import get
from requests.exceptions import HTTPError

from niagads.db.postgres.postgres_async import AsyncDatabase 
from niagads.filer import FILERMetadataParser, FILERApiWrapper
from niagads.utils.logging import ExitOnExceptionHandler
from niagads.utils.dict import print_dict

from constants import URLS


LOGGER = logging.getLogger(__name__)


def fetch_live_FILER_metadata(debug:bool=False):
    ''' for verifying tracks and removing any not currently available '''
    LOGGER.info("Fetching Live FILER track identifiers reference.")
    
    api = FILERApiWrapper(URLS.filer_api, debug=debug)
    
    # sum(list, []) is a python hack for flattening a nested list
    GRCh37 = sum([[ v for k, v in d.items() if k == '#Identifier' or k == 'Identifier'] \
        for d in api.make_request("get_metadata", {'assembly':'hg19'})], [])
    GRCh38 = sum([[ v for k, v in d.items() if k == '#Identifier' or k == 'Identifier'] \
        for d in api.make_request("get_metadata", {'assembly':'hg38'})], [])

    LOGGER.info("Found " + str(len(GRCh37)) + " GRCh37 live tracks.")
    LOGGER.info("Found " + str(len(GRCh38)) + " GRCh38 live tracks.")

    return  {"GRCh37": GRCh37, "GRCh38": GRCh38}


def initialize_metadata_cache(dbh, metadataFileName:str, debug: bool=False):
    ''' initializes FILER metadta from the metadata template file '''
    lineNum = 0
    currentLine = None
    try:
        # query FILER metadata (for verify track availabilty)
        liveMetadata = fetch_live_FILER_metadata(debug)
        
        # fetch the template file 
        requestUrl = URLS.filer_downloads + '/metadata/' + metadataFileName
        LOGGER.info("Fetching FILER metadata: " + requestUrl)
        
        if debug:
            LOGGER.debug("Fetching FILER metadata from " + requestUrl)
        response = get(requestUrl)
        response.raise_for_status()
        
        metadata = response.text.split('\n')
        header = metadata.pop(0).split('\t')
        if metadata[-1] == '': metadata.pop()    # file may end with empty line
            
        if debug:
            LOGGER.debug("Retrieved metadata for " + str(len(metadata)) + " tracks.")
    
        parser = FILERMetadataParser(debug=debug)
        parser.set_filer_download_url(URLS.filer_downloads)
        parser.set_primary_key_label('track_id')
        parser.set_biosample_props_as_json()
        parser.set_dates_as_strings()
        
        for line in metadata:
            lineNum += 1
            currentLine = line
        
            # parse & create Metadata object
            parser.set_metadata(dict(zip(header, line.split('\t'))))
            track = parser.parse()
            
            LOGGER.critical(track)
            
            if track['track_id'] in liveMetadata[track['genome_build']]:
                1
                # db.session.add(Track(**track))
            else:
                LOGGER.info("Track not found in FILER: " + currentLine)
            
            if debug and lineNum % 10000 == 0:
                LOGGER.debug("Loaded metadata for " + str(lineNum) +" tracks")
            
        # db.session.commit()
        
    except HTTPError as err:
        raise HTTPError("Unable to fetch FILER metadata", err)
    except Exception as err:
        raise RuntimeError("Unable to parse FILER metadata, problem with line #: " 
                + str(lineNum), currentLine , err)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize FILER Track Metadata Cache", allow_abbrev=False)
    parser.add_argument("--trackMetadataFile", help="full URI", required=True)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--logFilePath", default="/logs")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        handlers=[ExitOnExceptionHandler(
            filename=path.join(args.logFilePath, 'initialize_filer_cache.log'),
            mode='w',
            encoding='utf-8',
        )],
        format='%(asctime)s %(funcName)s %(levelname)-8s %(message)s',
        level=logging.DEBUG if args.debug else logging.INFO)

    initialize_metadata_cache(None, args.trackMetadataFile, args.debug)
    
  
