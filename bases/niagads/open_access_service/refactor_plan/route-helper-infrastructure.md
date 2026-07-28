# Route Helper Infrastructure Refactor Plan

## Goal

Keep routes simple while splitting the current route helper stack into clearer logical components.

Routes should still call one endpoint-facing service. They should not need to pass around many helper objects.

## Implementation and Planning Rules & Guidelines

    - respect existing code patterns especially for encapsulation (private v protected members).  
    - no added bloat.  do not add wrappers, getters, setters, etc that were not in the original design without asking or giving good justification beyond boilerplate.  
    - keep answers short, brief.  I dont' need to be taught.  
    - only do what I ask do not go further and anticiapte needs and use cases that don't exist

## Core Naming

- `RouteHelperService` -> `EndpointService`
- `Parameters` -> `RequestParameters`
- `MetadataRouteHelperService` -> `MetadataEndpointService`
- `FILERRouteHelper` -> `FILEREndpointService`
- `GenomicsRouteHelper` -> `GenomicsEndpointService`
- `ApiWrapperService` -> `FILERClient`

## Shared Components

- `ResponseConfiguration`
  - Keep as the response parameter/config model.

- `RequestParameters`
  - Arbitrary request parameter container used by endpoint services.

- `CacheService`
  - Cache reads/writes.
  - Cache key variants for raw responses, views, and content variants.

- `PaginationService`
  - Page validation.
  - Offset calculation.
  - Result slicing.
  - Max-page enforcement.

- `RepresentationService`
  - Response model construction.
  - Request metadata injection.
  - Table response generation.

- `LocationResolver`
  - Feature/span/location normalization.

## Endpoint Services

- `EndpointService`
  - Generic route-facing coordinator.
  - Owns shared request state: managers, response configuration, request parameters.
  - Delegates cache, pagination, representation, and location logic to shared components.

- `MetadataEndpointService`
  - Coordinates track metadata lookup/search.
  - Uses `MetadataQueryService`.
  - Uses shared cache, pagination, and representation components.

- `FILEREndpointService`
  - FILER-specific workflow.
  - Metadata precheck.
  - Count estimation.
  - Upstream FILER retrieval.
  - Cross-track result merging.

- `GenomicsEndpointService`
  - GenomicsDB-specific workflow.
  - Query execution.
  - Feature annotation workflows.

## FILER-Specific Components

- `FILERClient`
  - Raw upstream FILER HTTP calls only.

- `FILERTrackDataPaginator`
  - Optional later extraction.
  - Only add this if cross-track cursor pagination remains complex after the first pass.

## Migration Order

1. Rename `Parameters` to `RequestParameters`.
2. Extract pagination from `RouteHelperService`.
3. Extract response generation from `RouteHelperService`.
4. Extract cache helpers.
5. Rename `RouteHelperService` to `EndpointService`.
6. Rename `MetadataRouteHelperService` to `MetadataEndpointService`.
7. Rename `FILERRouteHelper` and `GenomicsRouteHelper`.
8. Rename `ApiWrapperService` to `FILERClient`.
9. Decide whether FILER track-data pagination needs its own class.

## Rules

- Routes call one endpoint service.
- Endpoint services orchestrate workflows.
- Query services fetch data.
- Representation service shapes responses.
- Cache, pagination, and location handling stay shared infrastructure.
