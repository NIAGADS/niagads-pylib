from typing import Any, Dict, List, Optional, Self, Union

from niagads.common.models.core import T_TransformableModel
from niagads.common.models.metadata import (
    BiosampleCharacteristics,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
    CurationEvent,
)
from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.models.core import (
    ORMCompatibleDynamicRowModel,
    ORMCompatibleRowModel,
    ResultSize,
)
from niagads.api.common.models.response.record import RecordResponse
from niagads.genomics.features.core import GenomicFeatureType
from niagads.genomics.sequence.assembly import Assembly
from niagads.utils.dict import promote_nested
from pydantic import Field, model_validator

COMPOSITE_ATTRIBUTES: Dict[str, T_TransformableModel] = {
    "biosample_characteristics": BiosampleCharacteristics,
    "participant_phenotypes": Phenotype,
    "experimental_design": ExperimentalDesign,
    "provenance": Provenance,
    "file_properties": FileProperties,
    "curation_history": CurationEvent,
}


class AbridgedTrack(ORMCompatibleDynamicRowModel):
    track_id: str = Field(
        title="Track ID",
        serialization_alias="id",
        description="stable track identifier",
    )
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: Assembly = Field(
        default=Assembly.GRCh38,
        title="Assembly",
        description=f"one of {Assembly.list()}",
    )
    feature_type: Optional[GenomicFeatureType] = Field(
        default=None,
        title="Feature",
        description=(
            f"primary type of genomic feature being annotated. "
            f"One of {GenomicFeatureType.list(to_lower=True)}"
        ),
    )
    is_download_only: Optional[bool] = Field(
        default=False,
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
    )
    is_shard: Optional[bool] = Field(
        default=False,
        title="Is Shard?",
        description="Flag indicating whether track is part of a result set sharded by chromosome.",
        exclude=True,
    )
    data_source: Optional[str] = Field(
        default=None,
        title="Data Source",
        description="original data source for the track",
    )
    data_category: Optional[str] = Field(
        default=None,
        title="Category",
        description="data category; may be analysis type",
    )
    url: Optional[str] = Field(
        default=None,
        title="Download URL",
        description="URL for NIAGADS-standardized file",
    )

    @model_validator(mode="before")
    @classmethod
    def process_extras(cls: Self, data: Union[Dict[str, Any]]):
        """
        promoted nested fields so that can get data_source, data_category,
        url, etc from `Track` object

        not doing null checks b/c if these values are missing there is an
        error in the data the needs to be reviewed

        After promotion, only keep extra counts, prefixed with `num_` as
        allowable extra fields for a track summary
        """

        # this will happen b/c FastAPI tries all models
        # until it can successfully serialize
        if isinstance(data, str):
            return data

        if not isinstance(data, dict):
            data = data.model_dump()  # assume data is an ORM w/model_dump mixin

        # should make data_source, url etc available
        promote_nested(data, updateByReference=True)

        # filter out excess from the Track ORM model
        modelFields = AbridgedTrack.model_fields.keys()
        return {
            k: v for k, v in data.items() if k in modelFields or k.startswith("num_")
        }


class Track(ORMCompatibleRowModel):

    track_id: str = Field(
        title="Track ID",
        serialization_alias="id",
        description="stable track identifier",
    )
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: Assembly = Field(
        default=Assembly.GRCh38,
        title="Assembly",
        description=f"Reference genome build; one of {Assembly.list()}",
    )
    feature_type: Optional[GenomicFeatureType] = Field(
        default=None,
        title="Feature",
        description=(
            f"Primary type of genomic feature being annotated; "
            f"one of {GenomicFeatureType.list(to_lower=True)}"
        ),
    )

    is_download_only: Optional[bool] = Field(
        default=False,
        title="Download Only",
        description="File is available for download only; data cannot be queried using the NIAGADS Open Access API.",
        json_schema_extra={"is_filer_annotation": True},
    )
    is_shard: Optional[bool] = Field(
        default=False,
        title="Is Shard?",
        description="Flag indicating whether track is part of a result set sharded by chromosome.",
        json_schema_extra={"is_filer_annotation": True},
        exclude=True,
    )
    # FIXME: exclude cohorts until parsing resolved for FILER
    cohorts: Optional[List[str]] = Field(default=None, title="Cohorts")
    biosample_characteristics: Optional[BiosampleCharacteristics] = Field(
        default=None,
        title="Sample Characteristics",
    )
    participant_phenotypes: Optional[Phenotype] = Field(
        default=None,
        title="Phenotypes",
    )
    experimental_design: Optional[ExperimentalDesign] = Field(
        default=None,
        title="Experimental Design",
    )
    provenance: Provenance = Field(
        title="Provenance",
    )
    file_properties: Optional[FileProperties] = Field(
        default=None,
        title="File Properties",
    )
    curation_history: Optional[list[CurationEvent]] = Field(
        default=None,
        title="Curation History",
        description="Chronological list of curation events applied to this track",
    )

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = super()._flat_dump(nullFree, delimiter)
        for field, value in self:
            if field in COMPOSITE_ATTRIBUTES.keys():
                del obj[field]
                if value is not None:
                    obj.update(value._flat_dump())
                else:
                    # create dict of {key: None}
                    obj.update(
                        {
                            k: None
                            for k in COMPOSITE_ATTRIBUTES[field].get_model_fields(
                                as_str=True
                            )
                        }
                    )

        return obj

    @classmethod
    def get_model_fields(cls, as_str=False):
        fields = super().get_model_fields()
        model: T_TransformableModel
        for fieldId, model in COMPOSITE_ATTRIBUTES.items():
            fields.update(model.get_model_fields())

        for fieldId in COMPOSITE_ATTRIBUTES.keys():
            del fields[fieldId]

        return list(fields.keys()) if as_str else fields

    def as_table_row(self, **kwargs):
        return super().as_table_row(**kwargs)

    def to_ga4gh_drs(self) -> dict:
        """Produce a minimal GA4GH DRS-style object for this track's primary file.

        Returns a dictionary conforming to the common DRS fields used for
        discovery and access. This is a best-effort, local-only serializer and
        does not perform any network calls.

        Raises ValueError if file_properties is not present.
        """
        if not self.file_properties:
            raise ValueError("file_properties required to generate DRS representation")

        drs_id = f"niagads:dataset:{self.track_id}"

        checksums = []
        if self.file_properties.md5sum:
            checksums.append({"type": "md5", "checksum": self.file_properties.md5sum})

        access_methods = []
        if self.file_properties.url:
            access_methods.append(
                {"type": "https", "access_url": self.file_properties.url}
            )

        return {
            "id": drs_id,
            "name": self.name,
            "size": self.file_properties.file_size,
            "checksums": checksums or None,
            "mime_type": self.file_properties.file_format,
            "access_methods": access_methods or None,
        }

    def to_datacite(self) -> dict:
        """Produce a minimal DataCite JSON representation for this Track.

        This builds a small DataCite-compatible dict suitable for metadata
        exchange or conversion to the DataCite JSON schema. Only a subset of
        fields are produced (identifiers, titles, publisher, publicationYear,
        descriptions, subjects, sizes, formats, relatedIdentifiers).

        """

        identifiers = [
            {
                "identifier": f"niagads:dataset:{self.track_id}",
                "identifierType": "OTHER",
            }
        ]

        titles = [{"title": self.name}]

        publisher = self.provenance.data_source
        publication_year = self.provenance.release_date

        descriptions = [
            {"description": self.description, "descriptionType": "Abstract"}
        ]

        subjects = []
        if self.participant_phenotypes:
            for term in self.participant_phenotypes.get_ontology_terms():
                subjects.append({"subject": term.term})
        if self.feature_type:
            subjects.append({"subject": self.feature_type})

        sizes = None
        formats = None
        if self.file_properties:
            sizes = (
                str(self.file_properties.file_size)
                if self.file_properties.file_size is not None
                else None
            )
            formats = self.file_properties.file_format

        related_identifiers = []
        if self.provenance.pubmed_id:
            for pmid in self.provenance.pubmed_id:
                related_identifiers.append(
                    {
                        "relatedIdentifier": str(pmid),
                        "relationType": "IsReferencedBy",
                        "relatedIdentifierType": "PMID",
                    }
                )

        return {
            "identifiers": identifiers,
            "titles": titles,
            "publisher": publisher,
            "publicationYear": publication_year,
            "descriptions": descriptions,
            "subjects": subjects or None,
            "sizes": sizes,
            "formats": formats,
            "relatedIdentifiers": related_identifiers or None,
        }

    def to_schemaorg(self) -> dict:
        """Produce a schema.org/Dataset JSON-LD representation for this Track.

        This builds a JSON-LD dict compatible with schema.org/Dataset (with
        BioSchemas property extensions). Includes identifier, name, description,
        datePublished, publisher, distribution (if file_properties present).
        """

        ld_context = "https://schema.org"
        dataset_type = ["Dataset", "https://bioschemas.org/types/Dataset/0.4-RELEASE"]

        identifier = f"niagads:dataset:{self.track_id}"

        schemaorg = {
            "@context": ld_context,
            "@type": dataset_type,
            "identifier": identifier,
            "name": self.name,
            "description": self.description,
            "datePublished": str(self.provenance.release_date),
            "publisher": {
                "@type": "Organization",
                "name": self.provenance.data_source,
            },
        }

        if self.file_properties and self.file_properties.url:
            schemaorg["distribution"] = {
                "@type": "DataDownload",
                "contentUrl": self.file_properties.url,
                "encodingFormat": self.file_properties.file_format
                or "application/x-gzip",
            }
            if self.file_properties.file_size:
                schemaorg["distribution"].update(
                    {"contentSize": f"{self.file_properties.file_size} bytes"}
                )

        return schemaorg


class TrackResultSize(ResultSize):
    track_id: str = Field(title="Track ID", serialization_alias="id")


class AbridgedTrackResponse(RecordResponse):
    data: List[AbridgedTrack] = Field(
        description="Abridged metadata for each track meeting the query criteria.  Depending on query may include count of records matching query parameters."
    )


class TrackResponse(RecordResponse):
    data: List[Track] = Field(
        description="Full metadata for each track meeting the query criteria."
    )

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        if self.is_empty():
            if incl_header:
                return self._get_empty_header()
            else:
                return ""

        else:
            fields = self.data[0].get_fields(as_str=True)
            rows = []
            for r in self.data:
                if isinstance(r, str):
                    rows.append(r)
                else:
                    # pass fields to ensure consistent ordering
                    rows.append(r.as_text(fields=fields, null_str=null_str))

            response_str = "\t".join(fields) + "\n" if incl_header else ""
            response_str += "\n".join(rows)

        return response_str
