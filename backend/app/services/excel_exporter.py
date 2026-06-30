import os
import json
import datetime
import pandas as pd  # type: ignore  # pyrefly: ignore
from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.models import Medicine, AuditRecord
from backend.app.core.config import settings

def update_scraped_content_excel(db: Session):
    """
    Queries all successfully scraped medicines, extracts their latest structured JSON,
    and updates E:/Content-Governance/data/scraped_content.xlsx with tabular rows.
    """
    print("[Excel Exporter] Updating scraped content Excel sheet...")
    
    # Query all medicines
    medicines = db.query(Medicine).all()
    
    rows = []
    for med in medicines:
        # Get the latest completed/scraped audit record
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id,
            AuditRecord.status.in_(["Scraped", "Completeness_Checked", "Audited"])
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit or not audit.json_path:
            continue
            
        json_abs_path = os.path.join(settings.DATA_DIR, audit.json_path)
        if not os.path.exists(json_abs_path):
            continue
            
        try:
            with open(json_abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Safely extract values
            safety = data.get("safety", {})
            fact_box = data.get("fact_box", {})
            
            # Format lists for cells
            side_effects_str = "\n".join(data.get("side_effects", []))
            quick_tips_str = "\n".join(data.get("quick_tips", []))
            
            faqs_list = []
            for faq in data.get("faqs", []):
                q = faq.get("question", "")
                a = faq.get("answer", "")
                faqs_list.append(f"Q: {q}\nA: {a}")
            faqs_str = "\n\n".join(faqs_list)
            
            substitutes_str = "\n".join(data.get("substitutes", []))
            
            row = {
                "SKU ID": med.id,
                "URLs": med.url,
                "Product Name": data.get("medicine_name", med.name),
                "Generic Name": data.get("generic_name", med.generic_name),
                "Dosage Form": data.get("dosage_form", ""),
                "Strength": data.get("strength", ""),
                "Product Summary": data.get("product_summary", ""),
                "Product Introduction": data.get("product_introduction", ""),
                "Uses": data.get("uses", ""),
                "Benefits": data.get("benefits", ""),
                "Side Effects": side_effects_str,
                "How to Use": data.get("how_to_use", ""),
                "How It Works": data.get("how_it_works", ""),
                "Dosage": data.get("dosage", ""),
                "Overdose": data.get("overdose", ""),
                "Missed Dose": data.get("missed_dose", ""),
                "Substitutes": substitutes_str,
                "Alcohol Safety": safety.get("alcohol", ""),
                "Pregnancy Safety": safety.get("pregnancy", ""),
                "Breastfeeding Safety": safety.get("breastfeeding", ""),
                "Driving Safety": safety.get("driving", ""),
                "Kidney Safety": safety.get("kidney", ""),
                "Liver Safety": safety.get("liver", ""),
                "Quick Tips": quick_tips_str,
                "Chemical Class": fact_box.get("chemical_class", ""),
                "Therapeutic Class": fact_box.get("therapeutic_class", ""),
                "Habit Forming": fact_box.get("habit_forming", ""),
                "Action Class": fact_box.get("action_class", ""),
                "Drug Interactions": data.get("drug_interactions", ""),
                "FAQs": faqs_str
            }
            rows.append(row)
        except Exception as e:
            print(f"[Excel Exporter] Error reading JSON for SKU {med.id}: {str(e)}")
            
    if not rows:
        print("[Excel Exporter] No scraped records to export.")
        return
        
    try:
        # Create DataFrame and export to Excel
        df = pd.DataFrame(rows)
        output_path = os.path.join(settings.DATA_DIR, "scraped_content.xlsx")
        try:
            if os.path.exists(output_path):
                with open(output_path, "r+"):
                    pass
        except IOError:
            output_path = os.path.join(settings.DATA_DIR, "scraped_content_fresh.xlsx")
            print(f"[Excel Exporter] scraped_content.xlsx is locked. Falling back to: {output_path}")
            
        # Write to excel using openpyxl engine
        df.to_excel(output_path, index=False)
        print(f"[Excel Exporter] Successfully wrote master sheet to: {output_path}")
        
        # Trigger progress logging
        try:
            update_batch_progress(db)
        except Exception as prog_err:
            print(f"[Excel Exporter] Error updating progress: {str(prog_err)}")
    except Exception as e:
        print(f"[Excel Exporter] Error writing Excel spreadsheet: {str(e)}")

def update_batch_progress(db: Session):
    """
    Computes total, completed, pending SKUs and estimated time remaining,
    saving the status to data/batch_progress.json.
    """
    total_skus = db.query(Medicine).count()
    
    # Load existing logs or active_process if they exist
    progress_file = os.path.join(settings.DATA_DIR, "batch_progress.json")
    active_process = "Scraping"
    existing_logs = []
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                active_process = old_data.get("active_process", active_process)
                existing_logs = old_data.get("logs", existing_logs)
        except:
            pass

    # Completed medicines are those that have a latest audit in appropriate statuses
    completed_count = 0
    medicines = db.query(Medicine).all()
    for med in medicines:
        latest_audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        # Count completion based on the active process
        if active_process.lower() == "scraping":
            if latest_audit and latest_audit.status in ["Scraped", "Completeness_Checked", "Audited", "Failed"]:
                completed_count += 1
        elif active_process.lower() == "completeness":
            if latest_audit and latest_audit.status in ["Completeness_Checked", "Audited", "Failed"]:
                completed_count += 1
        elif active_process.lower() == "accuracy":
            if latest_audit and latest_audit.status in ["Audited", "Failed"]:
                completed_count += 1
        else:
            if latest_audit and latest_audit.status in ["Completeness_Checked", "Audited", "Failed"]:
                completed_count += 1
            
    pending_count = total_skus - completed_count
    
    # Estimate time remaining based on active process
    if "scraping" in active_process.lower():
        rate = 15
    elif "accuracy" in active_process.lower() or "seo" in active_process.lower():
        rate = 4
    else:
        rate = 0.2
        
    time_remaining_sec = pending_count * rate
    time_remaining_str = f"{time_remaining_sec // 60}m {time_remaining_sec % 60}s" if time_remaining_sec > 0 else "0s"
    
    progress = {
        "active_process": active_process,
        "total_skus": total_skus,
        "completed": completed_count,
        "pending": pending_count,
        "percent_complete": round((completed_count / total_skus * 100), 2) if total_skus > 0 else 100.0,
        "estimated_time_remaining_seconds": time_remaining_sec,
        "estimated_time_remaining": time_remaining_str,
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "logs": existing_logs
    }
    
    try:
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        print(f"[Progress Tracker] Updated progress: {completed_count}/{total_skus} done. Time remaining: {time_remaining_str}")
    except Exception as e:
        print(f"[Progress Tracker] Error writing progress JSON: {str(e)}")

