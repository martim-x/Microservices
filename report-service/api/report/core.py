from fastapi import APIRouter

report_router = APIRouter(
    prefix="/api/report",
    tags=["report"],
)
