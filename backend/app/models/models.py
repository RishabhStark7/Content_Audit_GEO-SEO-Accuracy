import datetime
import uuid
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.database import Base

class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    generic_name = Column(String, nullable=True)
    priority = Column(String, default="Medium")
    owner = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    audits = relationship("AuditRecord", back_populates="medicine", cascade="all, delete-orphan")


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id = Column(String, primary_key=True, default=lambda: datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="CASCADE"), nullable=False)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Pending") # Pending, Scraped, Completeness_Checked, Audited, Failed
    
    # Storage Artifact Paths
    html_path = Column(String, nullable=True)
    pdf_path = Column(String, nullable=True)
    screenshot_path = Column(String, nullable=True)
    json_path = Column(String, nullable=True)
    
    # Governance Scores
    completeness_score = Column(Float, nullable=True)
    medical_accuracy_score = Column(Float, nullable=True)
    content_health_score = Column(Float, nullable=True)
    
    # Readability metrics
    flesch_reading_ease = Column(Float, nullable=True)
    flesch_kincaid_grade = Column(Float, nullable=True)
    
    # SEO & GEO metrics
    seo_score = Column(Float, nullable=True)
    geo_score = Column(Float, nullable=True)
    seo_geo_report_path = Column(String, nullable=True)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="audits")
    issues = relationship("Issue", back_populates="audit_record", cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_record_id = Column(String, ForeignKey("audit_records.id", ondelete="CASCADE"), nullable=False)
    
    attribute = Column(String, nullable=False) # e.g. "Uses", "Alcohol"
    content_bucket = Column(String, nullable=False) # e.g. "Core Medical Content", "Safety"
    issue_type = Column(String, nullable=False) # e.g. "INC" (Incorrect), "MIS" (Missing)
    root_cause = Column(String, nullable=True) # e.g. "Regulatory Update"
    severity = Column(String, default="Medium") # Critical, High, Medium, Low, Informational
    confidence = Column(String, default="Medium") # Very High, High, Medium, Low
    
    # Reference material info
    regulatory_source = Column(String, nullable=True) # CDSCO, FDA, etc.
    regulatory_section = Column(String, nullable=True)
    
    # Content details
    current_content = Column(Text, nullable=True)
    suggested_content = Column(Text, nullable=True)
    evidence_text = Column(Text, nullable=True)
    
    # Reviewer workflow
    reviewer_status = Column(String, default="Open") # Open, Assigned, Under Review, Accepted, Rejected, Resolved, Closed
    reviewer_comments = Column(Text, nullable=True)
    assigned_to = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    audit_record = relationship("AuditRecord", back_populates="issues")
