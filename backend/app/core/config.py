import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Medical Content Governance Platform"
    API_V1_STR: str = "/api/v1"
    
    # Database config: defaults to SQLite for local development, easily overridden with PostgreSQL
    DATABASE_URL: str = Field(
        default="sqlite:///E:/Content-Governance/data/mcgp.db",
        validation_alias="DATABASE_URL"
    )
    
    # Directory paths
    DATA_DIR: str = "E:/Content-Governance/data"
    ARCHIVE_DIR: str = "E:/Content-Governance/data/archive"
    
    # AI Config
    GEMINI_API_KEY: str = Field(default="", validation_alias="GEMINI_API_KEY")
    VERTEX_PROJECT: str = Field(default="", validation_alias="VERTEX_PROJECT")
    VERTEX_LOCATION: str = Field(default="us-central1", validation_alias="VERTEX_LOCATION")
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.ARCHIVE_DIR, exist_ok=True)
