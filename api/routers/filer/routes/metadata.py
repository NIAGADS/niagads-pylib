


@router.get("/record", tags=tags, response_model=TrackResponse,
    name="Get metadata for multiple tracks",
    description="retrieve metadata for one or more functional genomics tracks from FILER")
async def get_track_metadata(
        request: Request,
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request),
        format: str= Depends(format_param)) -> TrackResponse:
    
    result: List[Track] = await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned
    
    if format == ResponseType.JSON:
        return TrackResponse(request=requestData, response=result)
    else:
        # FIXME: cache in memory store; revisit when caching is set up
        request.session[requestData.request_id + '_response'] = [t.serialize(promoteObjs=True, collapseUrls=True) for t in result]
        request.session[requestData.request_id + '_request'] = requestData.serialize()
        redirectUrl = f'/view/table/filer_track?forwardingRequestId={requestData.request_id}'
        return RedirectResponse(url=redirectUrl, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/browser", tags=tags,  response_model=GenomeBrowserConfigResponse,
    name="Get Genome Browser configuration for multiple tracks",
    description="retrieve NIAGADS Genome Browser track configuration of session file for one or more functional genomics tracks from FILER")
async def get_track_browser_config(
        session: Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)], 
        track: Annotated[str, Query(description="comma separated list of one or more FILER track identifiers")],
        requestData: RequestDataModel = Depends(RequestDataModel.from_request)) -> GenomeBrowserConfigResponse:
    result = await MetadataQueryService(session).get_track_metadata(convert_str2list(track)) # b/c its been cleaned
    return GenomeBrowserConfigResponse(request=requestData, response=result)