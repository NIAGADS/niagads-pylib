from fastapi import Query

async def variant_identifier_param(variant: str = Query(regex="", description="")):
    return True


