import json
from typing import Any, Dict, Optional

from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.track.models.record import TrackRecord
from niagads.database.genomicsdb.schema.dataset.track import (
    Track,
    TrackConcept,
    TrackContext,
    TrackContextType,
)
from niagads.database.genomicsdb.schema.reference.ontology import (
    OntologyTerm as DBOntologyTerm,
    OntologyTermValidation,
)
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.mixins import (
    EmbeddingGeneratorContextMixin,
    ExternalDatabaseContextMixin,
)
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    EmbeddingParameterMixin,
)
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.list import chunker
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound


class EmbeddedTrackRecord(CustomBaseModel, arbitrary_types_allowed=True):
    track: TrackRecord
    chunk_text: str
    chunk_hash: bytes
    document_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


class TrackLoaderBaseParams(
    BasePluginParams,
    ExternalDatabaseRefMixin,
    EmbeddingParameterMixin,
): ...


class TrackLoaderBase(
    AbstractBasePlugin, ExternalDatabaseContextMixin, EmbeddingGeneratorContextMixin
):
    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._database_type_id: int = None

        # map of provided value (curie|term) to DB record
        self._ontology_term_reference: dict[str, DBOntologyTerm]

    def _load_track_record(self, file_path: str) -> Any:
        """Read JSON file and return parsed content."""
        with read_open_ctx(file_path) as fh:
            content = json.load(fh)
        return TrackRecord(**content)

    async def on_run_start(self, session):
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)

        if self.is_etl_run:
            await self.set_table_ref(session, Track)

    def get_record_id(self, erecord: EmbeddedTrackRecord):
        return erecord.track.id

    def _validate_study_diagnosis_phenotypes(self, record: TrackRecord):
        """Validate study diagnosis phenotypes against contextual phenotypes.

        Args:
            record: Track record to validate.

        Raises:
            ValueError: If a study diagnosis phenotype is missing from the
                contextual phenotypes.

        FIXME: Move this validation to TrackRecord model validation when
        study_diagnosis is provided.
        """
        phenotype_terms = [
            ot.term
            for ot in self._extract_contextual_ontology_terms(
                TrackContextType.PHENOTYPE, record
            )
        ]
        diagnosis_terms = [
            phenotype
            for diagnosis in record.study_diagnosis
            for phenotype in diagnosis.phenotype
        ]

        mismatches = sorted(set(diagnosis_terms) - set(phenotype_terms))
        if mismatches:
            raise ValueError(
                f"Study diagnosis phenotypes missing from contextual phenotypes: "
                f"{mismatches}"
            )

    async def _validate_track_record(self, record: TrackRecord):
        """
        Preprocess: Extract and validate ontology terms from a track record
        Logs result
        """
        self.logger.info(f"Validating track record ontology terms")
        async with self.session_ctx() as session:
            validation_result = await self._validate_ontology_terms(session, record)

        if not validation_result.not_matched and not validation_result.multiple_matches:
            self.logger.info("Ontology Term Validation: PASSED")
            self._validate_study_diagnosis_phenotypes(record)
            try:
                data_category = record.experimental_design.data_category
            except Exception as err:
                data_category = None
            if not data_category:
                raise ValueError(
                    f"Missing required `data_category` field (under `experimental_design`)"
                )

        else:
            self.logger.info("Ontology Term Validation: FAILED")
            self.logger.info(f"Valid Terms: {len(validation_result.valid)}")
            self.logger.info(f"Not Matched: {len(validation_result.not_matched)}")
            self.logger.info(f"Multiple Matches: {len(validation_result.not_matched)}")
            output_path = f"{self._params.file}.ot_validation.json"
            print(json.dumps(validation_result, indent=4), file=output_path)
            self.logger.info(f"Validation results saved to {output_path}")

        return validation_result

    def _extract_contextual_ontology_terms(
        self, context_type: TrackContextType, record: TrackRecord
    ):
        """Extract ontology terms from a track's contextual annotation.

        Args:
            context_type: Context definition used to retrieve the annotation.
            record: Track record containing the annotation.

        Returns:
            list[OntologyTerm] | None: Extracted terms, or None if no annotation
                is present.
        """
        annotation = context_type.retrieve_context_from_record(record)
        if annotation is None:
            return None

        self.logger.debug(f"context={context_type}; annotation={annotation}")

        return OntologyTerm.extract_from_obj(annotation)

    async def _validate_ontology_terms(
        self, session, record: TrackRecord
    ) -> OntologyTermValidation:
        """Validate ontology terms extracted from an object.

        Args:
            session: The database session used to resolve ontology terms.
            record: Track Record whose ontology terms should be extracted.

        """
        extracted_terms: dict = OntologyTerm.extract_from_obj(record, as_dict=True)
        return DBOntologyTerm.validate_terms(session, extracted_terms)

    def _update_nested_ontology_references(self, record: TrackRecord) -> None:
        """Replace nested ontology terms with their canonical database values.

        Updates each term's label and CURIE in place and adds its canonical key
        to the reference map for subsequent lookups by recursively parsing
        nested objects.

        Args:
            record: Track record to update.

        Raises:
            KeyError: If a term does not have a matching reference entry.
        """

        def update_ontology_terms(value: Any) -> None:
            if isinstance(value, OntologyTerm):
                key = f"{value.curie}|{value.term}"
                reference = self._ontology_term_reference[key]
                curie = reference.source_id.replace("_", ":")
                self._ontology_term_reference[f"{curie}|{reference.term}"] = reference
                value.term = reference.term
                value.curie = curie
            elif isinstance(value, BaseModel):
                for field_name in value.__class__.model_fields:
                    update_ontology_terms(getattr(value, field_name, None))
            elif isinstance(value, dict):
                for item in value.values():
                    update_ontology_terms(item)
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    update_ontology_terms(item)

        update_ontology_terms(record)

    def _generate_embedded_track_record(
        self, record: TrackRecord
    ) -> EmbeddedTrackRecord:
        try:
            chunk_text = json.dumps(
                record.model_dump(
                    exclude_none=True,
                    context={SerializationOptions.EMBEDDED_TEXT: True},
                )
            )
        except Exception as err:
            self.logger.critical(f"Problem generating chunk_text for record: {err}")

        # self.logger.debug(f"Chunk Text: {chunk_text}")

        document = json.dumps(record.model_dump(exclude_none=True))

        return EmbeddedTrackRecord(
            track=record,
            chunk_text=chunk_text,
            chunk_hash=self._embedding_generator.hash_text(chunk_text),
            document_hash=self._embedding_generator.hash_text(document),
        )

    async def _embed_track_records(
        self, records: list[TrackRecord]
    ) -> list[EmbeddedTrackRecord]:
        # generate embeddings
        embedded_track_records: list[EmbeddedTrackRecord] = [
            self._generate_embedded_track_record(record) for record in records
        ]

        embeddings = self._embedding_generator.generate(
            [r.chunk_text for r in embedded_track_records],
            as_list=True,
        )

        self.logger.info(
            f"Generated embeddings for {len(embedded_track_records)} records"
        )

        for index, embedding in enumerate(embeddings):
            embedded_track_records[index].embedding = embedding

        return embedded_track_records

    async def _load_track_record(self, session, erecord: EmbeddedTrackRecord):
        track_record = erecord.track

        track_data = track_record.model_dump(exclude=["id"], exclude_none=True)
        track_data["source_id"] = track_record.id
        track_data["run_id"] = self.run_id
        track_data["external_database_id"] = self.external_database_id

        track: Track = Track(**track_data)
        track_id: int = await track.submit(session)

        # now we need to load the linking tables
        concepts: list[TrackConcept] = []
        for keyword in track_record.keywords:
            key = f"{keyword.curie}|{keyword.term}"
            keyword_pk: int = self._ontology_term_reference[key].ontology_term_id
            self.logger.debug(f"Found Keyword: {key} - {keyword_pk}")
            concepts.append(
                TrackConcept(track_id=track_id, ontology_term_id=keyword_pk)
            )
        await TrackConcept.submit_many(session, concepts)

        contexts: list[TrackContext] = []
        context_type: TrackContextType
        for context_type in TrackContextType:
            ontology_terms: list[OntologyTerm] = (
                self._extract_contextual_ontology_terms(context_type, track_record)
            )
            for ot in ontology_terms:
                key = (ot.term, ot.curie)
                ot_pk: int = self._ontology_term_reference[key].ontology_term_id
                self.logger.debug(f"Found Contextual OT: {key} - {ot_pk}")
                contexts.append(
                    TrackContext(
                        track_id=track_id,
                        ontology_term_id=ot_pk,
                        context=str(context_type),
                    )
                )
        await TrackContext.submit_many(session, contexts)

        return self.create_checkpoint(record=track_record)
