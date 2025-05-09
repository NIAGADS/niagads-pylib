#!/usr/bin/env python3

import logging
from typing import List

from niagads.arg_parser.core import case_insensitive_enum_type
from niagads.common.constants.external_resources import NIAGADSResources
from niagads.database.models.metadata.composite_attributes import TrackDataStore
from niagads.database.models.metadata.track import Track
from niagads.genome.core import Assembly
from niagads.loaders.core import AbstractDataLoader
from niagads.metadata_parser.filer import MetadataTemplateParser
from niagads.requests.core import HttpClientSessionManager
from niagads.utils.logging import ExitOnExceptionHandler
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches, regex_extract, regex_replace
from pydantic import BaseModel
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
        dataStore: TrackDataStore,
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
        self.__dataStore = dataStore

        self.__parser = MetadataTemplateParser(
            template, self.__downloadUrl, debug=self._debug
        )
        self.__genomeBuild: Assembly = genomeBuild

        self.__parsedTracks: List[Track] = None
        self.__shardedTracks: dict = None
        self.__liveTracks: dict = None
        self.__counts: Counts = Counts()
        self.__skipLiveValidation = False

    def skip_live_validation(self):
        self.__skipLiveValidation = True

    def parse_template(self):
        self.__parsedTracks = self.__parser.parse(asTrackList=True)
        self.__counts.parsed = len(self.__parsedTracks)
        self.logger.info(f"Done parsing tracks (n = {self.__counts.parsed}).")
        if self._debug:
            self.logger.debug(f"Parsed track type = {type(self.__parsedTracks[0])}")
            self.logger.debug(f"{self.__parsedTracks[0].model_dump()}")

    async def fetch_live_track_ids(self):
        """Fetch live FILER track identifiers reference."""

        sessionManager = HttpClientSessionManager(self.__apiUrl, debug=self._debug)
        params = {"genomeBuild": self.__genomeBuild.hg_label()}
        response: dict = await sessionManager.fetch_json("get_metadata.php", params)
        await sessionManager.close()

        self.__liveTracks = {
            t["Identifier"] if "Identifier" in t else t["#Identifier"]: True
            for t in response
        }

        self.logger.info(
            f"Retrieved {len(self.__liveTracks)} {self.__genomeBuild} live tracks for validation."
        )

        self.logger.debug(self.__liveTracks)

    def __skip_track(self, track: Track):
        """Determine if a track should be skipped."""

        if track.genome_build is None:
            return True

        if "CADD" in track.name:
            return True

        dataSource = track.provenance.get("data_source")
        if dataSource == "Repeats":
            return True

        if dataSource.startswith("Ensembl"):
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

        self.report_config()

        if self.__parsedTracks is None:
            self.parse_template()

        self.logger.info("-------------------- Begin Load --------------------\n")

        if not self.__skipLiveValidation and self.__liveTracks is None:
            await self.fetch_live_track_ids()

        session: AsyncSession
        async for session in self.get_db_session():
            for track in self.__parsedTracks:
                if self.__skip_track(track):
                    self.__counts.skip += 1
                    continue

                if matches(
                    RegularExpressions.SHARD, track.file_properties.get("file_name")
                ):
                    # set shard properties
                    track.is_shard = True
                    track.shard_chromosome = f"chr{regex_extract(RegularExpressions.SHARD, track.file_properties.file_name)}".replace(
                        "_", ""
                    )
                    track.shard_root_track_id = self.__shardedTracks[
                        self.__get_shard_key(track.file_properties.file_name)
                    ]

                # set data store
                track.data_store = str(self.__dataStore)
                session.add(track)

                self.__counts.loaded += 1

                await self.commit(session, self.__counts.loaded, "Track records")
                if self._test is not None and self.__counts.loaded == self._commitAfter:
                    break

            # commit residuals / commit test
            await self.commit(
                session, self.__counts.loaded, "Track records", residuals=True
            )

            self.logger.info("-------------------- End Load --------------------\n")
            self.report_status()

    def report_status(self):
        transactionStatus = "INSERTED" if self._commit else "ROLLED BACK"
        self.logger.info(f"DONE{' WITH TEST' if self._test is not None else ''}")
        self.logger.info(
            f"PARSED {self.__counts.parsed} Track entries from {self.__parser.get_template_file_name()}"
        )
        self.logger.info(f"SKIPPED {self.__counts.skip} invalid track entries.")
        self.logger.info(
            f"{transactionStatus} {self.__counts.loaded} Track records into {TARGET_TABLE.title()}"
        )

        self.logger.info(
            f"FOUND {self.__counts.shards} sharded tracks belonging to {len(self.__shardedTracks) if self.__counts.shards > 0 else 0} unique result sets."
        )

    def report_config(self):
        """
        Log the configuration of the TrackMetadataLoader instance.
        """
        self.logger.info("TrackMetadataLoader Configuration:")
        self.logger.info(f"Template File: {self.__parser.get_template_file_name()}")
        self.logger.info(
            f"Database URI: {self._databaseSessionManager.get_engine().url}"
        )
        self.logger.info(f"Data Store: {self.__dataStore}")
        self.logger.info(f"Genome Build: {self.__genomeBuild}")
        self.logger.info(f"API URL: {self.__apiUrl}")
        self.logger.info(f"Download URL: {self.__downloadUrl}")
        self.logger.info(f"Commit Mode: {'Enabled' if self._commit else 'Disabled'}")
        self.logger.info(f"Test Mode: {'Enabled' if self._test else 'Disabled'}")
        self.logger.info(f"Debug Mode: {'Enabled' if self._debug else 'Disabled'}")
        self.logger.info(f"Verbose Mode: {'Enabled' if self._verbose else 'Disabled'}")
        self.logger.info(
            f"Skip Live Validation: {'Yes' if self.__skipLiveValidation else 'No'}"
        )
        self.logger.info(f"Commit After: {self._commitAfter} records")


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
    parser.add_argument("--commitAfter", type=int, default=10000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--test", action="store_true", help="run in test mode")
    parser.add_argument(
        "--skipLiveValidation",
        action="store_true",
        help="to speed up testing, skip validation against live instance",
    )
    parser.add_argument(
        "--dataStore",
        type=case_insensitive_enum_type(TrackDataStore),
        choices=TrackDataStore.list(),
        help="track data store",
        default=TrackDataStore.FILER,
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
            TrackDataStore(args.dataStore),
            Assembly(args.genomeBuild),
            test=args.test,
            commit=args.commit,
            debug=args.debug,
            verbose=args.verbose,
        )

        if args.skipLiveValidation:
            loader.skip_live_validation()

        loader.set_commit_after(args.commitAfter)

        await loader.load()

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
