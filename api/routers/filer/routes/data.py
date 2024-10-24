

@router.get("/data", tags=tags,
    name="Get data from multiple tracks",
    description="retrieve data from one or more functional genomics tracks from FILER in the specified region")
async def get_track_data(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        apiWrapperService: Annotated[ApiWrapperService, Depends(ApiWrapperService)],
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        span: str=Depends(span_param)):

    assembly = await MetadataQueryService(session).get_genome_build(convert_str2list(track), validate=True)
    if isinstance(assembly, dict):
        raise ValueError(f'Tracks map to multiple assemblies; please query GRCh37 and GRCh38 data independently')
        # TODO: return assembly -> track mapping in error message and/or suggest endpoint to query to get the mapping
        
    return apiWrapperService.get_track_hits(clean(track), span)