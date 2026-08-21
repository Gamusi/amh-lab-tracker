import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import get_current_user
from ..parsers.nihon_kohden import parse_nihon_kohden_output

logger = logging.getLogger("amh_integrations")

router = APIRouter(tags=["Analyzer Integrations"])

class AnalyzerParseRequest(BaseModel):
    analyzer_type: str = "nihon_kohden"
    raw_text: str

@router.post("/api/integrations/parse-analyzer-output")
def parse_analyzer_output(
    req: AnalyzerParseRequest,
    current_user: dict = Depends(get_current_user)
):
    logger.info(f"User '{current_user['username']}' requested parse for analyzer '{req.analyzer_type}'")
    logger.debug(f"raw_text length={len(req.raw_text)}, preview={req.raw_text[:200]!r}")

    
    if req.analyzer_type == "nihon_kohden":
        result = parse_nihon_kohden_output(req.raw_text)
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("detail", "Failed to parse Nihon Kohden output")
            )
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported analyzer type '{req.analyzer_type}'"
        )
