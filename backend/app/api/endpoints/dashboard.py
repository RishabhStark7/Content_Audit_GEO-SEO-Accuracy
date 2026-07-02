import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.models.database import get_db
from backend.app.models.models import Medicine, AuditRecord, Issue
from backend.app.schemas import schemas

router = APIRouter()

@router.get("/summary", response_model=schemas.DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """ Compiles overall medical governance KPIs for executive dashboards """
    total_urls = db.query(Medicine).count()
    
    scraped_audits = db.query(AuditRecord).filter(AuditRecord.status.in_(["Scraped", "Completeness_Checked", "Audited"])).all()
    urls_scraped = len(scraped_audits)
    
    audited_records = db.query(AuditRecord).filter(AuditRecord.status == "Audited").all()
    urls_audited = len(audited_records)
    
    # Calculate average scores
    avg_accuracy = db.query(func.avg(AuditRecord.medical_accuracy_score)).filter(AuditRecord.status == "Audited").scalar() or 0.0
    avg_completeness = db.query(func.avg(AuditRecord.completeness_score)).filter(AuditRecord.status.in_(["Completeness_Checked", "Audited"])).scalar() or 0.0
    avg_health = db.query(func.avg(AuditRecord.content_health_score)).filter(AuditRecord.status.in_(["Completeness_Checked", "Audited"])).scalar() or 0.0
    avg_readability = db.query(func.avg(AuditRecord.flesch_reading_ease)).filter(AuditRecord.flesch_reading_ease.isnot(None)).scalar() or 0.0
    avg_seo = db.query(func.avg(AuditRecord.seo_score)).filter(AuditRecord.seo_score.isnot(None)).scalar() or 0.0
    avg_geo = db.query(func.avg(AuditRecord.geo_score)).filter(AuditRecord.geo_score.isnot(None)).scalar() or 0.0
    
    # Issues count
    total_issues = db.query(Issue).count()
    critical_issues = db.query(Issue).filter(Issue.severity == "Critical").count()
    high_issues = db.query(Issue).filter(Issue.severity == "High").count()
    medium_issues = db.query(Issue).filter(Issue.severity == "Medium").count()
    low_issues = db.query(Issue).filter(Issue.severity == "Low").count()
    
    # Filter issues that are not Closed
    open_issues = db.query(Issue).filter(Issue.reviewer_status != "Closed").count()
    closed_issues = db.query(Issue).filter(Issue.reviewer_status == "Closed").count()
    
    # Average resolution time in hours
    resolved_issues = db.query(Issue).filter(Issue.resolved_at.isnot(None)).all()
    avg_res_time_hrs = 0.0
    if resolved_issues:
        total_time = sum((iss.resolved_at - iss.created_at).total_seconds() for iss in resolved_issues)
        avg_res_time_hrs = (total_time / len(resolved_issues)) / 3600.0
        
    return {
        "total_urls": total_urls,
        "urls_scraped": urls_scraped,
        "urls_audited": urls_audited,
        "overall_medical_accuracy_score": avg_accuracy,
        "overall_completeness_score": round(avg_completeness, 2),
        "overall_content_health_score": round(avg_health, 2),
        "overall_readability_score": round(avg_readability, 2),
        "overall_seo_score": round(avg_seo, 2),
        "overall_geo_score": round(avg_geo, 2),
        "total_issues": total_issues,
        "critical_issues": critical_issues,
        "high_issues": high_issues,
        "medium_issues": medium_issues,
        "low_issues": low_issues,
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "average_resolution_time_hrs": round(avg_res_time_hrs, 2)
    }

@router.get("/issues", response_model=List[schemas.IssueResponse])
def get_issues(
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """ Fetch issue list with optional governance filters """
    query = db.query(Issue)
    
    if severity:
        query = query.filter(Issue.severity == severity)
    if issue_type:
        query = query.filter(Issue.issue_type == issue_type)
    if status:
        query = query.filter(Issue.reviewer_status == status)
        
    return query.all()

@router.post("/issues/{issue_id}/update", response_model=schemas.IssueResponse)
def update_issue(issue_id: str, update: schemas.IssueUpdate, db: Session = Depends(get_db)):
    """ Updates ticket lifecycle workflow status """
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
        
    if update.reviewer_status is not None:
        issue.reviewer_status = update.reviewer_status
        if update.reviewer_status == "Closed":
            issue.resolved_at = datetime.datetime.utcnow()
        else:
            issue.resolved_at = None
            
    if update.reviewer_comments is not None:
        issue.reviewer_comments = update.reviewer_comments
        
    if update.assigned_to is not None:
        issue.assigned_to = update.assigned_to
        
    if update.severity is not None:
        issue.severity = update.severity
        
    if update.root_cause is not None:
        issue.root_cause = update.root_cause
        
    db.commit()
    db.refresh(issue)
    return issue

@router.get("/heatmap")
def get_heatmap_data(db: Session = Depends(get_db)):
    """ Returns data representing error counts grouped by category content buckets """
    results = db.query(Issue.content_bucket, func.count(Issue.id)).group_by(Issue.content_bucket).all()
    return {bucket: count for bucket, count in results}

@router.get("/trends")
def get_trends_data(db: Session = Depends(get_db)):
    """ Returns historical trend metrics """
    records = db.query(AuditRecord).order_by(AuditRecord.scraped_at.asc()).all()
    trends = []
    for r in records:
        trends.append({
            "audit_id": r.id,
            "timestamp": r.scraped_at,
            "accuracy": r.medical_accuracy_score or 0.0,
            "completeness": r.completeness_score or 0.0,
            "readability": r.flesch_reading_ease or 0.0,
            "seo": r.seo_score or 0.0,
            "geo": r.geo_score or 0.0
        })
    return trends

@router.get("/progress")
def get_progress():
    """ Exposes live progress logs for the batch scraping runner """
    import os
    import json
    from backend.app.core.config import settings
    progress_file = os.path.join(settings.DATA_DIR, "batch_progress.json")
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "total_skus": 0,
        "completed": 0,
        "pending": 0,
        "percent_complete": 0.0,
        "estimated_time_remaining": "0s",
        "last_updated": ""
    }

@router.post("/run-process")
def run_process(process_type: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """ Triggers completeness, accuracy, consumability, seo, or indepth audits asynchronously """
    if process_type not in ["completeness", "accuracy", "consumability", "seo", "indepth"]:
        raise HTTPException(status_code=400, detail="Invalid process type")
        
    from backend.app.models.database import SessionLocal
    from backend.app.services.pipeline_runner import (
        run_completeness_phase,
        run_consumability_phase,
        run_accuracy_phase,
        run_seo_prompts_phase,
        PipelineLogger
    )
    import os
    import pandas as pd
    
    # Check if input file exists
    catalog_path = "E:/Content-Governance/data/input.xlsx"
    if not os.path.exists(catalog_path):
        raise HTTPException(status_code=404, detail="Input Excel sheet not found")
        
    def run_job():
        db_session = SessionLocal()
        try:
            # Sync catalog Excel rows to Medicine table
            if catalog_path.endswith('.xlsx'):
                try:
                    df = pd.read_excel(catalog_path)
                except Exception:
                    df = pd.read_csv(catalog_path, sep='\t')
            else:
                df = pd.read_csv(catalog_path)
                
            url_col = "URLs" if "URLs" in df.columns else ("SKU URLs" if "SKU URLs" in df.columns else df.columns[0])
            
            medicines = []
            for idx, row in df.iterrows():
                url = row[url_col]
                if bool(pd.isna(url)):
                    continue
                url = str(url).strip()
                med = db_session.query(Medicine).filter(Medicine.url == url).first()
                if not med:
                    med = Medicine(url=url)
                    db_session.add(med)
                    db_session.commit()
                    db_session.refresh(med)
                medicines.append(med)
                
            total_skus = len(medicines)
            logger = PipelineLogger(db_session, process_type.capitalize(), total_skus)
            
            if process_type == "completeness":
                run_completeness_phase(db_session, medicines, logger)
            elif process_type == "accuracy":
                run_accuracy_phase(db_session, medicines, logger)
            elif process_type == "consumability":
                run_consumability_phase(db_session, medicines, logger)
            elif process_type == "seo":
                run_seo_prompts_phase(db_session, medicines, logger)
            elif process_type == "indepth":
                count = 0
                for med in medicines:
                    logger.log(f"Running In-depth Accuracy Audit for SKU #{med.id} ({med.name or 'Unknown'})...")
                    # Fetch audit record
                    audit = db_session.query(AuditRecord).filter(
                        AuditRecord.medicine_id == med.id
                    ).order_by(AuditRecord.scraped_at.desc()).first()
                    
                    if not audit:
                        audit = AuditRecord(medicine_id=med.id, status="Pending", json_path=f"archive/scraped_{med.id}.json")
                        db_session.add(audit)
                        db_session.commit()
                        db_session.refresh(audit)
                        
                    from backend.app.services.audit import run_indepth_audit
                    run_indepth_audit(db_session, audit)
                    
                    count += 1
                    logger.set_stats(count)
                    
                # Close the audit session to commit everything and clear cache
                db_session.close()
                
                # Open a fresh session for exporting Excel
                export_db = SessionLocal()
                try:
                    from backend.app.services.excel_exporter import export_activity_excel
                    export_activity_excel(export_db, "accuracy")
                    from backend.app.services.excel_exporter import update_scraped_content_excel
                    update_scraped_content_excel(export_db)
                finally:
                    export_db.close()
                return
        except Exception as err:
            print(f"[Async Job] Error: {str(err)}")
        finally:
            db_session.close()
            
    background_tasks.add_task(run_job)
    return {"message": f"Successfully triggered {process_type} process in the background."}


