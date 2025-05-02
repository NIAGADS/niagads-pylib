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
from niagads.utils.list import flatten
from niagads.utils.reg_ex import regex_extract, matches, regex_replace

from constants import URLS, SCHEMA, FILER_TABLE, SHARD_PATTERN

LOGGER = logging.getLogger(__name__)


def fetch_live_FILER_metadata(debug: bool = False):
    """for verifying tracks and removing any not currently available"""
    LOGGER.info("Fetching Live FILER track identifiers reference.")

    api = FILERApiWrapper(URLS.filer_api, debug=debug)

    GRCh37 = flatten(
        [
            [v for k, v in d.items() if k == "#Identifier" or k == "Identifier"]
            for d in api.make_request("get_metadata", {"assembly": "hg19"})
        ]
    )
    GRCh38 = flatten(
        [
            [v for k, v in d.items() if k == "#Identifier" or k == "Identifier"]
            for d in api.make_request("get_metadata", {"assembly": "hg38"})
        ]
    )
    GRCh38 = GRCh38 + flatten(
        [
            [v for k, v in d.items() if k == "#Identifier" or k == "Identifier"]
            for d in api.make_request("get_metadata", {"assembly": "hg38-lifted"})
        ]
    )

    LOGGER.info("Found " + str(len(GRCh37)) + " GRCh37 live tracks.")
    LOGGER.info("Found " + str(len(GRCh38)) + " GRCh38 live tracks.")

    return {"GRCh37": GRCh37, "GRCh38": GRCh38}


def extract_metadata_values(track: dict):
    """
    extract & format dict values for load; catch nulls, json etc

    Args:
        track (dict): field:value pairs
    Returns:
        array of data
    """
    fields = list(track.keys())
    fields.sort()  # so that order is consistent w/prepared statement
    values = []
    for f in fields:
        if isinstance(track[f], dict):
            values.append(json.dumps(track[f]))
        else:  # do we need to catch nulls?
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


def initialize_metadata_cache(metadataFileName: str, test: int, debug: bool = False):
    """initializes FILER metadta from the metadata template file"""
    lineNum = 1
    skipCount = 0
    currentLine = None
    parsedTracks = {}
    shardedTracks = {}
    try:
        # initialize parser
        parser = FILERMetadataParser(debug=debug)
        parser.set_filer_download_url(URLS.filer_downloads)
        parser.set_primary_key_label("track_id")
        parser.set_biosample_props_as_json()
        parser.set_dates_as_strings()
        # parser.set_biosample_mapper(read_reference_file(args.biosampleMapping))

        # fetch the template file
        metadata = read_reference_file(args.metadataTemplate)
        header = metadata.pop(0).split("\t")
        if metadata[-1] == "":
            metadata.pop()  # file may end with empty line
        LOGGER.info("Processing metadata for " + str(len(metadata)) + " tracks.")

        # query FILER metadata (for verify track availabilty)
        liveMetadata = (
            fetch_live_FILER_metadata(debug) if not args.skipLiveValidation else None
        )

        for line in metadata:
            lineNum += 1
            currentLine = line
            track = None  # so that errors don't print out track from previous iteration

            # parse & create Metadata object
            parser.set_metadata(dict(zip(header, line.split("\t"))))
            track = parser.parse()

            LOGGER.debug("Parsed track %s" % track)

            if track["genome_build"] is None:
                # FIXME: log non-assembly associated tracks and skip for now
                LOGGER.debug(
                    "SKIPPING track with `NoneType` value for Genome Build (line %s): %s"
                    % (lineNum, currentLine)
                )
                skipCount += 1
                continue

            if (
                "CADD" in track["name"]
            ):  # no need; CADD annotation will come from GenomicsDB endpoints
                LOGGER.debug(
                    "SKIPPING CADD Track (line %s): %s" % (lineNum, currentLine)
                )
                skipCount += 1
                continue

            if track["data_source"].startswith("Ensembl"):
                LOGGER.warning(
                    "SKIPPING Ensembl track (line %s): %s" % (lineNum, currentLine)
                )
                skipCount += 1
                continue

            # if 'download_only' in track:
            #     if track['download_only'] == True:
            #         LOGGER.warning('SKIPPING download onyl track(line %s): %s' % (lineNum, currentLine))
            #         skipCount +=1
            #         continue

            if track["track_id"] in parsedTracks:
                LOGGER.warning(
                    "SKIPPING duplicate track (line %s): %s" % (lineNum, currentLine)
                )
                skipCount += 1
                continue

            if (
                not args.skipLiveValidation
                and track["track_id"] not in liveMetadata[track["genome_build"]]
            ):
                LOGGER.info(
                    "SKIPPING track not found in current FILER release: (line %s): %s"
                    % (lineNum, currentLine)
                )
                skipCount += 1
                continue

            parsedTracks[track["track_id"]] = track

            if lineNum % 10000 == 0:
                LOGGER.debug("Processed metadata for " + str(lineNum) + " tracks")

        LOGGER.info(f"DONE PARSING Tracks. Found {len(parsedTracks)} valid tracks.")

        trackNum = 0
        insertCount = 0
        LOGGER.info("STARTING Load.")
        for track in parsedTracks.values():
            # check and handle sharded tracks (split by chromosome)
            isShard = matches(SHARD_PATTERN, track["file_name"])
            if isShard:
                track["is_shard"] = True
                sKey = regex_replace(SHARD_PATTERN, "_", track["file_name"])

                shardChrm = "chr" + regex_extract(
                    SHARD_PATTERN, track["file_name"]
                ).replace("_", "")
                track["shard_chromosome"] = shardChrm
                if sKey not in shardedTracks:
                    # find the first shard
                    shardedTracks[sKey] = next(
                        (
                            k
                            for k, t in parsedTracks.items()
                            if regex_replace(SHARD_PATTERN, "_", t["file_name"]) == sKey
                            and matches(r"_chr1_", t["file_name"])
                        ),
                        None,
                    )
                    LOGGER.info(
                        f"Found new sharded track series: {track['file_name']} with parent track: {shardedTracks[sKey]}"
                    )
                track["shard_parent_track_id"] = shardedTracks[sKey]

            insert_record(track)
            insertCount = insertCount + 1

            trackNum += 1
            if trackNum % 10000 == 0:
                LOGGER.debug("Inserted metadata for " + str(insertCount) + " tracks")

            if test is not None and lineNum == test:
                LOGGER.info("TEST LOAD - COMPLETE")
                return insertCount

    except HTTPError as err:
        raise HTTPError("Unable to fetch FILER metadata", err)
    except Exception as err:
        raise RuntimeError(
            "Unable to parse FILER metadata, problem with line #: " + str(lineNum),
            currentLine,
            track,
            err,
        )

    return insertCount, skipCount


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize FILER Track Metadata Cache", allow_abbrev=False
    )
    parser.add_argument(
        "--metadataTemplate",
        required=True,
        help="metadata template file; if file name includes '/', assumes local otherwise assumes it will needed to be fetched from the server",
    )
    # parser.add_argument("--biosampleMapping", required=True,
    #    help="biosample mapping file; if file name includes '/', assumes local otherwise assumes it will needed to be fetched from the server")
    parser.add_argument(
        "--connectionString", help="postgres connection string", required=True
    )
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--logFilePath", default="/logs")
    parser.add_argument("--test", type=int, help="number of test tracks to process")
    parser.add_argument(
        "--skipLiveValidation",
        action="store_true",
        help="to speed up testing, skip validation against live instance",
    )

    args = parser.parse_args()

    logging.basicConfig(
        handlers=[
            ExitOnExceptionHandler(
                filename=path.join(args.logFilePath, "initialize_filer_cache.log"),
                mode="w",
                encoding="utf-8",
            )
        ],
        format="%(asctime)s %(funcName)s %(levelname)-8s %(message)s",
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    try:
        database = Database(connectionString=args.connectionString)
        database.connect()
        nInserts, nSkips = initialize_metadata_cache(
            args.metadataTemplate, args.test, args.debug
        )
        LOGGER.info("INSERTED " + str(nInserts) + " rows.")
        LOGGER.info("SKIPPED " + str(nSkips) + " rows.")
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
