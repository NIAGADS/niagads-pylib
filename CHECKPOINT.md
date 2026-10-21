# ASK answer feedback checkpoint

Implementation added across niagads-pylib and niagads-viz-monorepo:

- Python ASK config, response contract, telemetry availability, streaming context,
  and `/ask/feedback` endpoint; new `ask/feedback.py` signs references and emits
  Logfire feedback events.
- Client response contract, `Feedback.tsx`, Chat integration, styles, and
  `/api/ask/feedback` proxy.
- Added backend feedback tests and client schema/proxy tests, all unrun.
- Replaced the signing-secret ENV setting with `ASK_FEEDBACK_ENABLE`; both API
  runtime ENV samples set TRUE. The signing key is derived automatically from
  the existing Logfire token using a feedback-specific HMAC label, so workers
  using the same token share it without extra configuration or secret files.
  Updated documentation and the unrun backend tests for the explicit flag.

No tests, checks, or final diff review performed, as requested. No credentials,
database, flat-file feedback store, or chat memory added.

Next step: when the user returns, review the implementation diff in both repos.
Then, only with authorization, run focused checks and feedback tests. Verify in
the browser that completed answers show rating controls, either selection opens
the comment form, successful submission shows confirmation and prevents another
submission, failure preserves input for retry, and absent telemetry hides controls.
Verify a submitted event links to the original response trace in Logfire.

User requested deferring review/checks for approximately 1 hour 15 minutes.
No platform usage reset time is known. No automatic resumption is scheduled.
