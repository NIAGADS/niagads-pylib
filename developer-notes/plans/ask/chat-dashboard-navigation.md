# ASK chat and dashboard navigation implementation plan

> Execute inline using Superpowers executing-plans. User approved the in-chat
> design and explicitly requested implementation on feature branches.

Goal: keep chat concise and move record lists and plots to a temporary dashboard.
Branches: codex/ask-chat-dashboard-navigation from refactor/api (Python) and
app/oa-api (frontend). Never main. Preserve user changes, feedback and diagnostics.

## Approved design

- Each user/assistant message is a Card; assistant narrative is a brief summary.
- Single gene/variant/track record lookups use API summary models and summary
  cards with a fixed, frontend-generated link to fetch full API JSON.
- Lists, associations and plots belong on /dashboard/{id}; chat links there.
- One generated ID per current conversation; in-memory client state survives
  same-tab route navigation, including chat messages and fetched track panels.
  Refresh/close/new session clears state. Unknown IDs show unavailable explicitly.
- Follow-ups retrieve fresh evidence and append panels to the same dashboard.
  Earlier panels are retained; no automatic cross-panel replacement/filtering.
- Raw records plus provenance have a Download JSON action independent of adapters.
  Downloads contain only retrieved pages, not implied complete database results.
- Render safe Markdown prose. Do not render raw HTML or inline data tables.
- Preserve v4, frontend-owned adapters, scientific measures, source/page/failure
  metadata, max-five track selection, feedback and text-only model history.

## Tasks

- [x] Python: change only ASK operation configs for record summaries and pass
  configured content to record requests; add concise-answer/no-record-dump rules.
  No SQL, ORM, ETL, embeddings, semantic retrieval or planning changes.
- [x] Frontend: persistent root AskSessionProvider owns useChat, current dashboard
  ID, draft and fetched-track batches; Chat renders cards, Markdown, record cards,
  diagnostic summaries and dashboard links without tables/charts.
- [x] Add /dashboard/[id], reuse Results only there, retain raw result download
  outside component boundaries; record cards remain cards on dashboard too.
- [x] Add fixed full-record proxy for supported entities, forwarding auth/errors
  using API_INTERNAL_URL. No model-generated upstream URL or arbitrary proxy.
- [x] Add Markdown dependency with raw HTML disabled, safe links and table notice.
- [x] Verify TypeScript/lint, Python parse/style/schema and focused diffs; review
  changes inline; update handoffs; commit/push both branches.

## Review focus and verification limits

Route changes must retain conversation, result references and fetched data.
Unknown dashboard IDs and failed adapters must retain explicit notices/downloads.
Single-record summary cards must distinguish false/zero/null and avoid invented
fields; association/search lists remain lists even when one row is returned.
Reusing retrieved evidence in the UI must not make it trusted model history.
No synthetic tests; no test execution or live database/model requests. Static
checks and any replay of the user's captured real response are reported separately
from live validation. No persistence, user authentication or shared dashboards.

## Execution ledger

Implemented inline, with no synthetic tests or live database/model requests.
Python parse/import/response schema/Black/isort passed; frontend TypeScript and
targeted ESLint passed before the captured-stream rendering correction. Markdown
dependencies installed with existing npm 12.0.2 and a writable temporary cache.

Corrected existing ActionButton native prop typing so feedback disabled controls
type-check; rebuilt UI with inherited deprecated Card/declaration-alias warnings.
No runtime API or unrelated UI behavior was changed.

Browser replay uses the actual stream uploaded by the user, with a local HTTP
replay server and Chromium; it makes no database or model calls. It exposed the
real rendering failure: matched_text is JSON-encoded text and the Table infers
cell configuration from JSON-looking strings. The frontend translator now wraps
string values explicitly, including string lists and category-summary terms.
Original evidence is untouched. Final full TypeScript and targeted ESLint passed
after this correction, as did Python Black/isort and both diff whitespace checks.

Chromium replay of the actual uploaded stream verified two conversation Cards,
no chat table, a generated dashboard link, and a dashboard Table with all ten
track rows. Selecting five tracks leaves the other five disabled. Back to chat
retains both messages and the same dashboard ID. Download JSON produced the
retrieved result with ten rows, identical to the original captured result.
This is a captured-response browser check, not live model/database validation.
Single-record summary rendering/full-record retrieval and future model adherence
still require local review with actual corresponding API responses.

Final inline review checked context lifetime, result ownership, raw-download
placement outside adapter boundaries, fixed proxy paths/auth forwarding, native
diagnostics, null/false values and preservation of scientific strings. No tests
or independent subagents were launched, following repository/user constraints.
