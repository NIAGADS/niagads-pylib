from datetime import datetime
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
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import RAGDocType
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
from niagads.etl.plugins.types import ResumeCheckpoint
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)

from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel


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
        self._track_type_id: int = None

        # map of provided value (curie|term) to DB record
        self._ontology_term_reference: dict[str, DBOntologyTerm]

    def _load_track_record(self, file_path: str) -> TrackRecord:
        """Load a track record from a JSON file.

        Args:
            file_path (str): Path to the JSON track record file.

        Returns:
            TrackRecord: The parsed track record.
        """
        with read_open_ctx(file_path) as fh:
            content = json.load(fh)
        return TrackRecord(**content)

    async def on_run_start(self, session) -> None:
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)

        if self.is_etl_run:
            await self.set_table_ref(session, Track)

    def get_record_id(self, erecord: EmbeddedTrackRecord) -> str:
        return erecord.track.id

    def _validate_study_diagnosis_phenotypes(self, record: TrackRecord) -> None:
        """Validate study diagnosis phenotypes against contextual phenotypes.

        Args:
            record (TrackRecord): Track record to validate.

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

    async def _validate_track_record(
        self, record: TrackRecord
    ) -> OntologyTermValidation:
        """Extract and validate ontology terms from a track record

        Args:
            record (TrackRecord): Track record to validate.

        Returns:
            OntologyTermValidation: Ontology term validation results.

        Raises:
            ValueError: If study diagnosis phenotypes are not contextualized
                or the required data category is missing.
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
    ) -> Optional[list[OntologyTerm]]:
        """Extract ontology terms from a track's contextual annotation.

        Args:
            context_type (TrackContextType): Context definition used to retrieve
                the annotation.
            record (TrackRecord): Track record containing the annotation.

        Returns:
            Optional[list[OntologyTerm]]: Extracted terms, or None if no
                annotation is present.
        """
        annotation = context_type.retrieve_context_from_record(record)
        if annotation is None:
            return None

        self.logger.debug(f"context={context_type}; annotation={annotation}")

        return OntologyTerm.extract_from_obj(annotation)

    async def _validate_ontology_terms(
        self, session, record: TrackRecord
    ) -> OntologyTermValidation:
        """Validate ontology terms extracted from a track record.

        Args:
            session (AsyncSession): Database session used to resolve ontology
                terms.
            record (TrackRecord): Track record whose ontology terms should be
                extracted.

        Returns:
            OntologyTermValidation: Validation results for the extracted
                ontology terms.

        """
        extracted_terms: dict = OntologyTerm.extract_from_obj(record, as_dict=True)
        return DBOntologyTerm.validate_terms(session, extracted_terms)

    def _update_nested_ontology_references(self, record: TrackRecord) -> None:
        """Replace nested ontology terms with their canonical database values.

        Updates each term's label and CURIE in place and adds the normalized
        CURIE and term to the reference map while recursively parsing nested
        objects.

        Args:
            record (TrackRecord): Track record to update.

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
        """Serialize a track record and prepare its embedding metadata.

        Args:
            record (TrackRecord): Track record to serialize.

        Returns:
            EmbeddedTrackRecord: Serialized track record with content hashes.
        """
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
        """Generate embeddings for prepared track records.

        Args:
            records (list[TrackRecord]): Track records to serialize and embed.

        Returns:
            list[EmbeddedTrackRecord]: Track records containing generated
                embedding vectors.
        """
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

    async def _generate_track_concepts(
        self, track_record: TrackRecord, track_id: int
    ) -> list[TrackConcept]:
        """Create concept links for a track's keyword annotations.

        Args:
            track_record (TrackRecord): Track record containing keyword
                annotations.
            track_id (int): Database identifier of the track.

        Returns:
            list[TrackConcept]: Track concept records linking the track to its
                keyword terms.
        """
        # now we need to load the linking tables
        concepts: list[TrackConcept] = []
        for keyword in track_record.keywords:
            key = (keyword.term, keyword.curie)
            keyword_pk: int = self._ontology_term_reference[key]["ontology_term_id"]
            self.logger.debug(f"Found Concept Keyword: {key} - {keyword_pk}")
            concepts.append(
                TrackConcept(track_id=track_id, ontology_term_id=keyword_pk)
            )
        return concepts
        #

    async def _generate_track_context(
        self, track_record: TrackRecord, track_id: int
    ) -> list[TrackContext]:
        """Create context links for a track's contextual annotations.

        Args:
            track_record (TrackRecord): Track record containing contextual
                annotations.
            track_id (int): Database identifier of the track.

        Returns:
            list[TrackContext]: Track context records linking the track to
                contextual terms.
        """
        contexts: list[TrackContext] = []
        context_type: TrackContextType
        for context_type in TrackContextType:
            ontology_terms: list[OntologyTerm] = (
                self._extract_contextual_ontology_terms(context_type, track_record)
            )
            for ot in ontology_terms:
                key = (ot.term, ot.curie)
                ot_pk: int = self._ontology_term_reference[key]["ontology_term_id"]
                self.logger.debug(f"Found Contextual OT: {key} - {ot_pk}")
                contexts.append(
                    TrackContext(
                        track_id=track_id,
                        ontology_term_id=ot_pk,
                        context=str(context_type),
                    )
                )
        return contexts

    def _get_track_type_id(self, record: TrackRecord) -> int:
        """Resolve and cache the ontology_term_id for a track type.

        Args:
            record (TrackRecord): Track record whose track type should be
                resolved.

        Returns:
            int: ontology_term_id for the track type.
        """
        if not self._track_type_id:
            key = (record.track_type.term, record.track_type.curie)
            self._track_type_id = self._ontology_term_reference[key]["ontology_term_id"]
        return self._track_type_id

    async def _load_track_records(
        self,
        session,
        records: list[EmbeddedTrackRecord],
        *,
        is_filer_track: bool = False,
    ) -> ResumeCheckpoint:
        """Persist a track record, its context, concepts, and embeddings.

        Args:
            session (AsyncSession): Database session used for persistence.
            records (list[EmbeddedTrackRecord]): Embedded track records to
                load.
            is_filer_track (bool): Whether the tracks originate from FILER.

        Returns:
            ResumeCheckpoint: Checkpoint for the last loaded track record.
        """

        tracks: list[Track] = []
        for record in records:
            track_type_id = self._get_track_type_id(record.track)
            tracks.append(
                Track(
                    **record.track.model_dump(exclude=["id"], exclude_none=True),
                    source_id=record.track.id,
                    track_type_id=track_type_id,
                    run_id=self.run_id,
                    external_database_id=self.external_database_id,
                    is_filer_track=is_filer_track,
                )
            )

        await Track.submit_many(session, tracks)

        chunk_metadata: list[ChunkMetadata] = []
        track_concepts: list[TrackConcept] = []
        track_contexts: list[TrackContext] = []
        for index, record in enumerate(records):
            track_id = tracks[index].track_id
            track_concepts.extend(self._generate_track_concepts(record, track_id))
            track_contexts.extend(self._generate_track_context(record, track_id))
            chunk_metadata.append(
                ChunkMetadata(
                    table_id=self._table_ref.table_id,
                    row_id=track_id,
                    document_type=str(RAGDocType.METADATA),
                    document_hash=record.document_hash,
                    chunk_hash=record.chunk_hash,
                    chunk_text=record.chunk_text,
                    run_id=self.run_id,
                )
            )

        await TrackConcept.submit_many(session, track_concepts)
        await TrackContext.submit_many(session, track_contexts)
        await ChunkMetadata.submit_many(session, chunk_metadata)

        chunk_embeddings: list[ChunkEmbedding] = []
        for index, metadata in enumerate(chunk_metadata):
            chunk_embeddings.append(
                ChunkEmbedding(
                    chunk_metadata_id=metadata.chunk_metadata_id,
                    chunk_hash=metadata.chunk_hash,
                    embedding_model=str(self._params.embedding_model),
                    embedding=records[index].embedding,
                    embedding_date=datetime.now().isoformat(),
                    embedding_run_id=self.run_id,
                    run_id=self.run_id,
                )
            )

        await ChunkEmbedding.submit_many(session, chunk_embeddings)
        return self.create_checkpoint(record=records[-1])
