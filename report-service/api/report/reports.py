from api.dependencies.services import get_message_queue_service
from fastapi import APIRouter, Depends
from services.a_message_queue_service import AMessageQueueService

local_router = APIRouter(prefix="")


@local_router.get("/reports")
def get_reports(
    message_queue_service: AMessageQueueService = Depends(get_message_queue_service),
):
    return message_queue_service.generated_reports
