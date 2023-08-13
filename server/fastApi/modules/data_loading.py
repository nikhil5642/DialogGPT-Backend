from fastapi import APIRouter
from src.DataBaseConstants import RESULT, SUCCESS
from pydantic import BaseModel

from src.data_sources.urls_loader import get_all_urls_mapping

router = APIRouter(prefix="/load")

class UrlLoader(BaseModel):
    sourceURL: str

@router.post("/urlLoader")
async def urlLoader(data: UrlLoader):
    urlMappings=get_all_urls_mapping(data.sourceURL)
    

