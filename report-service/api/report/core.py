from api.report.reports import local_router
from fastapi import APIRouter

report_router = APIRouter(
    prefix="/api/report",
    tags=["report"],
)


for router in [local_router]:
    report_router.include_router(router=router)
