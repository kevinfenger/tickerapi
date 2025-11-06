from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints.scores import router as scores_router
import os
import redis

app = FastAPI(
    title="Sports Scores API",
    description="Real-time sports scores and team data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scores_router, prefix="/api", tags=["scores"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Sports Scores API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Health check endpoint for load balancers and monitoring"""
    try:
        # Check Redis connection
        from app.core.cache import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "environment": os.getenv("ENV", "development"),
        "redis": redis_status,
        "version": "1.0.0"
    }