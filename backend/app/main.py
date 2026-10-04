from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.reading import router as reading_router
from app.api.v1.listening import router as listening_router
from app.api.v1.writing import router as writing_router
from app.api.v1.speaking import router as speaking_router

app = FastAPI(
    title="AI IELTS Coach API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")


def health_response():
    return {
        "status": "healthy",
        "service": "AI IELTS Coach API"
    }


@app.get("/health")
def health_check():
    return health_response()


@app.get("/api/health")
def api_health_check():
    return health_response()


app.include_router(reading_router, prefix="/api/v1")
app.include_router(listening_router, prefix="/api/v1")
app.include_router(writing_router, prefix="/api/v1")
app.include_router(speaking_router, prefix="/api/v1")
