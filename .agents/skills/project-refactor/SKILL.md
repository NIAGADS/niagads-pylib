---
name: project-refactor
description: >
    Enforce strict change boundaries when working on incremental refactoring
    branches. Apply automatically on branches named "refactor" or starting
    with "refactor/". These branches contain intentionally incomplete
    migrations, obsolete implementations, and temporarily incompatible code.
    Prevent unsolicited changes, unrelated error reporting, and attempts
    to reconcile legacy and refactored implementations.
---

# Project Refactor

## Purpose

Support incremental, controlled refactoring of an existing codebase
without assuming that the entire project must remain consistent,
functional, or compatible throughout the process.

Refactoring branches are works in progress, not necessarily stable
development environments.

## Activation

Apply this skill whenever the current Git branch is `refactor` or
starts with `refactor/`.

Check the current branch before beginning work. Do not require the
user to explicitly invoke this skill.

These rules supplement existing project instructions. Where general
project instructions encourage broad cleanup, consistency, or
validation, the restrictions in this skill take precedence.

## 1. Strict Scope Enforcement

- Modify only the files, functions, classes, or components necessary
  to complete the user's explicit request.
- Do not expand the scope to address unrelated problems discovered
  during implementation.
- Track unrelated issues discovered incidentally during implementation
  without investigating or modifying them.
- Upon completion of the requested work, briefly summarize these issues
  in a separate "Follow-up Considerations" section, including specific
  examples, file paths, and line numbers where available.
- Do not perform additional analysis solely to populate this section.
- Omit the section if no unrelated issues were identified.
- Do not perform opportunistic cleanup, formatting, modernization,
  optimization, or bug fixes.
- Do not modify adjacent code merely to improve consistency.
- Do not update other callers or consumers unless explicitly requested
  or strictly necessary for the requested change.
- If a necessary change falls outside the requested scope, explain
  the dependency and request authorization before proceeding.
- Never treat access to a file as authorization to refactor its
  unrelated contents.

## 2. Legacy and Refactored Code Must Remain Distinct

Assume the repository may contain:

- Legacy implementations awaiting migration.
- Partially refactored implementations.
- New implementations replacing legacy patterns.
- Temporarily duplicated functionality.
- Incompatible interfaces and dependencies.
- Dead or obsolete code not yet removed.

Rules:

- Do not assume all code should follow the same architecture.
- Do not infer intended behavior from unrelated legacy code.
- Do not apply new patterns to legacy implementations unless requested.
- Do not restore deprecated patterns to make refactored code compatible.
- Do not reconcile conflicting implementations without explicit instructions.
- Preserve existing legacy behavior unless its modification is requested.
- Use the conventions and architecture of the target implementation,
  not necessarily those of the surrounding repository.

When the intended implementation is ambiguous, identify the ambiguity
rather than making assumptions based on other parts of the codebase.

## 3. Incomplete Refactoring Is Expected

Treat incomplete migration as an intentional project state.

The following are not, by themselves, reasons to modify code or
report defects:

- Broken imports in files outside the requested scope.
- References to renamed or removed APIs.
- Missing implementations in unmigrated modules.
- Incompatible method signatures between old and new code.
- Incomplete dependency migrations.
- Failing tests for unrelated functionality.
- Unused legacy methods, classes, or imports.
- Inconsistent patterns across migrated and unmigrated modules.

Do not attempt to make the entire repository build, type-check, or
pass tests unless explicitly instructed.

## 4. Error Reporting and Validation

Validation must be relevant to the requested change.

- Prioritize targeted validation of modified code.
- Do not run repository-wide validation by default.
- Do not report unrelated pre-existing errors.
- Do not diagnose or investigate failures in unmigrated modules
  unless specifically requested.
- Distinguish errors introduced by the current changes from
  existing incompatibilities caused by ongoing refactoring.
- If broader validation is explicitly requested, report relevant
  results separately from known or suspected migration-related
  failures.
- Never claim the entire project is valid based only on targeted
  checks.

Report an out-of-scope problem only when it directly blocks the
requested work or presents a material risk introduced by the change.

## 5. Dependency and Impact Analysis

Before making changes:

1. Identify the precise requested behavior and target code.
2. Inspect the relevant implementation and its immediate dependencies.
3. Determine which existing conventions apply to the target code.
4. Establish the minimum necessary modification scope.

Do not interpret dependency discovery as permission to modify
everything that depends on the target implementation.

If the change requires a broader migration, stop at the requested
boundary and identify the additional work needed.

## 6. Code Reuse and Architecture

- Prefer existing utilities, mixins, base classes, models, and helpers
  when they are appropriate to the target architecture.
- Do not assume that legacy implementations represent the desired
  architecture.
- Do not copy obsolete patterns merely because they occur elsewhere.
- Do not modify shared abstractions to accommodate legacy consumers
  unless explicitly requested.
- Where new and old behaviors must coexist, prefer a scoped adapter
  or wrapper over altering shared behavior, when appropriate.
- Do not introduce compatibility layers or temporary shims without
  a demonstrated requirement.

## 7. Change Discipline

- Keep diffs minimal and directly attributable to the request.
- Preserve unrelated code, comments, and formatting.
- Avoid file-wide formatting when changing a small section.
- Do not delete obsolete code unless specifically instructed.
- Do not change public interfaces or exports beyond the requested
  scope.
- Do not add speculative defensive code for hypothetical migration
  problems.
- Do not silently expand the implementation to resolve downstream
  compatibility issues.

Before completing, review the diff and remove any changes that
cannot be justified by the explicit request.

## 8. Communication

Keep responses focused on the requested task.

Report:

- What was changed.
- Whether targeted validation succeeded, failed, or was not run.
- Any direct blockers preventing completion.

Do not provide unsolicited lists of:

- Existing repository-wide errors.
- Unmigrated modules.
- Architectural inconsistencies.
- Unrelated technical debt.
- Suggested additional refactors.

Do not turn a narrowly scoped request into a general code review.

## 9. API Test Maintenance

When modifying API endpoints, request/response models, dependencies,
or other API behavior, update the corresponding pytest tests as needed.

- Identify existing tests associated with the modified API functionality.
- Update tests to reflect the intended refactored behavior, including
  changes to routes, parameters, schemas, responses, and dependencies.
- Add tests for new API functionality when appropriate.
- Remove or replace obsolete test expectations only when directly
  related to the requested changes.
- Preserve unrelated tests, including those targeting legacy APIs
  awaiting refactoring.
- Do not modify production code solely to make obsolete tests pass.
- Run relevant targeted tests when feasible.
- Do not attempt to resolve failures caused by unrelated or incomplete
  refactoring work.
- Report targeted test results and any validation limitations.

Test maintenance is considered part of the authorized scope for API
changes, but must remain limited to the functionality being modified.

## Governing Principle

**An incomplete refactor is not an invitation to repair the project.**

The user's explicit request defines the authorized scope of work.
Preserve everything outside that scope unless further changes are
strictly necessary and authorized.
