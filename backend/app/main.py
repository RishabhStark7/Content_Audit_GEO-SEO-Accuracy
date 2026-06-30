from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.models.database import engine, Base
from backend.app.api.endpoints import scraper, completeness, audit, dashboard

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["scraper"])
app.include_router(completeness.router, prefix=f"{settings.API_V1_STR}/completeness", tags=["completeness"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Medical Content Governance Platform API", "status": "running"}
