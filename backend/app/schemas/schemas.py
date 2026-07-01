import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Medicine Schemas
class MedicineBase(BaseModel):
    url: str
    name: Optional[str] = None
    generic_name: Optional[str] = None
    priority: str = "Medium"
    owner: Optional[str] = None
    category: Optional[str] = None

class MedicineCreate(MedicineBase):
    pass

class MedicineResponse(MedicineBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# Issue Schemas
class IssueBase(BaseModel):
    attribute: str
    content_bucket: str
    issue_type: str
    root_cause: Optional[str] = None
    severity: str
    confidence: str
    regulatory_source: Optional[str] = None
    regulatory_section: Optional[str] = None
    current_content: Optional[str] = None
    suggested_content: Optional[str] = None
    evidence_text: Optional[str] = None
    reviewer_status: str
    reviewer_comments: Optional[str] = None
    assigned_to: Optional[str] = None

class IssueUpdate(BaseModel):
    reviewer_status: Optional[str] = None
    reviewer_comments: Optional[str] = None
    assigned_to: Optional[str] = None
    severity: Optional[str] = None
    root_cause: Optional[str] = None
    resolved_at: Optional[datetime.datetime] = None

class IssueResponse(IssueBase):
    id: str
    audit_record_id: str
    created_at: datetime.datetime
    resolved_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# Audit Record Schemas
class AuditRecordBase(BaseModel):
    medicine_id: int
    status: str
    html_path: Optional[str] = None
    pdf_path: Optional[str] = None
    screenshot_path: Optional[str] = None
    json_path: Optional[str] = None
    completeness_score: Optional[float] = None
    medical_accuracy_score: Optional[float] = None
    content_health_score: Optional[float] = None
    flesch_reading_ease: Optional[float] = None
    flesch_kincaid_grade: Optional[float] = None
    seo_score: Optional[float] = None
    geo_score: Optional[float] = None
    seo_geo_report_path: Optional[str] = None

class AuditRecordResponse(AuditRecordBase):
    id: str
    scraped_at: datetime.datetime
    issues: List[IssueResponse] = []

    class Config:
        from_attributes = True

class DashboardSummaryResponse(BaseModel):
    total_urls: int
    urls_scraped: int
    urls_audited: int
    overall_medical_accuracy_score: float
    overall_completeness_score: float
    overall_content_health_score: float
    overall_readability_score: float
    overall_seo_score: float
    overall_geo_score: float
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    open_issues: int
    closed_issues: int
    average_resolution_time_hrs: float
