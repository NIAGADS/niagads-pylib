from fastapi import Path
from api.common.formatters import clean

async def forwarding_request_param(forwardingRequestId: str = Path(
    description="unique ID for the forwarding request; valid for 1 hr after initial request is made")) -> str:
    return clean(forwardingRequestId)
