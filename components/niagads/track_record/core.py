"""core defines the `Track` (metadata) record database model"""

from typing import Optional

from niagads.genome.core import Assembly
from niagads.list_utils.core import list_to_string
from niagads.open_access_api_configuration.core import DataStore
from niagads.track_record.models.properties import BiosampleCharacteristics
from sqlalchemy import TEXT, Column, Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint


class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "metadataentry"
    __table_args__ = (
        CheckConstraint(
            f"genome_build in ({list_to_string(Assembly.list(), quote=True, delim=', ')})",
            name="check_genome_build",
        ),
        {"schema": "track"},
    )

    metadata_entry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    track_id: Mapped[str] = mapped_column(unique=True, index=True)
    data_store: DataStore
    name: Mapped[str]
    description: Mapped[str] = mapped_column(String(2000))

    genome_build: str = Column(
        Enum(Assembly, native_enum=False), nullable=False, index=True
    )

    feature_type: Mapped[str] = mapped_column(String(50), index=True)
    is_download_only: Mapped[bool] = mapped_column(default=False, index=True)

    searchable_text: str = Column(TEXT, index=True)

    is_shard: Mapped[Optional[bool]]
    shard_root_track_id: Mapped[Optional[str]] = mapped_column(index=True)

    # biosample
    biosample_characteristics: Mapped[BiosampleCharacteristics] = mapped_column(JSONB)

    """
    # experimental design
    experimental_design: ExperimentalDesign | None = Field(sa_column=Column(JSONB))

    # provenance
    provenance: Provenance | None = Field(sa_column=Column(JSONB))

    # track_properties
    properties: TrackProperties | None = Field(sa_column=Column(JSONB))
    
    file_name: Optional[str]
    url: Optional[str]
    md5sum: Optional[str]

    bp_covered: Optional[int] = Field(sa_column=Column(BigInteger()))
    number_of_intervals: Optional[int] = Field(sa_column=Column(BigInteger()))
    file_size: Optional[int]

    file_format: Optional[str]
    file_schema: Optional[str]
    release_date: Optional[date] = Field(sa_column=Column(TIMESTAMP(timezone=False)))

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
