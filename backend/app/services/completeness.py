import os
import json
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.models.models import AuditRecord, Issue
from backend.app.services.readability import calculate_readability
from backend.app.services.seo_geo import analyze_seo_geo
from backend.app.core.config import settings

MANDATORY_ATTRIBUTES = [
    "product_introduction", "uses", "benefits", "side_effects", 
    "how_to_use", "how_it_works", "alcohol", "pregnancy", 
    "breastfeeding", "driving", "kidney", "liver", "quick_tips", 
    "chemical_class", "therapeutic_class", "habit_forming", 
    "action_class", "drug_interactions", "faqs"
]

OPTIONAL_ATTRIBUTES = [
    "product_summary", "dosage", "overdose", "missed_dose", "substitutes"
]

EXPECTED_ATTRIBUTES = MANDATORY_ATTRIBUTES + OPTIONAL_ATTRIBUTES

def run_completeness_validation(db: Session, audit_record: AuditRecord):
    """
    Module 2: Content Completeness, Readability Scorer, and SEO/GEO Analyzer.
    Triggers automatically after scraping is complete.
    """
    print(f"[Completeness Service] Triggered for audit: {audit_record.id}")
    
    # 1. Load the structured JSON data
    # Path is relative to the backend project cwd or settings DATA_DIR
    json_absolute_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
    html_absolute_path = os.path.join(settings.DATA_DIR, audit_record.html_path)
    
    if not os.path.exists(json_absolute_path):
        print(f"[Completeness Service] Error: JSON file not found at: {json_absolute_path}")
        audit_record.status = "Failed"
        db.commit()
        return
        
    with open(json_absolute_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(html_absolute_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Check presence of each expected attribute
    presence_matrix = {}
    
    # Text attributes directly in root
    for attr in ["product_introduction", "uses", "benefits", "how_to_use", "how_it_works", "drug_interactions", "product_summary", "dosage", "overdose", "missed_dose"]:
        val = data.get(attr)
        presence_matrix[attr] = bool(val and len(str(val).strip()) > 3)
        
    # List attributes in root
    for attr in ["side_effects", "quick_tips", "faqs", "substitutes"]:
        val = data.get(attr)
        presence_matrix[attr] = bool(val and len(val) > 0)
        
    # Safety attributes (nested under 'safety')
    safety_block = data.get("safety", {})
    for attr in ["alcohol", "pregnancy", "breastfeeding", "driving", "kidney", "liver"]:
        val = safety_block.get(attr, "")
        # Check if present and not default "Unknown" or empty
        has_val = bool(val and len(str(val).strip()) > 0 and "unknown" not in str(val).lower())
        presence_matrix[attr] = has_val
        
    # Fact Box attributes (nested under 'fact_box')
    fact_block = data.get("fact_box", {})
    for attr in ["chemical_class", "therapeutic_class", "habit_forming", "action_class"]:
        val = fact_block.get(attr, "")
        presence_matrix[attr] = bool(val and len(str(val).strip()) > 0)
        
    # Calculate completeness score based ONLY on mandatory attributes
    present_mandatory_count = sum(1 for attr in MANDATORY_ATTRIBUTES if presence_matrix.get(attr, False))
    completeness_score = (present_mandatory_count / len(MANDATORY_ATTRIBUTES)) * 100.0
    audit_record.completeness_score = round(completeness_score, 2)
    
    # Log missing attributes as issues under the simplified LCQ/MIS taxonomy
    # (Since missing attributes represent "Missing Information" (MIS), we insert them)
    # Clear any existing issues for this audit record to allow re-runs
    db.query(Issue).filter(Issue.audit_record_id == audit_record.id).delete()
    
    for attr, present in presence_matrix.items():
        # Do not flag missing optional elements as compliance issues
        if attr in OPTIONAL_ATTRIBUTES:
            continue
            
        if not present:
            # Map attribute to its corresponding category bucket
            bucket = "Core Medical Content"
            if attr in ["alcohol", "pregnancy", "breastfeeding", "driving", "kidney", "liver"]:
                bucket = "Safety"
            elif attr in ["chemical_class", "therapeutic_class", "habit_forming", "action_class"]:
                bucket = "Metadata"
            elif attr == "side_effects":
                bucket = "Adverse Events"
            elif attr == "drug_interactions":
                bucket = "Drug Interactions"
            elif attr == "faqs":
                bucket = "FAQs"
                
            # Insert a "Missing Information" compliance issue
            missing_issue = Issue(
                audit_record_id=audit_record.id,
                attribute=attr.replace('_', ' ').capitalize(),
                content_bucket=bucket,
                issue_type="MIS", # Missing Information
                root_cause="Content Omission",
                severity="Medium" if bucket != "Core Medical Content" else "High",
                confidence="Very High",
                regulatory_source="Tata 1mg Content Guideline",
                current_content=None,
                suggested_content=f"Add missing information for {attr.replace('_', ' ')}.",
                reviewer_status="Open",
                reviewer_comments="Automatically flagged by completeness validator."
            )
            db.add(missing_issue)

    # 3. Calculate Flesch-Kincaid Readability Scores
    # Concatenate all readable blocks of content
    readable_text = ""
    for field in ["product_introduction", "uses", "benefits", "how_to_use", "how_it_works", "drug_interactions"]:
        val = data.get(field)
        if val:
            readable_text += "\n" + str(val)
            
    # Add FAQs text
    for faq in data.get("faqs", []):
        readable_text += f"\n{faq.get('question', '')} {faq.get('answer', '')}"
        
    readability_results = calculate_readability(readable_text)
    audit_record.flesch_reading_ease = readability_results["flesch_reading_ease"]
    audit_record.flesch_kincaid_grade = readability_results["flesch_kincaid_grade"]
    
    # 4. Perform SEO and GEO Gap Analysis
    seo_geo_results = analyze_seo_geo(html_content, data)
    audit_record.seo_score = seo_geo_results["seo_score"]
    audit_record.geo_score = seo_geo_results["geo_score"]
    
    # Save detailed SEO/GEO JSON report
    slug_dir = os.path.dirname(json_absolute_path)
    report_file = os.path.join(slug_dir, "seo_geo_report.json")
    with open(report_file, "w", encoding="utf-8") as rf:
        json.dump(seo_geo_results, rf, indent=2)
        
    # Store path relative to data folder (matching other files)
    audit_record.seo_geo_report_path = str(Path(report_file).relative_to(settings.DATA_DIR))
    
    # 5. Save everything and update status
    audit_record.status = "Completeness_Checked"
    db.commit()
    
    # Automatically update master Excel file with scraped contents
    try:
        from backend.app.services.excel_exporter import update_scraped_content_excel
        update_scraped_content_excel(db)
    except Exception as excel_error:
        print(f"[Completeness Service] Failed to update Excel: {str(excel_error)}")
        
    print(f"[Completeness Service] Finished: Completeness={audit_record.completeness_score}%, Readability Ease={audit_record.flesch_reading_ease}, SEO={audit_record.seo_score}, GEO={audit_record.geo_score}")
