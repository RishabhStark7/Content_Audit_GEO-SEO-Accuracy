import os
import sys
import json
import datetime
import subprocess
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd

from backend.app.models.database import get_db
from backend.app.models.models import Medicine, AuditRecord
from backend.app.schemas import schemas
from backend.app.core.config import settings

router = APIRouter()

def run_scraper_task(db_session_factory, url: str, medicine_id: int, version_id: str):
    """ Run the scraping task in a background subprocess to avoid event-loop blocking """
    # Re-create session for background thread
    db = db_session_factory()
    audit_record = db.query(AuditRecord).filter(AuditRecord.id == version_id).first()
    if not audit_record:
        db.close()
        return
        
    try:
        print(f"[Backend Subprocess] Launching scraper for {url} with version {version_id}")
        
        # Invoke scraper via subprocess to run playwright isolated
        scraper_script = os.path.join("E:/Content-Governance/scraper", "scraper.py")
        env = os.environ.copy()
        env["PYTHONPATH"] = "E:/Content-Governance"
        
        process = subprocess.run([
            sys.executable,
            scraper_script,
            "--url", url,
            "--version-id", version_id
        ], capture_output=True, text=True, cwd="E:/Content-Governance/scraper", env=env)
        
        if process.returncode != 0:
            raise Exception(f"Scraper exited with code {process.returncode}: {process.stderr}")
            
        print(f"[Backend Subprocess] Scraper finished successfully: {process.stdout}")
        
        # Locate the output file meta.json or structured.json
        from scraper.scraper import get_sku_id_from_url
        sku_id = get_sku_id_from_url(url)
        record_dir = os.path.join(settings.ARCHIVE_DIR, sku_id)
        meta_file = os.path.join(record_dir, "meta.json")
        
        if not os.path.exists(meta_file):
            raise Exception(f"Scraper metadata file not found at: {meta_file}")
            
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
        # Update Audit Record
        audit_record.status = "Scraped"
        audit_record.html_path = meta.get("html_path")
        audit_record.pdf_path = meta.get("pdf_path")
        audit_record.screenshot_path = meta.get("screenshot_path")
        audit_record.json_path = meta.get("json_path")
        
        # Save extracted name to the Medicine record
        medicine = db.query(Medicine).filter(Medicine.id == audit_record.medicine_id).first()
        if medicine:
            # Read name from structured JSON if exists
            json_abs_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
            if os.path.exists(json_abs_path):
                try:
                    with open(json_abs_path, "r", encoding="utf-8") as jf:
                        jdata = json.load(jf)
                        medicine.name = jdata.get("medicine_name", medicine.name)
                except Exception as name_err:
                    print(f"[Backend Subprocess] Failed to read name: {str(name_err)}")
            
            if not medicine.name:
                medicine.name = slug.replace("-", " ").title()
                
        db.commit()
        
        # Automatically trigger Part 1.5: Content Completeness Validation
        # In Part 1, we just import completeness checker dynamically or log that it will run.
        try:
            from backend.app.services.completeness import run_completeness_validation
            run_completeness_validation(db, audit_record)
        except Exception as validation_error:
            print(f"[Backend Subprocess] Completeness validation skipped or failed: {str(validation_error)}")
            
    except Exception as e:
        print(f"[Backend Subprocess] Scrape job failed for {url}: {str(e)}")
        audit_record.status = "Failed"
        db.commit()
    finally:
        db.close()


@router.post("/upload-excel", response_model=List[schemas.MedicineResponse])
def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """ Upload input.xlsx to register medicines in the system """
    try:
        content = file.file.read()
        file.file.seek(0)
        
        try:
            df = pd.read_excel(file.file)
        except Exception as e:
            print(f"[Upload API] Excel parsing failed: {str(e)}. Trying CSV/TSV reader...")
            file.file.seek(0)
            text_content = content.decode('utf-8', errors='ignore')
            if '\t' in text_content:
                df = pd.read_csv(file.file, sep='\t')
            else:
                df = pd.read_csv(file.file, sep=',')
        
        # Expected columns mapping (case-insensitive)
        column_mapping = {
            "medicine url": "url",
            "url": "url",
            "urls": "url",
            "sku urls": "url",
            "product name": "name",
            "priority": "priority",
            "owner": "owner",
            "category": "category"
        }
        
        # Normalize columns
        df.columns = [c.strip().lower() for c in df.columns]
        
        imported_medicines = []
        for _, row in df.iterrows():
            url_col = None
            for key in ["medicine url", "url", "urls", "sku urls", "sku url"]:
                if key in df.columns:
                    url_col = key
                    break
                    
            if not url_col:
                continue
                
            val = row[url_col]
            if val is None or (isinstance(val, float) and val != val):
                continue
                
            url = str(val).strip()
            if not url or url.lower() in ["nan", "none", "null"]:
                continue
            
            # Extract optional columns
            name_val = row["product name"] if "product name" in df.columns else None
            name = str(name_val).strip() if (name_val is not None and not (isinstance(name_val, float) and name_val != name_val)) else None
            if name and name.lower() in ["nan", "none", "null"]:
                name = None
            
            prio_val = row["priority"] if "priority" in df.columns else None
            priority = str(prio_val).strip() if (prio_val is not None and not (isinstance(prio_val, float) and prio_val != prio_val)) else "Medium"
            if priority.lower() in ["nan", "none", "null"]:
                priority = "Medium"
            
            owner_val = row["owner"] if "owner" in df.columns else None
            owner = str(owner_val).strip() if (owner_val is not None and not (isinstance(owner_val, float) and owner_val != owner_val)) else None
            if owner and owner.lower() in ["nan", "none", "null"]:
                owner = None
            
            cat_val = row["category"] if "category" in df.columns else None
            category = str(cat_val).strip() if (cat_val is not None and not (isinstance(cat_val, float) and cat_val != cat_val)) else None
            if category and category.lower() in ["nan", "none", "null"]:
                category = None
            
            # Check if URL already exists
            existing = db.query(Medicine).filter(Medicine.url == url).first()
            if existing:
                # Update existing info
                if name: existing.name = name
                existing.priority = priority
                if owner: existing.owner = owner
                if category: existing.category = category
                imported_medicines.append(existing)
            else:
                new_medicine = Medicine(
                    url=url,
                    name=name,
                    priority=priority,
                    owner=owner,
                    category=category
                )
                db.add(new_medicine)
                imported_medicines.append(new_medicine)
                
        db.commit()
        # Refresh to get IDs
        for med in imported_medicines:
            db.refresh(med)
            
        return imported_medicines
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process excel file: {str(e)}")


@router.post("/scrape-single", response_model=schemas.AuditRecordResponse)
def trigger_scrape_single(
    medicine_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """ Trigger playwrigt scraper for a specific medicine ID """
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found.")
        
    version_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Create AuditRecord entry in Pending state
    audit_record = AuditRecord(
        id=version_id,
        medicine_id=medicine.id,
        status="Pending",
        scraped_at=datetime.datetime.utcnow()
    )
    db.add(audit_record)
    db.commit()
    db.refresh(audit_record)
    
    # We pass the SessionLocal generator to background thread to handle DB isolation cleanly
    from backend.app.models.database import SessionLocal
    background_tasks.add_task(
        run_scraper_task, 
        SessionLocal, 
        medicine.url, 
        medicine.id, 
        version_id
    )
    
    return audit_record


@router.get("/list", response_model=List[schemas.MedicineResponse])
def list_medicines(db: Session = Depends(get_db)):
    """ Get all registered medicines """
    return db.query(Medicine).all()


@router.get("/audits", response_model=List[schemas.AuditRecordResponse])
def list_audits(db: Session = Depends(get_db)):
    """ Get all audit history records """
    return db.query(AuditRecord).all()


@router.get("/audit-details/{audit_id}", response_model=schemas.AuditRecordResponse)
def get_audit_details(audit_id: str, db: Session = Depends(get_db)):
    """ Get full details of a specific audit run """
    audit = db.query(AuditRecord).filter(AuditRecord.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit record not found.")
    return audit
