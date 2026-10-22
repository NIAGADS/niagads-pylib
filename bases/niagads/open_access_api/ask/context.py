"""Run-local, lossless evidence bookkeeping for completed tool exchanges."""

from dataclasses import replace
from uuid import uuid4

from niagads.common.core import ComponentBaseMixin
from niagads.open_access_api.ask.results import ResultStore
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_core import to_json, to_jsonable_python


class _WorkingContext(ComponentBaseMixin):
    """Keep snapshot ownership and outcomes in server deps for this run only."""

    def __init__(self, store: ResultStore):
        super().__init__()
        self._store = store
        self._marker = str(uuid4())
        self._results: dict[str, dict] = {}
        self._exchanges: dict[str, dict] = {}
        self._message: ModelRequest | None = None
        self._body: str | None = None

    def owns(self, message: ModelMessage) -> bool:
        """Never recognize snapshots by a user-supplied text prefix or metadata alone."""
        return (
            message is self._message
            and (message.metadata or {}).get("ask_working_context") == self._marker
            and len(message.parts) == 1
            and isinstance(message.parts[0], UserPromptPart)
            and message.parts[0].content == self._body
        )


def compact_history(
    ctx: RunContext[dict], messages: list[ModelMessage]
) -> list[ModelMessage]:
    """Fold complete, unambiguous exchanges only when serialized history gets smaller.

    Original user/assistant text and unresolved/retry exchanges remain. Internal
    reasoning accompanying fully completed calls is discarded with those calls.
    This does not recover spent tokens or create cross-turn model memory.
    """
    store = ctx.deps.get("store")
    if not isinstance(store, ResultStore):
        return messages
    state = ctx.deps.get("_ask_working_context")
    if not isinstance(state, _WorkingContext) or state._store is not store:
        state = _WorkingContext(store)
    calls: dict[str, list[ToolCallPart]] = {}
    returns: dict[str, list[tuple[int, ToolReturnPart]]] = {}
    retries = set()
    for index, message in enumerate(messages):
        for part in message.parts:
            if isinstance(part, ToolCallPart):
                calls.setdefault(part.tool_call_id, []).append(part)
            elif (
                isinstance(part, ToolReturnPart)
                and isinstance(message, ModelRequest)
                and message.state == "complete"
            ):
                returns.setdefault(part.tool_call_id, []).append((index, part))
            elif isinstance(part, RetryPromptPart):
                retries.add(part.tool_call_id)

    results = dict(state._results)
    exchanges = dict(state._exchanges)
    folded = set()
    response_indexes = set()
    for index, message in enumerate(messages):
        if not isinstance(message, ModelResponse):
            continue
        parts = [part for part in message.parts if isinstance(part, ToolCallPart)]
        if not parts or any(
            not isinstance(part, (ToolCallPart, TextPart, ThinkingPart))
            for part in message.parts
        ):
            continue
        group = []
        for call in parts:
            key = call.tool_call_id
            matches = returns.get(key, [])
            if len(calls[key]) != 1 or len(matches) != 1 or key in retries:
                break
            returned_index, returned = matches[0]
            if returned_index <= index or returned.tool_name != call.tool_name:
                break
            try:
                outcome = {"tool": call.tool_name, "arguments": call.args_as_dict()}
                content = returned.model_response_object()
                result_id = content.get("result_id")
                evidence = None
                if isinstance(result_id, str):
                    if result_id not in store.results:
                        break
                    evidence = store.summary(
                        result_id,
                        gene_evidence=content.get("evidence_fields", ()),
                        transcript=content.get("requested_transcript"),
                    )
                    if result_id in results and results[result_id] != evidence:
                        break
                    outcome["result_id"] = result_id
                    details = {
                        key: value
                        for key, value in content.items()
                        if key not in evidence or evidence[key] != value
                    }
                    if details:
                        outcome["details"] = details
                else:
                    outcome["output"] = content
                if returned.outcome != "success":
                    outcome["outcome"] = returned.outcome
                # Unsupported multimodal/non-JSON outcomes stay in their original exchange.
                to_json(outcome)
            except (ValueError, TypeError):
                break
            if key in exchanges and exchanges[key] != outcome:
                break
            group.append((key, outcome, result_id, evidence))
        else:
            for key, outcome, result_id, evidence in group:
                folded.add(key)
                exchanges[key] = outcome
                if evidence is not None:
                    results[result_id] = evidence
            response_indexes.add(index)

    if not folded:
        return messages
    payload = {
        "kind": "ask_working_context",
        "results": results,
        "exchanges": list(exchanges.values()),
        "presentation": [
            intent.model_dump(mode="json") for intent in store.presentations
        ],
        "issues": to_jsonable_python(ctx.deps.get("issues", [])),
        "warnings": ctx.deps.get("warnings", []),
        "failures": ctx.deps.get("failures", []),
    }
    body = to_json(payload).decode()
    snapshot = ModelRequest(
        parts=[UserPromptPart(body)],
        metadata={"ask_working_context": state._marker},
        instructions=next(
            (
                message.instructions
                for message in reversed(messages)
                if isinstance(message, ModelRequest)
                and message.instructions is not None
            ),
            None,
        ),
    )
    compacted = []
    snapshot_index = max(returns[key][0][0] for key in folded)
    for index, message in enumerate(messages):
        if state.owns(message):
            continue
        if index in response_indexes:
            text = [part for part in message.parts if isinstance(part, TextPart)]
            if text:
                compacted.append(replace(message, parts=text))
        elif isinstance(message, ModelRequest):
            parts = [
                part
                for part in message.parts
                if not (
                    isinstance(part, ToolReturnPart) and part.tool_call_id in folded
                )
            ]
            if parts:
                compacted.append(
                    replace(message, parts=parts)
                    if len(parts) != len(message.parts)
                    else message
                )
        else:
            compacted.append(message)
        if index == snapshot_index:
            compacted.append(snapshot)
    if len(ModelMessagesTypeAdapter.dump_json(compacted)) >= len(
        ModelMessagesTypeAdapter.dump_json(messages)
    ):
        return messages
    state._results = results
    state._exchanges = exchanges
    state._message = snapshot
    state._body = body
    ctx.deps["_ask_working_context"] = state
    return compacted
