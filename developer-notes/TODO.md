# TODOs

## Open Access API

* Add XML and plain text serializers.
* Add explicit types for nested dictionaries in API responses, including
  `memberships` and `functional_annotation`, so generated OpenAPI documentation
  describes their structure instead of showing `{"additionalProperty": "anything"}`.
* generate python and typescript SDKS [design prompt](plans/api-refactor_plan/sdk-prompt.md)

## ASK NIAGADS alpha

* Evaluate AD-related Gene Ontology (GO) annotations and pathway memberships as
  additional gene evidence for ASK. Define how to identify AD-relevant terms and
  pathways and preserve their provenance and distinction from direct association
  evidence before implementation.
* Add Open Access to the NIAGADS code of conduct.
* Identify the best matching source phrase within a semantically matched document
  chunk for gene, variant, and track searches. Embedding similarity identifies
  the winning chunk but does not locate an exact phrase. Return the full matched
  chunk for now; evaluate extracting a supporting source passage for more precise
  evidence and LLM summaries. Example: searching genes for `blood` returns F13B
  (`ENSG00000143278`, coagulation factor XIII B chain). `matched_text` should
  contain the winning document chunk, with a future refinement identifying the
  passage supporting its relevance to blood instead of echoing the query.
* Deferred: implement batch ontology-based ORM retrieval for gene documents and
  tracks. See [Prompt 006](plans/ask/deferred-prompts.md#prompt-006-ontology-based-retrieval-for-gene-documents-and-tracks)
  for association paths and scope. Activate only when explicitly requested.
* Revisit ASK configuration loading and discoverability. `AskSettings` maps
  `ASK_*` environment variables to unprefixed attributes through `env_prefix`
  and reads `.env` relative to the working directory. Query embedding settings
  use `CustomSettings.from_env()` and honor `SERVICE_ENV`, while telemetry checks
  `LOGFIRE_TOKEN` directly in the process environment. Align these paths with
  established project conventions and document variable-to-consumer mappings.
  Clarify that `sample.ask.env` is a template and is not loaded automatically.
* Deferred discussion: [ASK design prompts](plans/ask/deferred-prompts.md)
  cover hard-coded capabilities, unexpected requests, extension scenarios, and
  assessment/refactoring of Polylith base/component boundaries (Prompt 005).
  Reference only; activate individual prompts only when explicitly requested.
* Potential refactor: generate ASK operation metadata at build time from FastAPI
  route definitions or an exported OpenAPI specification instead of maintaining
  `bases/niagads/open_access_api/ask/operations.py` independently. Route definitions
  can retain the actual Python response/record model classes; OpenAPI describes
  their schemas but does not reliably identify the intended entity, annotation
  kind, or default model among content-dependent alternatives. Evaluate explicit
  route metadata for ASK eligibility, entity/annotation mapping, and model
  selection as the single source for generation. Preserve planned-operation
  status and explicit tool exposure; discovering a route must not automatically
  make it callable by the agent. Generate without database startup or provider
  calls, and detect stale or inconsistent generated metadata during build checks.
  Assess alongside the existing frontend type exporter before implementation.
* Local follow-up: update ORM retrieval models/methods for paginated associations
  by region and phenotype-associated genes with curated and +/-10 kb proximity
  evidence. Database queries belong in the ORM layer, never in API code. These
  changes are outside the cloud prototype scope and require separate approval.
* Wire placeholder region endpoints to those ORM methods after they are ready;
  preserve existing API response/parameter conventions. Until then report the
  capability as not implemented, not an empty successful result.
* Validate the OpenRouter query embedding integration live with the user-selected
  ETL default via OPENROUTER_EMBEDDING_MODEL=liquid/lfm-2.5-embedding-350m:free. Confirm availability and
  compatible model/version, encoding, dimensions, and gene/track results locally.
  Query embedding wiring is implemented; stored vectors, ETL, and ORM retrieval
  remain unchanged. Never substitute another embedding model.
* Conversation history is current-session only for the alpha. Deferred: persist
  conversations across visits using the existing Valkey and AWS Cognito
  infrastructure, which is not present on the selected development branches.
  Inspect that infrastructure before designing the persistence integration.
* Deferred: query variant annotations for variants predicted to impact a gene,
  then use supporting phenotype associations to identify associated genes.
  Variant querying infrastructure is not available yet; do not implement this
  retrieval path in the alpha.
* Initial gene-association evidence paths: curated gene records
  (`associated_with_known_ad_locus` and/or `memberships.curated_lists`) and
  associated variants within the gene footprint plus 10 kb on each side.
  Preserve the evidence type and provenance in responses; proximity does not
  establish predicted impact.

* fix bug w/ALFA loading from dbSNP VCF: wrap in {'ALFA':}.  TODO - patch db

* update schema dataset model to reflect new api model
* replace flat_dump w/context based serialization (will get passed to all children)
* can we move casesensitiveenum to common.types ? circular imports?!

## Project wide

* Potential refactor: evaluate migrating `HttpClientSessionManager`
  (`components/niagads/requests/core.py`) from aiohttp to HTTPX to unify shared
  HTTP client management. Currently the manager provides pooled network sessions,
  timeouts, request logging, JSON retrieval, and cleanup for existing consumers.
  In contrast, ASK's `bases/niagads/open_access_api/ask/api_client.py` accepts an
  `httpx.AsyncClient` and streams responses with a byte limit. Its caller in
  `ask/transport.py` supplies `httpx.ASGITransport` to invoke the existing FastAPI
  routes in process, forwarding selected request headers without a network call.
  HTTPX is used here for that transport capability, not because agent tools
  require a separate HTTP client implementation.
  These uses could converge on the existing manager backed by HTTPX, preserving
  its public retrieval/lifecycle methods while allowing an optional transport
  and bounded streaming. First inventory callers, particularly those obtaining
  the underlying aiohttp session through `__call__`: request/response APIs,
  timeout semantics, connection limits, exception handling, and logging need
  compatibility review. A direct client substitution is insufficient. Discuss
  scope before implementation; this is a candidate refactor, not an approved
  migration.
* systematically review all function defintions and use `"*, "` before named parameters to enforce using they keywords

## ETL

* **Bug fix:** Correct track `study_diagnosis[].phenotype` values stored as
  string representations of lists instead of JSON arrays. Repair existing
  records and ensure ETL preserves phenotype lists during serialization.
* Refine embedding document chunking into smaller, semantically distinct chunks
  so gene names and aliases are separate from pathway content. ETL should retain
  each chunk's type and determine its retrieval priority so ranking can account
  for the kind of evidence matched, alongside embedding similarity. For example,
  an `amyloid beta` match in a gene-name chunk should rank above a match in a
  pathway chunk. Define chunk boundaries and priority rules before implementation.

### FILER

* extract `is_cancer_cell`, `is_immune_cell` from track_description (probably) only relevant to ENCODE tracks
* there will be a new version of the template files with new column headers

```
NGENC7VGJXPUQ5  ENCODE  ENCFF078YRQ.bed.gz      3700    728458  IDR thresholded peaks   hg38    Ishikawa        Cell line       EFO:0005718     Female Reproductive     ENCSR000BKW     1       1_1     FOXA1   TF ChIP-seq   bed narrowPeak   62535   ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3    07/10/2025      12/12/2020      07/31/2025      https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz 2fd60d49de95ff2545c9292b3d46eb2a        wget https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz -P ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/   wget https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/ENCFF078YRQ.bed.gz.tbi -P ${TARGETDIR}/GADB/Annotationtracks/ENCODE/data/TF-ChIP-seq/narrowpeak/hg38/3/       https://www.encodeproject.org   https://www.encodeproject.org/files/ENCFF078YRQ/@@download/ENCFF078YRQ.bigBed   wget https://tf.lisanwanglab.org/GADB/Annotationtracks/Downloads/ENCODE/ENCFF078YRQ.bigBed -P ${TARGETDIR}/GADB/Annotationtracks/Downloads/ENCODE/     0fbb96a7db792b531812d6cf84a83f0c        TF ChIP-seq peaks       TF ChIP-seq IDR thresholded peaks       Biosample_summary=Homo sapiens Ishikawa treated with 0.02% dimethyl sulfoxide for 1 hour;Lab=Richard Myers, HAIB;ENCODE_internal_tags=RegulomeDB_1_0,RegulomeDB_2_0,RegulomeDB_2_1,ENCYCLOPEDIAv2,ENCYCLOPEDIAv1,RegulomeDB_2_2;Life_stage_age=adult 39 years;Reference=PMID:22710073;External_resources=GEO:GSM803444,UCSC-ENCODE-hg19:wgEncodeEH001586,FactorBook:ENCSR000BKW;Project=ENCODE;Award=U54HG004576;Experiment_date_released=2011-07-18;Submitted_track_name=rep1-pr1_vs_rep1-pr2.idr0.05.bfilt.regionPeak.bb;ENCODE_preferred_default=false;ENCODE_biosample_term_name=Ishikawa;ENCODE_cell_slims=cancer cell;ENCODE_system_slims=reproductive system;ENCODE_biosample_term_synonyms=Ishikawa cell;Analysis_title=ENCODE4 v1.6.1 GRCh38;GM=NR;Schema=bed6+4   Reproductive    Adult   ENCODE Ishikawa (repl. 1) TF ChIP-seq FOXA1 IDR thresholded peaks (narrowPeak) [Experiment: ENCSR000BKW] [Life stage: Adult]    forGenomeBrowser
```

### Bugs

* make wrappers for sqlalchemy.exc errors NoResultFound, MultipleResultFound so errors can be handled w/out importing from sqlalchemy?
* OWL plugin loading ORCID's as terms -> why? manually patched db but need to fix (maybe skip NAMED_INDIVIDUALS?)

```0000-0002-3734-1859 150819 Carlo Tornial https://orcid.org/0000-0002-3734-1859```

## OWL ETL

* OBJECT PROPERTIES are not always parsing correctly - see example below where CURIE is extracted incorrectly; problematic example below appears to be UBERON, but appears to affect most ontologies.  Sometimes like this and sometimes missing prefix, e.g., sequence ontology has `so#` prefixed object properties; also affects some ANNOTATION PROPERTIES

```text
source_id ontology_term_id term term_iri entity_type label definition
has_component 162250 has component http://purl.obolibrary.org/obo/RO_0002180 OBJECT_PROPERTY has component w 'has component' p if w 'has part' p and w is such that it can be directly disassembled into into n parts p, p2, p3, ..., pn, where these parts are of similar type.
```

## Top Priority

## Better VSCode

* Code Actions (e.g., for abstract classes)
* isort

## Documentation

* use lazydocs instead of sphinx
  
## Developer notes

* settings/configuration for `_api` bases; see <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage>
* microservices w/FastAPI - <https://dev.to/paurakhsharma/microservice-in-python-using-fastapi-24cc#using-nginx>

## ASK dashboard follow-up

- Repair table histogram filters separately; numeric and p-value filtering is disabled in ASK dashboard translators for now.
- Adapt regional Manhattan for association position versus -log10(p), with disease/population grouping; preserve distinctions between p-values and other significance measures.
- Consider shared parent state for bidirectional filtering between tables and other dashboard panels after the independent-panel first pass.
