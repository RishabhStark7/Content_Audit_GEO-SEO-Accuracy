import datetime
import uuid
from typing import Any
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.database import Base

class Medicine(Base):
    __tablename__ = "medicines"

    id: Any = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url: Any = Column(String, unique=True, index=True, nullable=False)
    name: Any = Column(String, nullable=True)
    generic_name: Any = Column(String, nullable=True)
    priority: Any = Column(String, default="Medium")
    owner: Any = Column(String, nullable=True)
    category: Any = Column(String, nullable=True)
    created_at: Any = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    audits = relationship("AuditRecord", back_populates="medicine", cascade="all, delete-orphan")


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Any = Column(String, primary_key=True, default=lambda: datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    medicine_id: Any = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False)
    scraped_at: Any = Column(DateTime, default=datetime.datetime.utcnow)
    status: Any = Column(String, default="Pending") # Pending, Scraped, Completeness_Checked, Audited, Failed
    
    # Storage Artifact Paths
    html_path: Any = Column(String, nullable=True)
    pdf_path: Any = Column(String, nullable=True)
    screenshot_path: Any = Column(String, nullable=True)
    json_path: Any = Column(String, nullable=True)
    
    # Governance Scores
    completeness_score: Any = Column(Float, nullable=True)
    medical_accuracy_score: Any = Column(Float, nullable=True)
    content_health_score: Any = Column(Float, nullable=True)
    
    # Readability metrics
    flesch_reading_ease: Any = Column(Float, nullable=True)
    flesch_kincaid_grade: Any = Column(Float, nullable=True)
    
    # SEO & GEO metrics
    seo_score: Any = Column(Float, nullable=True)
    geo_score: Any = Column(Float, nullable=True)
    seo_geo_report_path: Any = Column(String, nullable=True)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="audits")
    issues = relationship("Issue", back_populates="audit_record", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id: Any = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_record_id: Any = Column(String, ForeignKey("audit_records.id", ondelete="CASCADE"), nullable=False)
    
    attribute: Any = Column(String, nullable=False) # e.g. "Uses", "Alcohol"
    content_bucket: Any = Column(String, nullable=False) # e.g. "Core Medical Content", "Safety"
    issue_type: Any = Column(String, nullable=False) # e.g. "INC" (Incorrect), "MIS" (Missing)
    root_cause: Any = Column(String, nullable=True) # e.g. "Regulatory Update"
    severity: Any = Column(String, default="Medium") # Critical, High, Medium, Low, Informational
    confidence: Any = Column(String, default="Medium") # Very High, High, Medium, Low
    
    # Reference material info
    regulatory_source: Any = Column(String, nullable=True) # CDSCO, FDA, etc.
    regulatory_section: Any = Column(String, nullable=True)
    
    # Content details
    current_content: Any = Column(Text, nullable=True)
    suggested_content: Any = Column(Text, nullable=True)
    evidence_text: Any = Column(Text, nullable=True)
    
    # Reviewer workflow
    reviewer_status: Any = Column(String, default="Open") # Open, Assigned, Under Review, Accepted, Rejected, Resolved, Closed
    reviewer_comments: Any = Column(Text, nullable=True)
    assigned_to: Any = Column(String, nullable=True)
    
    created_at: Any = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at: Any = Column(DateTime, nullable=True)

    # Relationships
    audit_record = relationship("AuditRecord", back_populates="issues")
