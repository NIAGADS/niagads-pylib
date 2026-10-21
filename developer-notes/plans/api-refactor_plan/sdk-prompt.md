# Task: Generate and Integrate API Client SDKs

Generate Python and TypeScript client SDKs for the NIAGADS Open Access API using its FastAPI-generated OpenAPI specification.

The SDKs will be maintained in two existing monorepos:

- **Python monorepo:** Python client, publishable to PyPI.
- **JavaScript/Next.js monorepo:** TypeScript client, publishable to npm.

## 1. Discovery

Before implementing:

- Inspect both monorepos, their existing package structures, build configurations, dependencies, and publishing conventions.
- Locate the FastAPI OpenAPI specification and determine how it can be exported reproducibly.
- Review existing API clients, shared utilities, models, and HTTP request wrappers to avoid duplicating functionality.
- Inspect relevant `AGENTS.md` files and project conventions.
- Identify the appropriate package names and locations based on existing conventions.

Do not restructure either monorepo.

## 2. SDK Generation

Use established OpenAPI client generators rather than implementing clients manually.

Evaluate suitable generators, including:

- Python: `openapi-python-client` or OpenAPI Generator.
- TypeScript: OpenAPI Generator or another well-maintained TypeScript generator.

Prefer generators that produce:

- Typed request and response models.
- Methods corresponding to API operations.
- Support for query parameters, pagination, and response formats.
- Configurable API base URLs.
- Standard HTTP error handling.
- Minimal runtime dependencies.

Ensure that generated method names are derived from stable OpenAPI `operationId` values.

Do not modify existing FastAPI endpoints or response models merely to accommodate SDK generation. Report any OpenAPI specification issues that prevent correct generation.

## 3. Monorepo Integration

Integrate each SDK as an independent package within its corresponding monorepo.

Requirements:

- Follow existing package naming, directory structure, and packaging conventions.
- Keep generated code separate from handwritten extensions and configuration.
- Avoid unnecessary dependencies and abstraction layers.
- Ensure SDK packages can be imported and used independently of the API server.
- Support local development and eventual publication to PyPI and npm.
- Preserve existing monorepo functionality.

Do not duplicate backend business logic in the SDKs.

## 4. Reproducible Generation

Provide a straightforward regeneration workflow for both SDKs.

- Pin generator versions.
- Store necessary generator configurations in version control.
- Generate clients from the same authoritative OpenAPI specification.
- Ensure regeneration is deterministic and does not overwrite handwritten code.
- Document how to regenerate the SDKs after an API specification change.

Avoid introducing unnecessary CI/CD infrastructure.

## 5. Testing

Add appropriate tests to verify:

- Correct request URLs and query parameter serialization.
- Request and response model handling.
- API configuration and base URL overrides.
- Error handling.
- Representative endpoints, including single-record lookups, multi-record lookups, and searches.

Use mocked HTTP responses. Do not require a running production API.

Integrate tests with the existing monorepo test frameworks.

## 6. Packaging and Documentation

Prepare both packages for publishing:

- PyPI package metadata and build configuration.
- npm package metadata, exports, and TypeScript declarations.
- Appropriate package dependencies.
- Minimal README documentation with installation and usage examples.
- Instructions for building, testing, regenerating, and publishing each package.

Do not publish packages or create releases.

## 7. Implementation Constraints

- Follow existing project conventions and `AGENTS.md` instructions.
- Reuse existing components and utilities where appropriate.
- Do not modify unrelated code.
- Do not refactor legacy components as part of this task.
- Avoid changes to API behavior.
- Prefer minimal, maintainable configurations over custom tooling.
- If an issue outside the task scope is discovered, report it rather than changing unrelated files.

## 8. Completion Report

Upon completion, provide:

1. SDK package names and locations.
2. Selected generators and reasons for selection.
3. Files created or modified.
4. Commands to regenerate, build, and test each SDK.
5. Test results.
6. Any OpenAPI specification limitations or issues requiring follow-up.
7. Remaining steps before publishing to PyPI and npm.

**Important:** Begin with a brief implementation plan based on the actual repository structures. Do not assume package locations or existing build conventions. Then proceed with implementation within the stated scope.
