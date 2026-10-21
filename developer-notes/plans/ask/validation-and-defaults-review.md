# ASK validation and defaults review

Reviewed 2026-10-20. Scope: every Python module in
`bases/niagads/open_access_api/ask/`, as currently checked out.
Application code was not changed; no tests or live requests were run.
References below are `filename:line` within that directory.

**Flags:** **REVIEW** = assumed policy, possible duplication, or unnecessary
restriction; **MASKS** = can replace missing/invalid information with an apparently
valid value; **STRUCTURAL** = supports an actual downstream operation or declared
contract, though that contract can still be reviewed; **INIT** = local accumulator,
not a fallback for failed data. A flag identifies a review candidate, not proof
that removing it is safe. No historical approval is inferred from existing code.

## Highest-priority review candidates

| Location | Concern |
| --- | --- |
| `api_client.py:63–75` | Checks the application's own API envelope, row shape, and semantic identifier again. These can reject an otherwise successful response if the actual API contract differs. Confirm against existing response models before keeping bespoke checks. |
| `api_client.py:77–79` | Missing pagination becomes `{}`, then missing total pages becomes the current page. This can silently report no more results. |
| `tools.py:78,140–146` | Missing transcripts become `[]`; missing/duplicate transcript matches or missing locations become user clarification. An API/schema problem can look like user ambiguity. |
| `transport.py:27,52,103,165–170`; `api_client.py:44`; `results.py:22`; `tools.py:238` | Multiple independent limits reject work even when provider/API data is valid. Values are prototype policies, not demonstrated provider requirements. |
| `transport.py:124–135` | Missing presentation selections generate tables; first failure wins; a run with no results and no failures becomes `ok`. These are assumed completion semantics. |
| `tools.py:191–217` | Missing OpenAPI paths/parameters/descriptions become empty values. Missing metadata can look like no available operations. |
| `provider.py:10`; `api_client.py:31–37` | Truthiness and identifier validation overlap with settings/API validation. Confirm where validation belongs; do not add parallel rules. |

The rejected model-name comparison discussed in this conversation lives in the
shared embedding service, outside this directory. It has been removed in the
current task. That failure illustrates why a local equality check is not evidence
of an upstream contract. Shared embedding validation is not included in this
ASK-only inventory.

## Validation, empty/invalid checks, filters, and limits

### Configuration and agent construction

| Location | Check | Assessment |
| --- | --- | --- |
| `config.py:10–23` | Pydantic validates declared settings types; unrelated settings are ignored. | STRUCTURAL type parsing; **MASKS** unknown/misspelled ASK settings through `extra="ignore"`. |
| `config.py:18` | Model request budget must be 1–12. | **REVIEW** chosen prototype ceiling. |
| `config.py:19` | Tool budget must be 1–20. | **REVIEW** chosen prototype ceiling. |
| `config.py:20` | API timeout must be >0 and ≤30 seconds. | Positive timeout is structural; **REVIEW** 30-second ceiling. |
| `config.py:21` | Overall deadline must be >0 and ≤120 seconds. | Positive deadline is structural; **REVIEW** 120-second ceiling. |
| `provider.py:10` | Rejects falsey model or API key. | Explicit missing-configuration error; **REVIEW** optional settings followed by runtime enforcement. Does not verify model availability or key validity. |
| `agent.py:49` | Builds provider model only when injected `model is None`. | STRUCTURAL dependency selection; not input rejection. |
| `agent.py:55–57` | One retry, tool timeout, 2,000 output tokens, parallel tool calls disabled. | **REVIEW** execution policies, not provider necessities. |

### Incoming conversation and streaming

| Location | Check | Assessment |
| --- | --- | --- |
| `transport.py:26–28` | `messages` must be a list containing 1–12 entries. | List/nonempty checks support iteration and conversation input; **REVIEW** 12-entry limit and overlap with adapter schema validation. |
| `transport.py:32–36` | Each message must be a dict with role `user` or `assistant`. | **REVIEW** text-only/history policy; rejects other roles even if supported by the underlying SDK. |
| `transport.py:37–39` | Message `parts` must be a list. | STRUCTURAL before iteration; **REVIEW** duplicate adapter validation and missing-parts fallback. |
| `transport.py:42–43` | Each part must be a dict. | STRUCTURAL before field access; possible duplicate SDK validation. |
| `transport.py:44–47` | Rejects nontext user parts; silently skips nontext assistant parts. | **REVIEW** asymmetric filtering policy; can discard history content. |
| `transport.py:48–50` | Text must be a string. | STRUCTURAL before measuring/forwarding; possible duplicate SDK validation. |
| `transport.py:52–53` | Rejects a text part >8,000 characters or all text >16,000 characters. | **REVIEW** chosen character limits, separate from token limits. |
| `transport.py:55–56` | Retains a message only if its collected text-part list is nonempty. | **REVIEW** drops messages. This does not reject empty text strings: an empty string still creates a part. |
| `transport.py:57–58` | Requires retained history and a final user message. | **REVIEW** conversation protocol assumption; duplicates SDK requirements if the adapter already enforces them. Does not check that the final string contains a question/nonwhitespace text. |
| `transport.py:66–76,83–84` | Configuration errors become HTTP 503; detects Pydantic errors to omit input values from logs. | STRUCTURAL exception classification; **REVIEW** generic “explicit free model” message can misdescribe unrelated settings errors. No free-model validation actually occurs here. |
| `transport.py:103–104` | Rejects request bodies >65,536 bytes. | **REVIEW** prototype body cap, independent of message/character/token caps. |
| `transport.py:106–112` | Parses JSON, requires a dict, sanitizes history, invokes SDK input validation; JSON/type/value errors become HTTP 422. | STRUCTURAL parse boundary; **REVIEW** manual validation overlaps adapter validation. |
| `transport.py:124–127` | Uses stored presentations if nonempty, otherwise generates tables for the first six results. | **REVIEW** automatic UI policy rather than invalid-input protection. |
| `transport.py:128–135` | First failure becomes overall status; otherwise `empty` only if results exist and every result has no rows; otherwise `ok`. | **REVIEW** ordering-dependent failure precedence and `ok` for no retrieval. |
| `transport.py:149–151` | Forwards authorization/cookie/request-ID headers only if present. | STRUCTURAL optional-header handling. |
| `transport.py:154,165–170` | Enforces overall deadline, configured request/tool budgets, 20,000 input tokens, 12,000 output tokens. | **REVIEW** independent run budgets; distinguish from per-request 2,000-token setting. |
| `transport.py:175–181` | Replaces SDK error chunks with generic public error text. | **MASKS** details in stream; original error text now logged. |
| `transport.py:187–193` | Re-raises cancellation; all other exceptions become a generic error event and DONE. | Cancellation handling is structural; **MASKS** distinct failures in client output, now logged server-side. |

### API retrieval and result conversion

| Location | Check | Assessment |
| --- | --- | --- |
| `api_client.py:21–22` | Operation must be registered. | STRUCTURAL restriction to the operation registry; **REVIEW** whether direct callers can supply unknown names. |
| `api_client.py:25,71` | Semantic conversion selected by `record_model is SearchMatch`. | **REVIEW** exact-class identity excludes subclasses/alternate semantic models; routing assumption, not explicit validation. |
| `api_client.py:27–28` | Association operations override outgoing content with registry configuration. | STRUCTURAL full/summary selection; overrides caller input rather than checking it. |
| `api_client.py:30–35` | If path contains the entity placeholder, sanitizes the ID, then invokes existing gene/variant validators. | Reuses project utilities; **REVIEW** duplicate validation at API boundary and HTML sanitization of identifiers. Missing ID raises from `pop`, without a fallback. |
| `api_client.py:36–38` | Rejects falsey IDs, `.`/`..`, or any slash, then URL-quotes the value. | **REVIEW** overlap with gene/variant validators and quoting; route/path behavior must be established before removal. Track identifiers do not get the gene/variant validators. |
| `api_client.py:44–47` | Rejects response body >1 MiB. | **REVIEW** chosen prototype cap; rejects an otherwise valid API page. |
| `api_client.py:50–61` | Logs HTTP errors; maps 501 to unsupported; raises on other HTTP errors. | Status handling is structural; **REVIEW** assumes every 501 means pending ORM integration. |
| `api_client.py:62–67` | JSON must be a dict containing `data`; `data` must be a list and every row a dict. | STRUCTURAL for current conversion; **REVIEW** bespoke revalidation instead of established response models. Scans every row before retaining the first 50. |
| `api_client.py:69` | Retains only first 50 rows. | **REVIEW** unconditional truncation, separate from tool search limit and API page size. |
| `api_client.py:72–75` | Semantic rows must have `matched_record_id`; overwrites `id`, then merges details if truthy. | **REVIEW** assumed serialized shape. Details may overwrite the ID; missing key check does not check its value. |
| `api_client.py:78–79` | Converts page to int; reports more results if >50 rows or reported total pages > page. | **REVIEW** assumes page-number metadata and infers continuation after truncation; defaults can hide metadata omissions. |
| `api_client.py:91–94` | Sources use first truthy `track`, `id`, or `source_id`; rows without any are skipped; sources deduplicated. | **REVIEW / MASKS** provenance selection is inferred from arbitrary record identifiers; missing provenance disappears. |
| `api_client.py:96–105` | Adds warning for semantic results and for >50-row truncation. | Explanatory conditions; no rejection. |

### Tool checks and result storage

| Location | Check | Assessment |
| --- | --- | --- |
| `tools.py` signatures | SDK/Pydantic validates annotated strings, `Entity`, literals, and constrained integers for tool arguments. | STRUCTURAL declared tool schema; string annotations do not require nonempty values. |
| `tools.py:23–35` | NotImplemented becomes unsupported; HTTP/value errors become retrieval error. | **MASKS** validation, provider/API failures, malformed JSON, and result limits under broad statuses; original exceptions now logged. |
| `tools.py:42` | Search limit 1–50. | **REVIEW** chosen cap; duplicates downstream limit rules. |
| `tools.py:45–54` | Entity must map to a search operation; variant gets a special unsupported explanation. | STRUCTURAL current registry capability check; **REVIEW** variant-specific prose can become stale. |
| `tools.py:76,137–138` | Inspects result ID presence to distinguish successful retrieval from an error dictionary. | STRUCTURAL current return convention; possible consequence of mixing two return shapes. |
| `tools.py:78–83` | Missing transcripts default to empty; only existing id/name/location fields included; first 20 transcripts retained and truncation flagged. | **MASKS** absent fields; **REVIEW** 20-entry cap may hide a desired transcript from the model. |
| `tools.py:90–94,108–112` | Association page 1–100 (`MAX_NUM_PAGES`); flank 0–1,000,000; content full/summary only. | Shared page ceiling reused; **REVIEW** duplicate API validation and chosen flank maximum. |
| `tools.py:97–101,115–119,150–154,167–171` | Summary content selects summary operation; otherwise selects full. | STRUCTURAL dispatch after literal validation. |
| `tools.py:131–133,162–164` | Transcript/region content restricted to full/summary. | STRUCTURAL declared capability, potentially duplicate API restriction. |
| `tools.py:140–146` | Exact transcript-ID matching; requires exactly one match with truthy location, otherwise clarification. | **REVIEW** duplicate matches/missing locations can indicate data faults rather than a need for user clarification. Prevents silently choosing a different transcript/span. |
| `tools.py:175–184` | Phenotype tool always reports unsupported. | **REVIEW** static readiness assumption; no actual capability probe. |
| `tools.py:193–197` | OpenAPI search considers GET only; any casefolded query word must occur in path/summary. | **REVIEW** search policy; empty query returns no matches, not all operations. |
| `tools.py:203,215–222` | Summary cut to 300 chars; only present whitelisted parameter fields, first 12 parameters; stops at 10 matches. | **REVIEW** lossy caps; exactly 10 matches reported as truncated even if no more exist. |
| `tools.py:229,234–242` | Component literal validated; Presentation validated; stored dataset compatibility checked; ≥6 presentations rejected; value errors trigger model retry. | Component/reference checks support current UI contract; **REVIEW** six-presentation policy and duplicate limit in response schema. |
| `results.py:22–23` | Rejects add when 12 results already stored. | **REVIEW** prototype ceiling; also rejects replacement of an existing ID at capacity. |
| `results.py:29–30` | Result reference must exist in this run. | STRUCTURAL evidence ownership/reference integrity. |
| `results.py:37–54,64` | Preview first five rows; whitelisted fields; scalar values only; stringified length ≤300; first 20 sources. | **REVIEW** preview filtering can conceal relevant fields or identifiers without warning. |
| `results.py:59` | Emits annotation value if truthy, otherwise null. | STRUCTURAL search results have no annotation; not a missing-required-field fallback. |
| `results.py:72–77` | Source chart requires one of three entity/association pairs and summary content. | STRUCTURAL current chart contract; **REVIEW** manually maintained entity allowlist. |

### Data contracts, registry, telemetry, and export

| Location | Check | Assessment |
| --- | --- | --- |
| `contracts.py:19–67` | Pydantic checks all annotated enum/literal/container/field types; three models forbid extra fields. | STRUCTURAL contract enforcement; **REVIEW** schema duplication with tool inputs and SDK/frontend contracts. Nested row/parameter values remain `Any`; these are not domain-record validation. |
| `contracts.py:30–34` | Rows ≤100; page 1–100; limit 1–100; sources ≤100. | **REVIEW** local caps, partly inconsistent with 50-row conversion and 12-result policy. |
| `contracts.py:44–47` | Component two literals; result ID length ≥1; title ≤160; slot primary/secondary. | Reference/component selection is structural; **REVIEW** title cap and fixed slot vocabulary. Whitespace-only ID passes length check. |
| `contracts.py:55–67` | Version must be 2; status is one of seven literals; ≤12 result sets; ≤6 presentations. | Version/status contract is structural; **REVIEW** hard limits duplicate store/tool checks. |
| `operations.py:19–27` | AskOperation validates required endpoint/entity/nullable annotation/response configuration; object is frozen. | STRUCTURAL static registry definition. Nested ResponseConfiguration reuses shared types/validators; not new ASK-specific checks. |
| `operations.py:135–138` | Search registry includes only exact SearchMatch record-model identity. | **REVIEW** same exact-class assumption as retrieval conversion. |
| `telemetry.py:14–29` | Loads settings only if absent; distinguishes Pydantic errors for redacted logging; invalid config returns false; disabled telemetry or missing/empty token returns false. | Optional configuration handling; **MASKS** telemetry enabled with missing token looks like ordinary disabled telemetry. |
| `telemetry.py:31–46` | Content setting selects extra scrubbing; headers/full HTTP content/binary model content not captured. | Explicit logging policy rather than data rejection; **REVIEW** hand-selected scrubbing coverage. |
| `telemetry.py:49–53` | Every instrumentation exception is logged then converted to false. | **MASKS** failure and intentional disablement share return value. |
| `export_types.py:42–46` | CLI requires destination and converts it to Path. | STRUCTURAL CLI argument parsing. No additional empty/path/existence validation. |
| `__init__.py` | No validation or defaults. | Nothing to review. |

## Defaults and empty-value fallbacks

Repeated identical defaults are grouped with every use identified. Optional
annotations without a default are required nullable fields, not implicit `None`
defaults. Output literals, such as error statuses, are fixed result values rather
than missing-input defaults; relevant status fallback behavior is listed below.

| Location | Default/value supplied | Assessment |
| --- | --- | --- |
| `config.py:10–12` | `ASK_` prefix; `.env`; unknown fields ignored. | Configuration conventions; **MASKS** misspelled optional settings. |
| `config.py:14–17` | `model=None`, `api_key=None`. | Intentional optional configuration, rejected when building provider model. No empty-string defaults. |
| `config.py:18–23` | Requests 8; tools 12; API timeout 20s; deadline 90s; telemetry false; capture_content false. | **REVIEW** prototype execution/logging policies. |
| `agent.py:47,55–57` | Injected model None; retries 1; max_tokens 2000; parallel_tool_calls false; tool timeout inherited from settings. | Injection sentinel plus **REVIEW** execution policies. |
| `contracts.py:24` | Generated UUID result ID. | STRUCTURAL run-local reference creation; not a missing API identifier replacement. |
| `contracts.py:26–28`; `operations.py:26` | Annotation allows None but has no default. | Required nullable field. Search registry explicitly sets annotation None (`operations.py:34,42`). |
| `contracts.py:29–36` | Content FULL; rows `[]`; page 1; limit 50; has_more false; sources `[]`; parameters `{}`; warnings `[]`. | **MASKS** omitted rows/provenance/page metadata when constructing models without explicit values. `retrieve()` currently supplies all these fields; defaults matter to other/future constructors. |
| `contracts.py:46–47` | Title “Retrieved evidence”; slot primary. | **REVIEW** UI defaults. |
| `contracts.py:55–67` | Version 2; status ok; results `[]`; presentation `[]`; warnings `[]`. | **REVIEW / MASKS** default success with no results. Current completion code supplies status/results/presentation/warnings explicitly. |
| `results.py:17–18,36` | Store results `{}`; presentations `[]`; preview `[]`. | INIT: empty run state and preview accumulation. |
| `results.py:59` | Null annotation for a search result. | Intentional absence, not invented annotation data. |
| `api_client.py:39–40,68` | Chunks `[]`; byte counter 0; rows `[]`. | INIT: response and result accumulation. |
| `api_client.py:75` | `matched_record_details` missing or falsey → `{}`. | **MASKS** absent/null/invalid falsey details as no additional metadata. |
| `api_client.py:77` | Missing or falsey pagination → `{}`. | **MASKS** pagination availability. |
| `api_client.py:78` | Missing request page →1. | **REVIEW** duplicates API/tool page default; explicit null/invalid values still fail int conversion. |
| `api_client.py:79` | Missing total_pages → current page. | **MASKS** unknown continuation as no further API page. |
| `api_client.py:86` | Result limit always 50. | **REVIEW** fixed value regardless of requested/API limit or actual row count. |
| `api_client.py:91–94` | Source falls through track → id → source_id; missing lookups implicitly None. | **REVIEW / MASKS** inferred provenance and silent omission. |
| `api_client.py:96–105` | Nonapplicable warnings contribute `[]`. | INIT/conditional output: not a replacement for failed retrieval. |
| `tools.py:33–34,52–53,143,182–183` | Missing deps warnings/failures created with `setdefault(..., [])`. | **REVIEW** normal transport already initializes both; can conceal incomplete dependency wiring. Does not repair explicit None. |
| `tools.py:42,90–94,108–112,131–133,162–164` | Search limit 10; gene/variant page 1, flank 0; all association tools content FULL. | **REVIEW** chosen defaults; flank 0 and FULL affect query meaning. |
| `tools.py:78,140` | Missing row transcripts → `[]`. | **MASKS** missing structure as no transcripts. Explicit null is not repaired. |
| `tools.py:80,141–142` | Omit absent transcript fields; missing ID/location implicitly None. | **MASKS** schema omissions; selection failures become clarification. |
| `tools.py:190` | Operation matches `[]`. | INIT search accumulator. |
| `tools.py:191` | Missing OpenAPI paths → `{}`. | **MASKS** missing operation catalog as no matches. |
| `tools.py:195,203` | Missing operation summary → empty string. | **REVIEW** summary can be optional, but fallback suppresses evidence that searchable descriptions are absent. These are the explicit empty-string defaults in this package. |
| `tools.py:202,204` | Missing operationId/x-status → None through `.get()`. | **REVIEW** optional metadata; operationId absence may matter to callers. |
| `tools.py:217` | Missing parameters → `[]`; absent whitelisted parameter properties omitted. | **REVIEW** valid for a parameterless GET; **MASKS** if metadata was expected. |
| `tools.py:221–223` | Truncated false unless ten matches reached, then true. | **REVIEW** exactly-ten case assumes additional omitted matches. |
| `tools.py:229–230` | Component table; title “Retrieved evidence”. | **REVIEW** repeats Presentation defaults/registry policy. |
| `transport.py:26,32,44,48` | Missing messages/role/type/text → None via `.get()`. | STRUCTURAL missing-value detection; subsequently rejected or filtered, not converted to valid text. |
| `transport.py:29–30,40,100` | Clean messages `[]`; size 0; collected text parts `[]`; raw body empty bytearray. | INIT request accumulation. |
| `transport.py:37` | Missing parts → `[]`. | **MASKS** malformed message as no content, which may then be dropped. |
| `transport.py:56,59` | Generates new message/conversation UUIDs; trigger submit-message. | **REVIEW** rewrites client IDs and assumes submission trigger. |
| `transport.py:95–97` | FastAPI dependency providers for agent/transport/settings. | STRUCTURAL dependency injection, not data defaults. |
| `transport.py:113,117–118,157,198` | SDK version 7; OpenAPI catalog title/version; internal base URL; stream protocol v1 and no-cache. | Protocol/wiring constants; **REVIEW** version choices when SDK/client changes, not empty-data fallbacks. |
| `transport.py:121` | Deps warnings/failures `[]`. | INIT per-run state; store/spec explicitly provided. |
| `transport.py:124–127` | Falsey presentations → generated tables for first six results. | **REVIEW** manufactures a display selection rather than leaving it absent. |
| `transport.py:128–135` | First failure, else empty for all-empty existing results, else ok. | **REVIEW / MASKS** partial success and no-retrieval semantics. |
| `transport.py:148–152` | Header comprehension may produce `{}` if none present. | INIT/optional headers; no fabricated credentials. |
| `transport.py:168–169` | Run token budgets 20000 input, 12000 output. | **REVIEW** hardcoded execution limits. |
| `telemetry.py:12,31–46` | Settings None triggers load; patterns None when capture enabled, otherwise regex list; send only with token; capture_headers/capture_all/include_binary_content false. | Explicit optional/instrumentation policy; None means no extra regex patterns, not “no SDK scrubbing.” |
| `telemetry.py:28` | Missing LOGFIRE_TOKEN → None via getenv; falsey token disables telemetry. | **MASKS** enabled-but-unconfigured telemetry. |
| `telemetry.py:27,29,53` | False for config error, disabled/missing token, or instrumentation error. | **MASKS** distinct states into the same return value. |
| `operations.py:35–130` | Most ResponseConfiguration objects omit format/content/UI, inheriting JSON/FULL/DEFAULT; summary operations explicitly set SUMMARY. | Reused shared defaults; **REVIEW** whether these presentation/format fields are needed by this registry. |
| `export_types.py:22–38` | Enum/registry comprehensions; output lines initialized with generated-file comment. | Output construction, not empty-data fallback. No optional destination/default path. |

## Non-runtime constraints in the agent prompt

`agent.py:21–44` also instructs the model to use registered tools and retrieved
evidence only; treat retrieved text as data; avoid invented results/code;
separate empty retrieval from failures; request clarification for disease/transcript
ambiguity; preserve exact transcript selection and provenance; distinguish
semantic similarity, proximity, and association; re-fetch follow-up evidence; and
use the operation catalog for API help. These are behavioral instructions, not
Python validators. Statements that variant semantic search, phenotype retrieval,
or predicted-impact infrastructure are unavailable are **REVIEW** capability
assumptions that can become stale.

## Review boundary and verification

All 12 Python modules were inspected, including the empty package initializer.
Shared sanitization, identifier validation, response configuration, and base-model
behavior were consulted only where directly used. This is not an inventory of
every transitive Pydantic/SDK/domain validator. No requirement for prototype caps
or fallback semantics was established by this review; such values remain flagged
for decision. No application-code edits, tests, database access, or provider calls
were performed for this inventory.
