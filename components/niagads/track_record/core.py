"""core SQLModel defining a `Track` record"""

from datetime import date
from typing import Optional

from niagads.open_access_api_configuration.core import DataStore
from niagads.open_access_api_models.core import SerializableModel
from pydantic import computed_field
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB, TEXT, TIMESTAMP
from sqlmodel import Column, Field, SQLModel


class Track(SQLModel, SerializableModel, table=True):
    __tablename__ = "metadata"
    __table_args__ = {"schema": "track"}

    track_id: str = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = Field(sa_column=Column(TEXT))
    genome_build: Optional[str] = "GRCh38"
    feature_type: Optional[str] = None
    download_only: Optional[bool] = False
    data_store: DataStore

    # biosample
    biosample_characteristics: BiosampleCharacteristics | None = Field(
        sa_column=Column(JSONB)
    )

    # experimental design
    experimental_design: ExperimentalDesign | None = Field(sa_column=Column(JSONB))

    # provenance
    provenance: Provenance | None = Field(sa_column=Column(JSONB))

    file_name: Optional[str]
    url: Optional[str]
    md5sum: Optional[str]

    bp_covered: Optional[int] = Field(sa_column=Column(BigInteger()))
    number_of_intervals: Optional[int] = Field(sa_column=Column(BigInteger()))
    file_size: Optional[int]

    file_format: Optional[str]
    file_schema: Optional[str]

    release_date: Optional[date] = Field(sa_column=Column(TIMESTAMP(timezone=False)))

    searchable_text: Optional[str] = Field(sa_column=Column(TEXT))
    is_shard: Optional[bool]
    shard_root_track_id: Optional[str]

    # FIXME: move to Provenance
    @computed_field
    @property
    def data_source_url(self) -> str:
        dsKey = (
            self.data_source + "|" + self.data_source_version
            if self.data_source_version is not None
            else self.data_source
        )
        try:
            return getattr(DATASOURCE_URLS, dsKey)
        except (
            Exception
        ) as e:  # TODO: error reporting to admins b/c this is a missing data problem
            return self.data_source

    # =================================
    # GENOME BROWSER FIELDS
    # =================================

    # FIXME: create genome browser properties object and populate
    """
    @computed_field
    @property
    def IGV_browser_config(self) -> IGVBrowserConfig:
        # index_url, browser_track_name, browser_track_category, browser_track_format, track_type
    
    @computed_field
    @property
    def index_url(self) -> str:
        if self.url.endswith(".gz"):
            return self.url + ".tbi"
        else:
            return None
    
    @computed_field
    @property
    def browser_track_name(self) -> str:
        return (
            self.track_id
            + ": "
            + self.name.replace(
                f"{self.feature_type} {self.feature_type}", self.feature_type
            )
        )

    @computed_field
    @property
    def browser_track_category(
        self,
    ) -> str:  # TODO: be more specific? e.g., data category?
        return "Functional Genomics"

    @computed_field
    @property
    def browser_track_format(self) -> str:
        if self.file_schema is None:
            return "bed"
        schema = self.file_schema.split("|")
        return schema[0]

    @computed_field
    @property
    def browser_track_type(self) -> str:
        trackType = "annotation"
        if "|" in self.file_schema:
            schema = self.file_schema.split("|")
            trackType = schema[1]
        return trackType
    """
