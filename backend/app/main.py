from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import settings

app = FastAPI(
    title="LIFELINK Emergency Coordination API",
    description="Explainable, safety-gated community-first emergency coordination layer",
    version="1.0.0",
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [
        "https://*.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Enforce standardized error envelope across all unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )


# Mount API routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "LIFELINK API",
        "version": "1.0.0",
        "status": "online",
        "health": "/api/v1/health",
    }
