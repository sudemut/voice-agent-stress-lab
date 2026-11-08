from fastapi import FastAPI

from app.api.orders import router as order_router


def create_app():
    app = FastAPI(title="Voice Agent Stress Lab")
    app.include_router(order_router)
    return app
