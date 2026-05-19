from fastapi import Request
from services.a_message_queue_service import AMessageQueueService


def get_message_queue_service(request: Request) -> AMessageQueueService:
    return request.app.state.message_queue_service
