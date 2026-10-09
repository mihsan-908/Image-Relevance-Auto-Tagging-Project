from fastapi import FastAPI
from .config import Settings, get_settings

from app.routes.review_routes import router as review_router
from app.routes.job_routes import router as job_router
from app.routes.cost_routes import router as cost_router

# Create a FastAPI instance
app = FastAPI(
    title="Image Relevance & Auto-Tagging Engine",
    version="1.0.0",
)

# Simple root endpoint
@app.get("/", tags=["Root"])
def read_root(settings: Settings = get_settings()):
    return {"message": "Image Relevance & Auto-Tagging backend API"}

# Health-check endpoint used for sanity testing
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app.include_router(review_router)
app.include_router(job_router)
app.include_router(cost_router)
