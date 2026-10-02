from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.reading import router as reading_router
from app.api.v1.listening import router as listening_router

app = FastAPI(
    title="AI IELTS Coach API",
    version="1.0.0"
)


app.include_router(
    auth_router,
    prefix="/api/v1"
)

app.include_router(
    users_router,
    prefix="/api/v1"
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI IELTS Coach API"
    }

app.include_router(
    reading_router,
    prefix="/api/v1",
)

app.include_router(
    listening_router,
    prefix="/api/v1",
)