#!/usr/bin/env python3

import logging
from typing import List

from niagads.arg_parser.core import case_insensitive_enum_type
from niagads.common.constants.external_resources import NIAGADSResources
from niagads.database.models.metadata.track import Track
from niagads.genome.core import Assembly
from niagads.loaders.core import AbstractDataLoader
from niagads.metadata_parser.filer import MetadataTemplateParser
from niagads.requests.core import HttpClientSessionManager
from niagads.utils.list import flatten
from niagads.utils.logging import ExitOnExceptionHandler
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches, regex_extract, regex_replace
from pydantic import BaseModel
from requests.exceptions import HTTPError
from sqlalchemy.ext.asyncio import AsyncSession

TARGET_TABLE = f"{Track.metadata.schema}.{Track.__tablename__}"


class Counts(BaseModel):
    skip: int = 0
    loaded: int = 0
    parsed: int = 0
    shards: int = 0


class TrackMetadataLoader(AbstractDataLoader):
    def __init__(
        self,
        template: str,
        databaseUri: str,
        genomeBuild: Assembly = Assembly.GRCh38,
        apiUrl: str = NIAGADSResources.FILER_API,
        downloadUrl: str = NIAGADSResources.FILER_DOWNLOADS,
        commit: bool = False,
        test: bool = False,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(databaseUri, commit, test, debug, verbose)

        self.__apiUrl = apiUrl
        self.__downloadUrl = downloadUrl

        self.__parser = MetadataTemplateParser(
            template, self.__downloadUrl, debug=self._debug
        )
        self.__genomeBuild: Assembly = genomeBuild

        self.__parsedTracks: List[Track] = None
        self.__shardedTracks: dict = None
        self.__liveTracks: List[int] = None
        self.__counts: Counts = Counts()
        self.__skipLiveValidation = False

    def skip_live_validation(self):
        self.__skipLiveValidation = True

    def parse_template(self):
        self.__parsedTracks = self.__parser.parse(asTrackList=True)
        self.__counts.parsed == len(self.__parsedTracks)

    def fetch_live_track_ids(self):
        """Fetch live FILER track identifiers reference."""

        sessionManager = HttpClientSessionManager(self.__apiUrl)
        params = {"genomeBuild": self.__genomeBuild.hg_label()}

        self.__liveTracks = flatten(
            [
                [v for k, v in d.items() if "Identifier" in k]
                for d in sessionManager.fetch("get_metadata.php", params)
            ]
        )

    def __skip_track(self, track: Track):
        """Determine if a track should be skipped."""

        if track.genome_build is None:
            return True

        if "CADD" in track.name:
            return True

        if track.provenance.data_source == "Repeats":
            return True

        if track.provenance.data_source.startswith("Ensembl"):
            return True

        if not self.__skipLiveValidation:
            if track.track_id not in self.__liveTracks:
                return True

        return False

    def __get_shard_key(self, fileName: str):
        # check to see if the root of a sharded file has been identified,
        # if not, find and save
        shardKey = regex_replace(RegularExpressions.SHARD, "_", fileName)
        if shardKey not in self.__shardedTracks:
            self.__shardedTracks[shardKey] = next(
                (
                    t
                    for t in self.__parsedTracks
                    if regex_replace(RegularExpressions.SHARD, "_", fileName)
                    == shardKey
                    and matches(r"_chr1_", t["file_name"])
                ),
                None,
            )

        return self.__shardedTracks[shardKey]

    async def load(self):
        if self.__parsedTracks is None:
            self.parse_template()

        if not self.__skipLiveValidation and self.__liveTracks is None:
            self.fetch_live_track_ids()

        session: AsyncSession = self.get_db_session()
        for track in self.__parsedTracks:
            if self.__skip_track(track):
                self.__counts.skip += 1
                continue

            if matches(RegularExpressions.SHARD, track["file_name"]):
                # set shard properties
                track.is_shard = True
                track.shard_chromosome = f"chr{regex_extract(RegularExpressions.SHARD, track.file_properties.file_name)}".replace(
                    "_", ""
                )
                track.shard_root_track_id = self.__shardedTracks[
                    self.__get_shard_key(track.file_properties.file_name)
                ]

            await session.add(track)

            self.__counts.loaded += 1
            await self.commit(session, self.__counts.loaded, "Track records")
            if self._test is not None and self.__counts.loaded == self._test:
                break

        # commit residuals / commit test
        await self.commit(
            session, self.__counts.loaded, "Track records", residuals=True
        )

    def log_load_summary(self):
        transactionStatus = "INSERTED" if self._commit else "ROLLED BACK"
        if self._test is not None:
            self.logger.info(f"DONE with TEST (n={self._test})")
        else:
            self.logger.info("DONE")

        self.logger.info(
            f"PARSED {self.__counts.parsed} Track entries from {self.__parser.get_template_file_name()}"
        )
        self.logger.info(f"SKIPPED {self.__counts.loaded} invalid track entries.")
        self.logger.info(
            f"{transactionStatus} {self.__counts.loaded} Track records into {TARGET_TABLE.title()}"
        )
        self.logger.info(
            f"FOUND {self.__counts.shards} belonging to {len(self.__shardedTracks)} unique result sets."
        )


async def main():
    """
    Load metadata from a FILER template file into the database.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=f"Load records in {TARGET_TABLE.title()} from a FILER metadata template file",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--template",
        required=True,
        help="metadata template file; if file name does not start with `http` assumes locally hosted",
    )
    parser.add_argument(
        "--genomeBuild",
        type=case_insensitive_enum_type(Assembly),
        choices=Assembly.list(),
        default="GRCh38",
        help="assembly (genome build)",
    )
    parser.add_argument(
        "--databaseUri",
        help="postgres connection string; if not set tries to pull from .env file",
    )
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--test", type=int, help="number of test tracks to process")
    parser.add_argument(
        "--skipLiveValidation",
        action="store_true",
        help="to speed up testing, skip validation against live instance",
    )

    args = parser.parse_args()

    logging.basicConfig(
        handlers=[ExitOnExceptionHandler()],
        level=logging.DEBUG if args.debug else logging.INFO,
    )
    try:
        loader = TrackMetadataLoader(
            args.template,
            args.databaseUri,
            args.genomeBuild,
            test=args.test,
            commit=args.commit,
            debug=args.debug,
            verbose=args.verbose,
        )

        if args.skipLiveValidation:
            loader.skip_live_validation()

        await loader.load()

        loader.log_load_summary()

    except Exception as err:
        loader.logger.critical(err, exc_info=True, stack_info=True)
    finally:
        await loader.close()


def run_main():
    """wrapper necessary so that the main coroutine gets correctly awaited"""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run_main()
