import logging
from requests import get
from requests.exceptions import HTTPError

# from filer.models import Metadata
from niagads.filer import FILERMetadataParser
# from filer.parsers import FILERMetadataParser
from filer.track.models import Track
from api.internal.filer.wrapper import make_request
from shared_resources import constants

logger = logging.getLogger(__name__)

def fetch_live_FILER_metadata():
    ''' for verifying tracks and removing any not currently available '''
    
    # sum(list, []) is a python hack for flattening a nested list
    hg19 = sum([[ v for k, v in d.items() if k == 'Identifier'] for d in make_request("get_metadata", {'assembly':'hg19'})], [])
    hg38 = sum([[ v for k, v in d.items() if k == 'Identifier'] for d in make_request("get_metadata", {'assembly':'hg38'})], [])
    return  {"GRCh37": hg19, "GRCh38": hg38}

def initialize_metadata_cache(db, metadataFileName, debug):
    ''' initializes FILER metadta from the metadata template file '''
    lineNum = 0
    currentLine = None
    try:
        # query FILER metadata (for verify track availabilty)
        liveMetadata = fetch_live_FILER_metadata()
        
        # fetch the template file 
        requestUrl = constants.URLS.filer_downloads + '/metadata/' + metadataFileName
        if debug:
            logger.debug("Fetching FILER metadata from " + requestUrl)
        response = get(requestUrl)
        response.raise_for_status()
        
        metadata = response.text.split('\n')
        header = metadata.pop(0).split('\t')
        if metadata[-1] == '': metadata.pop()    # file may end with empty line
            
        if debug:
            logger.debug("Retrieved metadata for " + str(len(metadata)) + " tracks.")
    
        for line in metadata:
            lineNum += 1
            currentLine = line
        
            # parse & create Metadata object
            track = FILERMetadataParser(dict(zip(header, line.split('\t'))), debug)
            track.set_filer_download_url(constants.URLS.filer_downloads)
            track = track.parse()
            
            if track['identifier'] in liveMetadata[track['genome_build']]:
                db.session.add(Track(**track))
            else:
                logger.info("Track not found in FILER: " + currentLine)
            
            if debug and lineNum % 10000 == 0:
                logger.debug("Loaded metadata for " + str(lineNum) +" tracks")
            
        db.session.commit()
        
    except HTTPError as err:
        raise HTTPError("Unable to fetch FILER metadata", err)
    except Exception as err:
        raise RuntimeError("Unable to parse FILER metadata, problem with line #: " 
                + str(lineNum), currentLine , err)
