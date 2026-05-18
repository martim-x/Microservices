from fastapi import APIRouter

auth_router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)
