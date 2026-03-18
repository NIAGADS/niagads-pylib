from typing import List, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.common.track.models import (
    BiosampleCharacteristics,
    CurationEvent,
    ExperimentalDesign,
    FileProperties,
    Phenotype,
    Provenance,
)
from niagads.common.track.models.phenotypes import PhenotypeCount
from niagads.genomics.features.core import GenomicFeatureType
from niagads.genome_reference.human import GenomeBuild
from pydantic import Field


class BaseTrack(CustomBaseModel):

    track_id: str = Field(
        title="Track ID",
        alias="id",
        serialization_alias="id",
        description="stable track identifier",
    )
    name: str = Field(title="Name")
    description: Optional[str] = Field(default=None, title="Description")
    genome_build: GenomeBuild = Field(
        default=GenomeBuild.GRCh38,
        title="Genome Build",
        description="reference genome build",
    )
    feature_type: Optional[GenomicFeatureType] = Field(
        default=None,
        title="Feature",
        description="primary type of genomic feature being annotated",
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

    cohorts: Optional[List[str]] = Field(default=None, title="Cohorts")
    provenance: Provenance = Field(
        title="Provenance",
    )
    file_properties: FileProperties = Field(
        title="File Properties",
    )
    experimental_design: ExperimentalDesign = Field(
        default=None,
        title="Experimental Design",
    )
    participant_phenotypes: Optional[Phenotype] = Field(
        default=None,
        title="Phenotypes",
    )
    study_diagnosis: Optional[List[PhenotypeCount]] = Field(
        default=None,
        title="Study Diagnosis",
        description="number of cases and controls",
    )
    biosample_characteristics: Optional[BiosampleCharacteristics] = Field(
        default=None,
        title="Sample Characteristics",
    )

    curation_history: Optional[List[CurationEvent]] = Field(
        default=None,
        title="Curation History",
        description="Chronological list of curation events applied to this track",
    )

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
