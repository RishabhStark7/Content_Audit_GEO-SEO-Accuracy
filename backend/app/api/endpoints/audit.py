from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.models.models import AuditRecord
from backend.app.schemas import schemas
from backend.app.services.audit import run_accuracy_audit

router = APIRouter()

def execute_audit_background(db_session_factory, audit_id: str):
    """ Background thread executor for AI audit """
    db = db_session_factory()
    audit_record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not audit_record:
        db.close()
        return
        
    try:
        run_accuracy_audit(db, audit_record)
    except Exception as e:
        print(f"[Backend Subprocess] Accuracy audit job failed: {str(e)}")
        audit_record.status = "Failed"
        db.commit()
    finally:
        db.close()

@router.post("/trigger", response_model=schemas.AuditRecordResponse)
def trigger_audit(audit_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """ Trigger AI-assisted Medical Accuracy Audit on scraped and completeness-checked page """
    audit_record = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not audit_record:
        raise HTTPException(status_code=404, detail="Audit record not found.")
        
    # Set status to pending audit trigger
    audit_record.status = "Auditing"
    db.commit()
    db.refresh(audit_record)
    
    from backend.app.models.database import SessionLocal
    background_tasks.add_task(execute_audit_background, SessionLocal, audit_id)
    
    return audit_record
