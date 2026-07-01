import os
import sys
import time
import json
import datetime
from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.database import SessionLocal
from backend.app.models.models import Medicine, AuditRecord
from backend.app.core.config import settings

# Configure UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

# Global progress status manager
PROGRESS_PATH = os.path.join(settings.DATA_DIR, "batch_progress.json")

class PipelineLogger:
    """
    Maintains process-level logs, prints them to stdout, and updates
    batch_progress.json with circular console output lines.
    """
    def __init__(self, db: Session, active_process: str, total_skus: int):
        self.db = db
        self.active_process = active_process
        self.total_skus = total_skus
        self.completed_skus = 0
        self.log_lines = []
        
    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        
        # Keep last 15 log lines
        self.log_lines.append(formatted)
        if len(self.log_lines) > 15:
            self.log_lines.pop(0)
            
        self.write_progress()
        
    def set_stats(self, completed: int):
        self.completed_skus = completed
        self.write_progress()
        
    def write_progress(self):
        pending = self.total_skus - self.completed_skus
        percent = round((self.completed_skus / self.total_skus) * 100, 2) if self.total_skus > 0 else 0.0
        
        # Estimate seconds remaining based on process type
        # Scraping: ~15s, Accuracy: ~4s, SEO: ~4s, Completeness/Consumability: ~0.2s
        if "scraping" in self.active_process.lower():
            rate = 15
        elif "accuracy" in self.active_process.lower() or "seo" in self.active_process.lower():
            rate = 4
        else:
            rate = 0.2
            
        time_left_sec = int(pending * rate)
        time_left_str = f"{time_left_sec // 60}m {time_left_sec % 60}s" if time_left_sec > 0 else "0s"
        
        progress_data = {
            "active_process": self.active_process,
            "total_skus": self.total_skus,
            "completed": self.completed_skus,
            "pending": pending,
            "percent_complete": percent,
            "estimated_time_remaining_seconds": time_left_sec,
            "estimated_time_remaining": time_left_str,
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logs": self.log_lines
        }
        
        try:
            with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Logger] Failed to write progress log file: {str(e)}")

def run_scraping_phase(db: Session, medicines: list, logger: PipelineLogger):
    logger.log("Starting Phase 1: Playwright Mobile Scraper...")
    from scraper.scraper import scrape_medicine
    
    count = 0
    logger.set_stats(count)
    
    for med in medicines:
        # Check if already scraped in database
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if audit and audit.status in ["Scraped", "Completeness_Checked", "Audited"] and audit.html_path:
            logger.log(f"SKU #{med.id} ({med.name or 'Unknown'}) already scraped. Skipping.")
            count += 1
            logger.set_stats(count)
            continue
            
        logger.log(f"Scraping SKU #{med.id}: {med.url}...")
        
        # Setup Audit record if missing
        if not audit:
            audit_id = f"{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{med.id}"
            audit = AuditRecord(id=audit_id, medicine_id=med.id, status="Pending")
            db.add(audit)
            db.commit()
            db.refresh(audit)
            
        try:
            # Trigger Playwright Scraper
            meta = scrape_medicine(med.url, audit.id)
            
            # Save results & update status
            audit.status = "Scraped"
            audit.html_path = meta["html_path"]
            audit.pdf_path = meta["pdf_path"]
            audit.screenshot_path = meta["screenshot_path"]
            audit.json_path = meta["json_path"]
            
            # Save actual name if available
            json_abs = os.path.join(settings.DATA_DIR, meta["json_path"])
            if os.path.exists(json_abs):
                with open(json_abs, "r", encoding="utf-8") as f:
                    jdata = json.load(f)
                    med.name = jdata.get("medicine_name", med.name)
                    
            db.commit()
            logger.log(f"Successfully scraped SKU #{med.id} ({med.name}).")
        except Exception as e:
            logger.log(f"ERROR: Failed to scrape SKU #{med.id}: {str(e)}")
            audit.status = "Failed"
            db.commit()
            
        # Commit checkpoint and update Excel file
        try:
            from backend.app.services.excel_exporter import update_scraped_content_excel
            update_scraped_content_excel(db)
        except Exception as sheet_err:
            logger.log(f"Warning: Sheet sync issue: {str(sheet_err)}")
            
        count += 1
        logger.set_stats(count)
        
    logger.log("Phase 1 complete: All SKUs scraped.")

def run_completeness_phase(db: Session, medicines: list, logger: PipelineLogger):
    logger.log("Starting Phase 2: Local Completeness Audit...")
    from backend.app.services.completeness import run_completeness_validation
    
    count = 0
    logger.set_stats(count)
    
    for med in medicines:
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit or not audit.json_path:
            logger.log(f"SKU #{med.id} has no scrape data. Skipping completeness check.")
            count += 1
            logger.set_stats(count)
            continue
            
        if audit.status in ["Completeness_Checked", "Audited"]:
            logger.log(f"SKU #{med.id} completeness already audited. Skipping.")
            count += 1
            logger.set_stats(count)
            continue
            
        logger.log(f"Auditing completeness for SKU #{med.id} ({med.name})...")
        try:
            run_completeness_validation(db, audit)
            logger.log(f"Completeness Audited for SKU #{med.id}. Score: {audit.completeness_score}%")
        except Exception as e:
            logger.log(f"ERROR: Completeness audit failed for SKU #{med.id}: {str(e)}")
            
        # Commit Excel updates
        try:
            from backend.app.services.excel_exporter import update_scraped_content_excel
            update_scraped_content_excel(db)
        except Exception as sheet_err:
            logger.log(f"Warning: Sheet sync issue: {str(sheet_err)}")
            
        count += 1
        logger.set_stats(count)
        
    logger.log("Phase 2 complete: Local Completeness Audited.")
    try:
        from backend.app.services.excel_exporter import export_activity_excel
        export_activity_excel(db, "completeness")
    except Exception as excel_err:
        logger.log(f"Warning: Activity Excel export failed: {str(excel_err)}")

def run_consumability_phase(db: Session, medicines: list, logger: PipelineLogger):
    logger.log("Starting Phase 3: Local Readability (Consumability) Audit...")
    from backend.app.services.readability import calculate_readability
    
    count = 0
    logger.set_stats(count)
    
    for med in medicines:
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit or not audit.json_path:
            logger.log(f"SKU #{med.id} has no scrape data. Skipping consumability check.")
            count += 1
            logger.set_stats(count)
            continue
            
        if audit.flesch_reading_ease is not None:
            logger.log(f"SKU #{med.id} consumability already audited. Skipping.")
            count += 1
            logger.set_stats(count)
            continue
            
        logger.log(f"Calculating readability for SKU #{med.id} ({med.name})...")
        try:
            # Load JSON content
            json_abs = os.path.join(settings.DATA_DIR, audit.json_path)
            with open(json_abs, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Compile text block
            text = f"{data.get('product_introduction', '')} {data.get('uses', '')} {data.get('benefits', '')}"
            res = calculate_readability(text)
            
            audit.flesch_reading_ease = res["flesch_reading_ease"]
            audit.flesch_kincaid_grade = res["flesch_kincaid_grade"]
            db.commit()
            
            logger.log(f"Consumability score for SKU #{med.id}: Reading Ease: {audit.flesch_reading_ease}, Grade: {audit.flesch_kincaid_grade}")
        except Exception as e:
            logger.log(f"ERROR: Consumability check failed for SKU #{med.id}: {str(e)}")
            
        # Commit updates
        try:
            from backend.app.services.excel_exporter import update_scraped_content_excel
            update_scraped_content_excel(db)
        except Exception as sheet_err:
            logger.log(f"Warning: Sheet sync issue: {str(sheet_err)}")
            
        count += 1
        logger.set_stats(count)
        
    logger.log("Phase 3 complete: Readability Consumability Audited.")
    try:
        from backend.app.services.excel_exporter import export_activity_excel
        export_activity_excel(db, "readability")
    except Exception as excel_err:
        logger.log(f"Warning: Activity Excel export failed: {str(excel_err)}")

def run_accuracy_phase(db: Session, medicines: list, logger: PipelineLogger):
    logger.log("Starting Phase 4: AI Medical Accuracy Audit...")
    from backend.app.services.audit import run_accuracy_audit
    
    count = 0
    logger.set_stats(count)
    
    for med in medicines:
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit or not audit.json_path:
            logger.log(f"SKU #{med.id} has no scrape data. Skipping Accuracy Audit.")
            count += 1
            logger.set_stats(count)
            continue
            
        if audit.status == "Audited":
            logger.log(f"SKU #{med.id} accuracy already audited. Skipping.")
            count += 1
            logger.set_stats(count)
            continue
            
        logger.log(f"Running AI accuracy audit for SKU #{med.id} ({med.name})...")
        try:
            run_accuracy_audit(db, audit)
            logger.log(f"AI Accuracy Score for SKU #{med.id}: {audit.medical_accuracy_score}%")
        except Exception as e:
            logger.log(f"ERROR: AI Accuracy Audit failed for SKU #{med.id}: {str(e)}")
            
        # Commit updates
        try:
            from backend.app.services.excel_exporter import update_scraped_content_excel
            update_scraped_content_excel(db)
        except Exception as sheet_err:
            logger.log(f"Warning: Sheet sync issue: {str(sheet_err)}")
            
        count += 1
        logger.set_stats(count)
        
    logger.log("Phase 4 complete: AI Accuracy Audits complete.")
    try:
        from backend.app.services.excel_exporter import export_activity_excel
        export_activity_excel(db, "accuracy")
    except Exception as excel_err:
        logger.log(f"Warning: Activity Excel export failed: {str(excel_err)}")

def run_seo_prompts_phase(db: Session, medicines: list, logger: PipelineLogger):
    logger.log("Starting Phase 5: AI SEO & User Prompts Audit...")
    from backend.app.services.seo_geo import run_seo_geo_ai_audit
    
    count = 0
    logger.set_stats(count)
    
    for med in medicines:
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit or not audit.json_path:
            logger.log(f"SKU #{med.id} has no scrape data. Skipping SEO/Prompts Audit.")
            count += 1
            logger.set_stats(count)
            continue
            
        # Check database scores first to avoid unnecessary actions
        if audit.seo_score is not None and audit.geo_score is not None:
            logger.log(f"SKU #{med.id} SEO/Prompts already audited. Skipping.")
            count += 1
            logger.set_stats(count)
            continue
            
        json_abs = os.path.join(settings.DATA_DIR, audit.json_path)
        report_file = os.path.join(os.path.dirname(json_abs), "seo_geo_report.json")
        
        # If database has no score but local report exists, restore directly from disk cache
        if os.path.exists(report_file):
            try:
                with open(report_file, "r", encoding="utf-8") as rf:
                    saved_results = json.load(rf)
                audit.seo_score = float(saved_results.get("seo_score", 0.0))
                audit.geo_score = float(saved_results.get("geo_score", 0.0))
                from pathlib import Path
                audit.seo_geo_report_path = str(Path(report_file).relative_to(settings.DATA_DIR))
                db.commit()
                logger.log(f"SKU #{med.id} SEO/Prompts restored from existing report file. SEO: {audit.seo_score}, GEO: {audit.geo_score}")
                count += 1
                logger.set_stats(count)
                continue
            except Exception as e:
                logger.log(f"Warning: Failed to restore existing SEO report for SKU #{med.id}: {str(e)}")
            
        logger.log(f"Running AI SEO & Prompts Audit for SKU #{med.id} ({med.name})...")
        try:
            run_seo_geo_ai_audit(db, audit)
            logger.log(f"AI SEO Score: {audit.seo_score}, GEO: {audit.geo_score}")
        except Exception as e:
            logger.log(f"ERROR: AI SEO/Prompts Audit failed for SKU #{med.id}: {str(e)}")
            
        # Commit updates
        try:
            from backend.app.services.excel_exporter import update_scraped_content_excel
            update_scraped_content_excel(db)
        except Exception as sheet_err:
            logger.log(f"Warning: Sheet sync issue: {str(sheet_err)}")
            
        count += 1
        logger.set_stats(count)
        
    logger.log("Phase 5 complete: AI SEO & Prompts Audits complete.")
    try:
        from backend.app.services.excel_exporter import export_activity_excel
        export_activity_excel(db, "seo")
    except Exception as excel_err:
        logger.log(f"Warning: Activity Excel export failed: {str(excel_err)}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MCGP Batch Process Pipeline Runner.")
    parser.add_argument("--process", type=str, default="all", 
                        choices=["all", "scraping", "completeness", "consumability", "accuracy", "seo"],
                        help="Specify process phase to execute.")
    args = parser.parse_args()
    
    # Auto-create tables on blank databases
    from backend.app.models.database import engine
    from backend.app.models.models import Base
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. Sync catalog Excel rows to Medicine table
    catalog_path = "E:/Content-Governance/data/input.xlsx"
    if not os.path.exists(catalog_path):
        print(f"ERROR: Input spreadsheet not found at: {catalog_path}")
        return
        
    # Standard sync using requests to backend or direct DB insertion
    # For safety, let's parse local Excel and sync database directly
    import pandas as pd  # type: ignore  # pyrefly: ignore
    try:
        if catalog_path.endswith('.xlsx'):
            try:
                df = pd.read_excel(catalog_path)
            except Exception:
                # TSV reader fallback
                df = pd.read_csv(catalog_path, sep='\t')
        else:
            df = pd.read_csv(catalog_path)
            
        # Map columns
        url_col = "URLs" if "URLs" in df.columns else ("SKU URLs" if "SKU URLs" in df.columns else df.columns[0])
        
        medicines = []
        for idx, row in df.iterrows():
            url = row[url_col]
            if bool(pd.isna(url)):
                continue
            url = str(url).strip()
            med = db.query(Medicine).filter(Medicine.url == url).first()
            if not med:
                med = Medicine(url=url)
                db.add(med)
                db.commit()
                db.refresh(med)
            medicines.append(med)
    except Exception as e:
        print(f"ERROR: Failed to sync Medicine DB with input sheet: {str(e)}")
        return
        
    total_skus = len(medicines)
    print(f"Platform synced successfully. Total catalog medicines: {total_skus}")
    
    # 2. Run selected phases sequentially
    phases_to_run = []
    if args.process == "all":
        phases_to_run = ["scraping", "completeness", "consumability", "accuracy", "seo"]
    else:
        phases_to_run = [args.process]
        
    for phase in phases_to_run:
        logger = PipelineLogger(db, phase.capitalize(), total_skus)
        
        if phase == "scraping":
            run_scraping_phase(db, medicines, logger)
        elif phase == "completeness":
            run_completeness_phase(db, medicines, logger)
        elif phase == "consumability":
            run_consumability_phase(db, medicines, logger)
        elif phase == "accuracy":
            run_accuracy_phase(db, medicines, logger)
        elif phase == "seo":
            run_seo_prompts_phase(db, medicines, logger)
            
    # Final excel synchronization
    try:
        from backend.app.services.excel_exporter import update_scraped_content_excel
        update_scraped_content_excel(db)
        print("[Pipeline Runner] Final Excel synchronization complete.")
    except Exception as sheet_err:
        print(f"Warning: Sheet sync issue: {str(sheet_err)}")
        
    db.close()
    print("Pipeline process completed successfully.")

if __name__ == "__main__":
    main()
