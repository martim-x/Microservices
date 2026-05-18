from api.report.core import report_router
from database.schemas import ReportOut

reports: list[ReportOut] = []


@report_router.get("/reports")
def get_reports():
    return reports
