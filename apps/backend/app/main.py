import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Smart Academic AI API",
    description="Multi-tenant Academic Intelligence & Personalized Learning Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_correlation_id_middleware(request: Request, call_next):
    """Inject correlation X-Request-ID into request state and response headers."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Include API v1 routes
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Smart Academic AI Backend API",
        "docs": "/docs",
        "health": "/api/v1/health"
    }
