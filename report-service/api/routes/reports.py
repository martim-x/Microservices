from api.app import mq_router
from database.schemas import ReportOut

reports: list[ReportOut] = []


@mq_router.get("/reports")
def get_reports():
    return reports
