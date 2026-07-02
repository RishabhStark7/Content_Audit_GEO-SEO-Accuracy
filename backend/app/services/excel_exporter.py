import os
import json
import datetime
import pandas as pd  # type: ignore  # pyrefly: ignore
from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.models import Medicine, AuditRecord, Issue
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
        
        # Save a duplicate copy with the dynamic filename format: scraped_content-date-time-noofSKUs.xlsx inside a separate directory
        try:
            total_skus = len(medicines)
            filename = get_activity_excel_filename("scraped_content", total_skus)
            scraped_dir = os.path.join(settings.DATA_DIR, "scraped_content")
            os.makedirs(scraped_dir, exist_ok=True)
            dup_output_path = os.path.join(scraped_dir, filename)
            df.to_excel(dup_output_path, index=False)
            print(f"[Excel Exporter] Successfully wrote duplicate scraped_content sheet to: {dup_output_path}")
        except Exception as dup_err:
            print(f"[Excel Exporter] Warning: Failed to write duplicate scraped content file: {str(dup_err)}")
            
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


def get_activity_excel_filename(activity: str, total_skus: int) -> str:
    now = datetime.datetime.now()
    # 1july26 format matching user requirement
    months = {
        1: "jan", 2: "feb", 3: "mar", 4: "apr", 5: "may", 6: "june",
        7: "july", 8: "aug", 9: "sept", 10: "oct", 11: "nov", 12: "dec"
    }
    month_str = months.get(now.month, now.strftime("%b").lower())
    day_str = str(now.day)
    year_str = now.strftime("%y") # 26
    date_str = f"{day_str}{month_str}{year_str}"
    
    # 700AM format matching user requirement (no colons, uppercase AM/PM, no leading zero on hour)
    hour = now.hour % 12
    if hour == 0:
        hour = 12
    minute = now.minute
    am_pm = "AM" if now.hour < 12 else "PM"
    time_str = f"{hour}{minute:02d}{am_pm}"
    
    return f"{activity}-{date_str}-{time_str}-{total_skus}.xlsx"


def get_friendly_issue_type(code: str) -> str:
    mapping = {
        "MIS": "Incomplete",
        "INC": "Incorrect",
        "CON": "Contradictory",
        "LCQ": "Low Quality"
    }
    return mapping.get(code, code)


def export_activity_excel(db: Session, activity: str):
    """
    Creates a specific Excel spreadsheet for the given activity (completeness, readability, accuracy, seo).
    Naming format: Activity-date-time-numberofSKUs.xlsx
    Example: completeness-1july26-700AM-38.xlsx
    """
    total_skus = db.query(Medicine).count()
    filename = get_activity_excel_filename(activity, total_skus)
    activity_dir = os.path.join(settings.DATA_DIR, activity)
    os.makedirs(activity_dir, exist_ok=True)
    output_path = os.path.join(activity_dir, filename)
    print(f"[Excel Exporter] Generating activity Excel for '{activity}' at: {output_path}")
    
    medicines = db.query(Medicine).all()
    summary_rows = []
    details_rows = []
    
    for med in medicines:
        # Get the latest completed/scraped audit record
        audit = db.query(AuditRecord).filter(
            AuditRecord.medicine_id == med.id
        ).order_by(AuditRecord.scraped_at.desc()).first()
        
        if not audit:
            continue
            
        audited_at_str = audit.scraped_at.strftime("%Y-%m-%d %H:%M:%S") if audit.scraped_at else ""
        
        # Load generic name from json to prevent "Unknown" showing up
        generic_name_display = med.generic_name
        if audit.json_path:
            json_abs_path = os.path.join(settings.DATA_DIR, audit.json_path)
            if os.path.exists(json_abs_path):
                try:
                    with open(json_abs_path, "r", encoding="utf-8") as f:
                        jdata = json.load(f)
                        generic_name_display = jdata.get("generic_name", med.generic_name)
                        # Sync it back to DB
                        if generic_name_display and not med.generic_name:
                            med.generic_name = generic_name_display
                            db.commit()
                except Exception as e:
                    print(f"Error loading generic name from json: {e}")
                    
        if not generic_name_display:
            generic_name_display = "Unknown"
        
        if activity == "completeness":
            # Extract completeness findings
            # Get missing mandatory attributes from issues table
            missing_issues = db.query(Issue).filter(
                Issue.audit_record_id == audit.id,
                Issue.issue_type == "MIS"
            ).all()
            missing_attrs = [issue.attribute for issue in missing_issues]
            missing_attrs_str = ", ".join(missing_attrs)
            
            summary_rows.append({
                "SKU ID": med.id,
                "URL": med.url,
                "Product Name": med.name or "Unknown",
                "Generic Name": generic_name_display,
                "Completeness Score (%)": audit.completeness_score or 0.0,
                "Status": audit.status or "Pending",
                "Missing Attributes Count": len(missing_attrs),
                "Missing Mandatory Attributes": missing_attrs_str,
                "Audited At": audited_at_str
            })
            
            for issue in missing_issues:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": issue.attribute,
                    "Error Categorization": "Incomplete",
                    "Part Written Wrong": "Missing from content",
                    "Suggested Correction": issue.suggested_content,
                    "Severity": issue.severity,
                    "Comments": issue.reviewer_comments
                })
                
        elif activity in ["readability", "consumability"]:
            summary_rows.append({
                "SKU ID": med.id,
                "URL": med.url,
                "Product Name": med.name or "Unknown",
                "Generic Name": generic_name_display,
                "Flesch Reading Ease": audit.flesch_reading_ease if audit.flesch_reading_ease is not None else "N/A",
                "Flesch-Kincaid Grade Level": audit.flesch_kincaid_grade if audit.flesch_kincaid_grade is not None else "N/A",
                "Status": audit.status or "Pending",
                "Audited At": audited_at_str
            })
            
            if audit.flesch_reading_ease is not None and audit.flesch_reading_ease < 50:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": "Flesch Reading Ease",
                    "Error Categorization": "Low Quality",
                    "Part Written Wrong": f"Flesch Reading Ease score is {audit.flesch_reading_ease} (Target > 50)",
                    "Suggested Correction": "Simplify the vocabulary and shorten sentence lengths to make the content more readable.",
                    "Severity": "Medium"
                })
            if audit.flesch_kincaid_grade is not None and audit.flesch_kincaid_grade > 10:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": "Flesch-Kincaid Grade Level",
                    "Error Categorization": "Low Quality",
                    "Part Written Wrong": f"Flesch-Kincaid Grade Level is {audit.flesch_kincaid_grade} (Target < 10)",
                    "Suggested Correction": "Simplify sentence structures to reduce the reading grade level.",
                    "Severity": "Medium"
                })
                
        elif activity == "accuracy":
            # Extract accuracy findings
            accuracy_issues = db.query(Issue).filter(
                Issue.audit_record_id == audit.id,
                (Issue.issue_type != "MIS") | (Issue.reviewer_comments.like("%Audit%")) | (Issue.reviewer_comments.like("%AI%"))
            ).all()
            
            critical_count = sum(1 for issue in accuracy_issues if issue.severity == "Critical")
            high_count = sum(1 for issue in accuracy_issues if issue.severity == "High")
            med_count = sum(1 for issue in accuracy_issues if issue.severity == "Medium")
            low_count = sum(1 for issue in accuracy_issues if issue.severity == "Low")
            info_count = sum(1 for issue in accuracy_issues if issue.severity == "Informational")
            
            # Evaluate attribute wise accuracy for all 24 attributes
            all_attrs = [
                "product_introduction", "uses", "benefits", "side_effects", 
                "how_to_use", "how_it_works", "alcohol", "pregnancy", 
                "breastfeeding", "driving", "kidney", "liver", "quick_tips", 
                "chemical_class", "therapeutic_class", "habit_forming", 
                "action_class", "drug_interactions", "faqs",
                "product_summary", "dosage", "overdose", "missed_dose", "substitutes"
            ]
            
            # Map of attribute matching patterns
            attr_mapping = {
                "product_introduction": ["product introduction", "introduction", "intro"],
                "uses": ["uses", "indication", "approved indications"],
                "benefits": ["benefits"],
                "side_effects": ["side effects", "adverse events", "adverse"],
                "how_to_use": ["how to use", "administration"],
                "how_it_works": ["how it works", "mechanism"],
                "alcohol": ["alcohol"],
                "pregnancy": ["pregnancy"],
                "breastfeeding": ["breastfeeding"],
                "driving": ["driving"],
                "kidney": ["kidney"],
                "liver": ["liver"],
                "quick_tips": ["quick tips", "tips"],
                "chemical_class": ["chemical class"],
                "therapeutic_class": ["therapeutic class"],
                "habit_forming": ["habit forming"],
                "action_class": ["action class"],
                "drug_interactions": ["drug interactions", "interactions"],
                "faqs": ["faqs", "faq"],
                "product_summary": ["product summary", "summary"],
                "dosage": ["dosage", "dose"],
                "overdose": ["overdose"],
                "missed_dose": ["missed dose"],
                "substitutes": ["substitutes", "alternative brands", "alternatives"]
            }
            
            # Formatting Rule: "Accurate" if no issues, otherwise the exact issue description
            attr_status = {a: "Accurate" for a in all_attrs}
            
            for issue in accuracy_issues:
                issue_attr = (issue.attribute or "").strip().lower()
                status_str = issue.current_content or issue.suggested_content or f"Incorrect information in {issue.attribute}"
                
                # Find matching attribute
                matched = False
                for a_key, patterns in attr_mapping.items():
                    if any(p in issue_attr for p in patterns):
                        attr_status[a_key] = status_str
                        matched = True
                        break
            
            # Severity classification (one severity per SKU)
            if critical_count > 0:
                sku_severity = "🔴 Critical"
            elif high_count > 0:
                sku_severity = "🟠 Major"
            elif med_count > 0 or low_count > 0:
                sku_severity = "🟡 Moderate"
            else:
                sku_severity = "🔵 Minor"
                
            # Score out of 10
            overall_score = round((audit.medical_accuracy_score or 0.0) / 10.0, 1)
            
            # Overall Comments: 2-4 bullet points summarizing major findings
            comments_list = []
            if not accuracy_issues:
                comments_list.append("No medical quality issues or regulatory non-compliance detected.")
                comments_list.append("Molecule information is accurate and aligned with SmPC guidelines.")
            else:
                if critical_count > 0:
                    comments_list.append("Critical patient safety warnings or contraindications are omitted.")
                if high_count > 0:
                    comments_list.append("Major medical inaccuracies or off-label indications found.")
                if med_count > 0 or low_count > 0:
                    comments_list.append("Clinical incompleteness or minor editorial adjustments required.")
                # Add specific suggestion summaries
                for issue in accuracy_issues[:2]:
                    comments_list.append(f"{issue.attribute}: {issue.suggested_content}")
            
            overall_comments = "\n".join([f"• {c}" for c in comments_list[:4]])
            
            summary_rows.append({
                "SKU Name": med.name or "Unknown",
                "Drug Name": generic_name_display,
                "SKU ID": med.id,
                "Product Introduction Accuracy": attr_status["product_introduction"],
                "Uses Accuracy": attr_status["uses"],
                "Benefits Accuracy": attr_status["benefits"],
                "Side Effects Accuracy": attr_status["side_effects"],
                "How to Use Accuracy": attr_status["how_to_use"],
                "How It Works Accuracy": attr_status["how_it_works"],
                "Alcohol Safety Accuracy": attr_status["alcohol"],
                "Pregnancy Safety Accuracy": attr_status["pregnancy"],
                "Breastfeeding Safety Accuracy": attr_status["breastfeeding"],
                "Driving Safety Accuracy": attr_status["driving"],
                "Kidney Safety Accuracy": attr_status["kidney"],
                "Liver Safety Accuracy": attr_status["liver"],
                "Quick Tips Accuracy": attr_status["quick_tips"],
                "Chemical Class Accuracy": attr_status["chemical_class"],
                "Therapeutic Class Accuracy": attr_status["therapeutic_class"],
                "Habit Forming Accuracy": attr_status["habit_forming"],
                "Action Class Accuracy": attr_status["action_class"],
                "Drug Interactions Accuracy": attr_status["drug_interactions"],
                "FAQs Accuracy": attr_status["faqs"],
                "Product Summary Accuracy": attr_status["product_summary"],
                "Dosage Accuracy": attr_status["dosage"],
                "Overdose Accuracy": attr_status["overdose"],
                "Missed Dose Accuracy": attr_status["missed_dose"],
                "Overall Comments": overall_comments,
                "Overall Score (/10)": overall_score,
                "Severity": sku_severity
            })
            
            for issue in accuracy_issues:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": issue.attribute,
                    "Error Categorization": get_friendly_issue_type(issue.issue_type),
                    "Part Written Wrong": issue.current_content,
                    "Suggested Correction": issue.suggested_content,
                    "Severity": issue.severity,
                    "Regulatory Source": issue.regulatory_source,
                    "Regulatory Section": issue.regulatory_section,
                    "Evidence / Citation": issue.evidence_text
                })
                
        elif activity in ["seo", "seo_geo"]:
            # Load detailed SEO/GEO cache JSON report if it exists
            missing_keywords_str = ""
            missing_prompts_str = ""
            
            keywords_list = []
            prompts_list = []
            
            if audit.seo_geo_report_path:
                report_abs = os.path.join(settings.DATA_DIR, audit.seo_geo_report_path)
                if os.path.exists(report_abs):
                    try:
                        with open(report_abs, "r", encoding="utf-8") as rf:
                            saved_results = json.load(rf)
                        keywords_list = saved_results.get("missing_keywords", [])
                        prompts_list = saved_results.get("missing_prompts", [])
                        missing_keywords_str = ", ".join(keywords_list)
                        missing_prompts_str = " | ".join(prompts_list)
                    except Exception as e:
                        print(f"[Excel Exporter] Warning: Failed to parse SEO report file: {str(e)}")
            
            summary_rows.append({
                "SKU ID": med.id,
                "URL": med.url,
                "Product Name": med.name or "Unknown",
                "Generic Name": generic_name_display,
                "SEO Score (%)": audit.seo_score or 0.0,
                "GEO Score (%)": audit.geo_score or 0.0,
                "Status": audit.status or "Pending",
                "Missing SEO/GEO Keywords": missing_keywords_str,
                "Missing Search Prompts": missing_prompts_str,
                "Audited At": audited_at_str
            })
            
            for kw in keywords_list:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": "SEO Keywords",
                    "Error Categorization": "Incomplete",
                    "Part Written Wrong": f"Missing search keyword: '{kw}'",
                    "Suggested Correction": f"Incorporate the keyword '{kw}' naturally into the page content.",
                    "Severity": "Medium"
                })
            for pr in prompts_list:
                details_rows.append({
                    "SKU ID": med.id,
                    "Product Name": med.name or "Unknown",
                    "Attribute": "Search Prompts",
                    "Error Categorization": "Incomplete",
                    "Part Written Wrong": f"Missing answer for query: '{pr}'",
                    "Suggested Correction": f"Add information to directly address the search query: '{pr}'.",
                    "Severity": "Medium"
                })
            
    if not summary_rows:
        print(f"[Excel Exporter] No records found to export for activity: {activity}")
        return
        
    try:
        df_summary = pd.DataFrame(summary_rows)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            if details_rows:
                df_details = pd.DataFrame(details_rows)
                df_details.to_excel(writer, sheet_name='Detailed Findings', index=False)
                
        print(f"[Excel Exporter] Successfully exported activity file: {output_path}")
    except Exception as e:
        print(f"[Excel Exporter] Error exporting activity Excel file for '{activity}': {str(e)}")


