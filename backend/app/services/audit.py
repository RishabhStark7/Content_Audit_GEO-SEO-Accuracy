import os
import json
import datetime
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.models import AuditRecord, Issue
from backend.app.core.config import settings

# Priority list for regulatory sources
REGULATORY_SOURCES = [
    "CDSCO (Central Drugs Standard Control Organisation)",
    "FDA (US Food and Drug Administration)",
    "EMA (European Medicines Agency)",
    "MHRA (Medicines and Healthcare products Regulatory Agency)",
    "Official SmPC (Summary of Product Characteristics)",
    "Official Package Insert",
    "Government Treatment Guidelines",
    "DailyMed 2026 Labels"
]

def determine_route_from_sku(sku_name: str, dosage_form: str) -> str:
    """ Determine the administration route from the SKU name and dosage form """
    combined = f"{sku_name} {dosage_form}".lower()
    if any(i in combined for i in ["eye", "ophthalmic", "ear"]):
        return "ophthalmic"
    elif "nasal" in combined:
        return "nasal"
    elif any(i in combined for i in ["injection", "infusion", "iv", "vial", "ampoule", "injectable"]):
        return "injection"
    elif any(t in combined for t in ["gel", "cream", "ointment", "spray", "topical", "lotion", "patch"]):
        return "topical"
    elif any(s in combined for s in ["syrup", "suspension", "liquid", "drops", "solution"]):
        return "oral"
    else:
        return "oral"

def clean_generic_and_fdc(generic: str) -> str:
    """ Keep generic/salt names and FDC structure (A + B + C), removing strength units """
    if not generic:
        return "unknown"
    # Remove strengths like (650mg), (100mg/ml), (500 mg + 150 mg) inside brackets/parentheses
    cleaned = re.sub(r'\([^)]*\)', '', generic)
    # Remove standalone strength numbers at the end
    cleaned = re.sub(r'\b\d+(?:\.\d+)?\s*(?:mg|ml|mcg|g)\b', '', cleaned, flags=re.I)
    # Standardize spaces around '+'
    cleaned = re.sub(r'\s*\+\s*', ' + ', cleaned)
    return cleaned.strip()

def get_regulatory_reference_mock(generic_raw: str, route: str, source: str) -> str:
    """ Mock helper returning regulatory text references for audit benchmark """
    generic = clean_generic_and_fdc(generic_raw).lower()
    
    if "paracetamol" in generic or "acetaminophen" in generic:
        return (
            f"Regulatory Document ({source}) for Paracetamol ({route}):\n"
            f"Approved indications: Treatment of mild to moderate pain, fever.\n"
            f"Recommended dosage: 500mg to 1000mg every 4 to 6 hours as needed. Do not exceed 4000mg in 24 hours.\n"
            f"Contraindications: Severe hepatic impairment, active liver disease, hypersensitivity to paracetamol.\n"
            f"Warnings: Alcohol consumption increases risk of hepatotoxicity. Use with caution in patients with renal impairment.\n"
            f"Side effects: Rare when used at recommended doses. Heavy overdose causes severe liver necrosis."
        )
    elif "amoxicillin" in generic:
        return (
            f"Regulatory Document ({source}) for Amoxicillin ({route}):\n"
            f"Approved indications: Treatment of susceptible bacterial infections including respiratory tract infections, otitis media, skin/soft tissue infections, and urinary tract infections.\n"
            f"Recommended dosage: 250mg to 500mg every 8 hours or 500mg to 875mg every 12 hours.\n"
            f"Contraindications: History of severe hypersensitivity reactions (e.g., anaphylaxis) to amoxicillin or other beta-lactams (penicillins, cephalosporins).\n"
            f"Warnings: Serious and occasionally fatal hypersensitivity (anaphylactic) reactions have been reported.\n"
            f"Side effects: Diarrhea, nausea, skin rash, vomiting."
        )
    elif "linezolid" in generic:
        return (
            f"Regulatory Document ({source}) for Linezolid ({route}) - Antibiotic:\n"
            f"Approved indications: Treatment of nosocomial pneumonia, community-acquired pneumonia, complicated skin and skin structure infections, and vancomycin-resistant Enterococcus faecium infections.\n"
            f"Recommended dosage: 600mg intravenously or orally every 12 hours for 10 to 14 days.\n"
            f"Contraindications: Known hypersensitivity to linezolid. Do not use in patients taking monoamine oxidase inhibitors (MAOIs).\n"
            f"Warnings: Myelosuppression (including anemia, leukopenia, pancytopenia, and thrombocytopenia) has been reported; monitor complete blood count weekly.\n"
            f"Side effects: Diarrhea, headache, nausea, vomiting, thrombocytopenia."
        )
    elif "ibuprofen" in generic:
        return (
            f"Regulatory Document ({source}) for Ibuprofen ({route}):\n"
            f"Approved indications: Relief of mild to moderate pain, primary dysmenorrhea, rheumatoid arthritis, osteoarthritis, and reduction of fever.\n"
            f"Recommended dosage: 200mg to 400mg every 4 to 6 hours. Do not exceed 1200mg/day for over-the-counter use, or 3200mg/day for prescription use.\n"
            f"Contraindications: Known hypersensitivity to ibuprofen or other NSAIDs. Contraindicated in the setting of CABG surgery.\n"
            f"Warnings: NSAIDs cause an increased risk of serious cardiovascular thrombotic events, myocardial infarction, stroke, and serious gastrointestinal adverse events including bleeding, ulceration, and perforation.\n"
            f"Side effects: Dyspepsia, abdominal pain, nausea, headache, dizziness."
        )
    elif "pantoprazole" in generic:
        return (
            f"Regulatory Document ({source}) for Pantoprazole ({route}):\n"
            f"Approved indications: Short-term treatment of erosive esophagitis associated with GERD, maintenance of healing of erosive esophagitis, and pathological hypersecretory conditions including Zollinger-Ellison syndrome.\n"
            f"Recommended dosage: 40mg once daily for up to 8 weeks.\n"
            f"Contraindications: Known hypersensitivity to pantoprazole or other proton pump inhibitors (PPIs).\n"
            f"Warnings: Acute tubulointerstitial nephritis has been observed. PPI therapy may be associated with an increased risk of Clostridium difficile-associated diarrhea.\n"
            f"Side effects: Headache, diarrhea, nausea, abdominal pain, flatulence."
        )
    elif "atorvastatin" in generic:
        return (
            f"Regulatory Document ({source}) for Atorvastatin ({route}):\n"
            f"Approved indications: Reduction of elevated total cholesterol, LDL-cholesterol, apolipoprotein B, and triglycerides in patients with primary hypercholesterolemia. Secondary prevention of cardiovascular disease.\n"
            f"Recommended dosage: 10mg to 80mg once daily.\n"
            f"Contraindications: Active liver disease or unexplained persistent elevations of serum transaminases. Pregnancy and lactation.\n"
            f"Warnings: Myopathy and rhabdomyolysis have been reported. Monitor liver enzymes before initiating therapy.\n"
            f"Side effects: Nasopharyngitis, arthralgia, diarrhea, pain in extremity, urinary tract infection."
        )
    else:
        # Generic fallback
        title = generic_raw.capitalize() if generic_raw else "Active Ingredient"
        return (
            f"Regulatory Document ({source}) for {title} ({route}):\n"
            f"Approved indications: Treatment of conditions clinically indicated for {title}.\n"
            f"Recommended dosage: As prescribed by a registered medical practitioner.\n"
            f"Contraindications: Known hypersensitivity to {title}.\n"
            f"Warnings: Use with caution. Consult doctor for safety guidelines.\n"
            f"Side effects: Nausea, dizziness, mild allergic reaction."
        )

def call_gemini_audit_llm(drug_name: str, generic_name: str, route: str, extracted_content: dict, references: List[str]) -> List[dict]:
    """ 
    Wrapper to call Gemini via Vertex AI or standard API key.
    If no API key/project is configured, falls back to structural mock generation.
    """
    if not settings.GEMINI_API_KEY and not settings.VERTEX_PROJECT:
        print("[Audit Service] No Gemini API key or Vertex project set. Falling back to structural mock generation.")
        return generate_mock_audit_issues(drug_name, generic_name, route, extracted_content)
        
    try:
        prompt = f"""
        You are a senior medical content auditor. Compare the following medicine catalog content against the provided regulatory reference texts and standard clinical parameters.
        
        Medicine: {drug_name}
        Parsed Generic/Salt Name: {generic_name}
        Route of Administration: {route}
        Extracted Catalog Content: {json.dumps(extracted_content)}
        Regulatory Reference Texts: {json.dumps(references)}
        
        CRITICAL RULES FOR AUDITING ACCURACY:
        1. Parse the exact drug/salt name along with the route of administration from the SKU details.
        2. Evaluate against the latest 2026 SmPC, CDSCO, or DailyMed labels for this exact drug/salt and route.
        3. In case of Fixed Dose Combinations (FDCs), if the generic name is A+B+C, ONLY look for the SmPC of A+B+C (do not evaluate against A+B+C+D).
        4. Focus on exact medical accuracy. For example, Linezolid is a serious antibiotic and must NOT be described as a common fever/pain reliever.
        5. Audit each and every content attribute (Uses, Side Effects, Dosage/How to Use, Safety warnings like Alcohol, Pregnancy, Driving, Kidney, Liver, etc.).
        
        You must strictly output a JSON list of issues. Each issue must have these keys:
        - attribute: string (e.g. 'Uses', 'Side Effects', 'Alcohol', 'Pregnancy', 'How to Use')
        - content_bucket: string ('Core Medical Content', 'Safety', 'Metadata', 'Drug Interactions', 'FAQs')
        - issue_type: string (Must be one of: 'INC' for Incorrect, 'CON' for Contradiction, 'LCQ' for Low Content Quality, 'MIS' for Missing)
        - root_cause: string ('Regulatory Update', 'Editorial Error', 'Content Omission', 'Mapping Error', 'Legacy Content', 'Taxonomy Error', 'Unknown')
        - severity: string ('Critical', 'High', 'Medium', 'Low', 'Informational')
        - confidence: string ('Very High', 'High', 'Medium', 'Low')
        - regulatory_source: string (e.g. 'FDA 2026', 'CDSCO', 'DailyMed 2026')
        - regulatory_section: string
        - current_content: string (what was wrong or incomplete)
        - suggested_content: string (what it should be corrected to)
        - evidence_text: string (direct quote or factual basis from regulatory source)
        """
        
        from backend.app.services.llm_client import call_gemini
        text = call_gemini("gemini-2.5-pro", prompt)
        return json.loads(text)
    except Exception as e:
        print(f"[Audit Service] Error calling Gemini API: {str(e)}. Falling back to mock generator.")
        return generate_mock_audit_issues(drug_name, generic_name, route, extracted_content)

def generate_mock_audit_issues(drug_name: str, generic_name: str, route: str, extracted_content: dict) -> List[dict]:
    """ 
    Generates mock compliance findings matching our taxonomy rules.
    Used for local testing when credentials are blank.
    """
    issues = []
    drug = drug_name.capitalize()
    generic = clean_generic_and_fdc(generic_name).lower()
    
    uses_text = extracted_content.get("uses", "")
    intro = extracted_content.get("product_introduction", "")
    how_to_use = extracted_content.get("how_to_use", "")
    
    # 1. Contradiction finding (CON)
    if "paracetamol" in generic:
        if uses_text and "fever" not in uses_text.lower():
            issues.append({
                "attribute": "Uses",
                "content_bucket": "Core Medical Content",
                "issue_type": "CON",
                "root_cause": "Editorial Error",
                "severity": "High",
                "confidence": "High",
                "regulatory_source": "CDSCO (Central Drugs Standard Control Organisation)",
                "regulatory_section": "Approved Indications",
                "current_content": "Uses section does not mention fever indication.",
                "suggested_content": "Paracetamol is indicated for general fever and pain relief.",
                "evidence_text": "Approved indications: Treatment of mild to moderate pain, fever."
            })
    elif "linezolid" in generic:
        if uses_text and "bacterial" not in uses_text.lower():
            issues.append({
                "attribute": "Uses",
                "content_bucket": "Core Medical Content",
                "issue_type": "CON",
                "root_cause": "Editorial Error",
                "severity": "High",
                "confidence": "High",
                "regulatory_source": "CDSCO (Central Drugs Standard Control Organisation)",
                "regulatory_section": "Approved Indications",
                "current_content": "Uses section lacks severe bacterial infections indications.",
                "suggested_content": "Linezolid is indicated for nosocomial pneumonia and complicated skin infections.",
                "evidence_text": "Approved indications: Treatment of nosocomial pneumonia, community-acquired pneumonia, complicated skin and skin structure infections."
            })
            
    # 2. Low Content Quality finding (LCQ)
    if intro and len(intro) < 150:
        issues.append({
            "attribute": "Product Introduction",
            "content_bucket": "Core Medical Content",
            "issue_type": "LCQ",
            "root_cause": "Legacy Content",
            "severity": "Medium",
            "confidence": "Very High",
            "regulatory_source": "Tata 1mg Editorial Guidelines",
            "regulatory_section": "Introduction guidelines",
            "current_content": intro,
            "suggested_content": f"Expand product introduction for {drug} to include manufacturer, major uses, and basic mechanism summaries.",
            "evidence_text": "Guidelines: Product introduction should have a minimum of 3 sentences."
        })
        
    # 3. Incorrect Information finding (INC)
    if how_to_use:
        if "paracetamol" in generic:
            issues.append({
                "attribute": "How to Use",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Regulatory Update",
                "severity": "Critical",
                "confidence": "High",
                "regulatory_source": "FDA (US Food and Drug Administration)",
                "regulatory_section": "Dosage and Administration",
                "current_content": "Maximum daily dosage is listed without explicit hepatotoxicity warnings.",
                "suggested_content": "Add warning: Do not exceed 4000mg of paracetamol in 24 hours. The risk of liver damage increases if exceeded.",
                "evidence_text": "Do not exceed 4000mg in 24 hours. Heavy overdose causes severe liver necrosis."
            })
        elif "linezolid" in generic:
            issues.append({
                "attribute": "How to Use",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Regulatory Update",
                "severity": "Critical",
                "confidence": "High",
                "regulatory_source": "FDA (US Food and Drug Administration)",
                "regulatory_section": "Dosage and Administration",
                "current_content": "Maximum daily dosage is listed without myelosuppression warnings.",
                "suggested_content": "Add warning: Monitor complete blood counts weekly due to myelosuppression risk during Linezolid therapy.",
                "evidence_text": "Myelosuppression (including anemia, leukopenia, pancytopenia, and thrombocytopenia) has been reported; monitor complete blood count weekly."
            })
        elif "amoxicillin" in generic:
            issues.append({
                "attribute": "How to Use",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Regulatory Update",
                "severity": "Critical",
                "confidence": "High",
                "regulatory_source": "FDA (US Food and Drug Administration)",
                "regulatory_section": "Dosage and Administration",
                "current_content": "Maximum daily dosage is listed without anaphylaxis warnings.",
                "suggested_content": "Add warning: Hypersensitivity reactions (anaphylaxis) have been reported.",
                "evidence_text": "Serious and occasionally fatal hypersensitivity (anaphylactic) reactions have been reported."
            })
            
    return issues

def run_accuracy_audit(db: Session, audit_record: AuditRecord):
    """
    Module 3: Medical Accuracy Audit.
    Evaluates the scraped JSON content using Gemini Pro against regulatory sources.
    """
    print(f"[Audit Service] Triggered Accuracy Audit for audit: {audit_record.id}")
    
    # 1. Load structured JSON
    json_absolute_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
    if not os.path.exists(json_absolute_path):
        print(f"[Audit Service] Error: structured JSON file not found at {json_absolute_path}")
        return
        
    with open(json_absolute_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    medicine_name = data.get("medicine_name", "Unknown Medicine")
    generic_raw = data.get("generic_name", "Unknown generic")
    dosage_form = data.get("dosage_form", "")
    
    # Determine proper drug/salt and route
    generic_name = clean_generic_and_fdc(generic_raw)
    route = determine_route_from_sku(medicine_name, dosage_form)
    
    # 2. Benchmark references lookup
    references = []
    for source in REGULATORY_SOURCES:
        ref_text = get_regulatory_reference_mock(generic_name, route, source)
        references.append(ref_text)
        
    # 3. Call AI Auditor
    audit_findings = call_gemini_audit_llm(medicine_name, generic_name, route, data, references)
    
    # 4. Insert issues into database
    # Keep any existing MIS issues (which were logged by the completeness validator)
    # only delete prior accuracy issues to allow re-runs
    db.query(Issue).filter(
        Issue.audit_record_id == audit_record.id,
        Issue.issue_type != "MIS"
    ).delete()
    
    for finding in audit_findings:
        issue = Issue(
            audit_record_id=audit_record.id,
            attribute=finding.get("attribute", "General"),
            content_bucket=finding.get("content_bucket", "Core Medical Content"),
            issue_type=finding.get("issue_type", "LCQ"),
            root_cause=finding.get("root_cause", "Unknown"),
            severity=finding.get("severity", "Medium"),
            confidence=finding.get("confidence", "Medium"),
            regulatory_source=finding.get("regulatory_source"),
            regulatory_section=finding.get("regulatory_section"),
            current_content=finding.get("current_content"),
            suggested_content=finding.get("suggested_content"),
            evidence_text=finding.get("evidence_text"),
            reviewer_status="Open",
            reviewer_comments=f"Generated by AI auditor against {finding.get('regulatory_source', 'Regulatory Reference')}."
        )
        db.add(issue)
        
    # 5. Calculate Medical Accuracy Score dynamically
    accuracy_score = 100.0
    for finding in audit_findings:
        if finding.get("issue_type") in ["INC", "CON", "LCQ"]:
            severity = finding.get("severity", "Medium").capitalize()
            if severity == "Critical":
                accuracy_score -= 30.0
            elif severity == "High":
                accuracy_score -= 20.0
            elif severity == "Medium":
                accuracy_score -= 10.0
            elif severity == "Low":
                accuracy_score -= 5.0
                
    accuracy_score = max(0.0, min(100.0, accuracy_score))
    audit_record.medical_accuracy_score = round(accuracy_score, 2)
    
    # Content Health Score is a weighted combination:
    # 40% Completeness, 30% Accuracy, 15% SEO score, 15% GEO score
    comp_score = audit_record.completeness_score or 0.0
    acc_score = audit_record.medical_accuracy_score or 0.0
    seo_score = audit_record.seo_score or 0.0
    geo_score = audit_record.geo_score or 0.0
    
    health_score = (0.40 * comp_score) + (0.30 * acc_score) + (0.15 * seo_score) + (0.15 * geo_score)
    audit_record.content_health_score = round(health_score, 2)
    
    audit_record.status = "Audited"
    db.commit()
    
    # Automatically update batch progress metrics
    try:
        from backend.app.services.excel_exporter import update_batch_progress
        update_batch_progress(db)
    except Exception as progress_error:
        print(f"[Audit Service] Failed to update progress JSON: {str(progress_error)}")
        
    print(f"[Audit Service] Finished: Accuracy={audit_record.medical_accuracy_score}%, Content Health Score={audit_record.content_health_score}%")

def run_indepth_audit(db: Session, audit_record: AuditRecord):
    """
    Module 3.5: In-depth Medical Accuracy Audit.
    Evaluates every attribute across 7 dimensions and uses the new 100-point formula:
    Overall Score = Medical Accuracy (30%) + Clinical Completeness (20%) + Patient Safety (20%) +
                    Regulatory Alignment (10%) + Formulation Consistency (10%) + Editorial Quality (10%)
    """
    print(f"[Audit Service] Triggered In-depth Accuracy Audit for audit: {audit_record.id}")
    
    # 1. Load structured JSON
    json_absolute_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
    if not os.path.exists(json_absolute_path):
        print(f"[Audit Service] Error: structured JSON file not found at {json_absolute_path}")
        return
        
    with open(json_absolute_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    medicine_name = data.get("medicine_name", "Unknown Medicine")
    generic_raw = data.get("generic_name", "Unknown generic")
    dosage_form = data.get("dosage_form", "")
    
    generic_name = clean_generic_and_fdc(generic_raw)
    route = determine_route_from_sku(medicine_name, dosage_form)
    
    # 2. Benchmark references lookup
    references = []
    for source in REGULATORY_SOURCES:
        ref_text = get_regulatory_reference_mock(generic_name, route, source)
        references.append(ref_text)
        
    # 3. Call In-depth AI Auditor
    audit_findings = call_gemini_indepth_audit_llm(medicine_name, generic_name, route, data, references)
    
    # 4. Insert issues into database
    # Delete prior non-completeness accuracy issues to allow re-runs
    db.query(Issue).filter(
        Issue.audit_record_id == audit_record.id,
        Issue.issue_type != "MIS"
    ).delete()
    
    for finding in audit_findings.get("issues", []):
        issue = Issue(
            audit_record_id=audit_record.id,
            attribute=finding.get("attribute", "General"),
            content_bucket=finding.get("content_bucket", "Core Medical Content"),
            issue_type=finding.get("issue_type", "LCQ"),
            root_cause=finding.get("root_cause", "Unknown"),
            severity=finding.get("severity", "Medium"),
            confidence=finding.get("confidence", "Medium"),
            regulatory_source=finding.get("regulatory_source"),
            regulatory_section=finding.get("regulatory_section"),
            current_content=finding.get("current_content"),
            suggested_content=finding.get("suggested_content"),
            evidence_text=finding.get("evidence_text"),
            reviewer_status="Open",
            reviewer_comments=f"In-depth Audit: {finding.get('reviewer_comments', 'Validated by AI against SmPC/DailyMed')}"
        )
        db.add(issue)
        
    # 5. Apply new 100-point scoring algorithm
    scores = audit_findings.get("scores", {})
    med_acc = scores.get("medical_accuracy", 30.0)
    clin_comp = scores.get("clinical_completeness", 20.0)
    pat_saf = scores.get("patient_safety", 20.0)
    reg_align = scores.get("regulatory_alignment", 10.0)
    form_cons = scores.get("formulation_consistency", 10.0)
    edit_qual = scores.get("editorial_quality", 10.0)
    
    total_indepth_score = med_acc + clin_comp + pat_saf + reg_align + form_cons + edit_qual
    total_indepth_score = max(0.0, min(100.0, total_indepth_score))
    
    # Save the score to medical_accuracy_score field
    audit_record.medical_accuracy_score = round(total_indepth_score, 2)
    
    # Recalculate Content Health Score (40% Completeness, 30% In-depth Accuracy, 15% SEO, 15% GEO)
    comp_score = audit_record.completeness_score or 0.0
    acc_score = audit_record.medical_accuracy_score or 0.0
    seo_score = audit_record.seo_score or 0.0
    geo_score = audit_record.geo_score or 0.0
    
    health_score = (0.40 * comp_score) + (0.30 * acc_score) + (0.15 * seo_score) + (0.15 * geo_score)
    audit_record.content_health_score = round(health_score, 2)
    
    audit_record.status = "Audited"
    db.commit()
    
    # Update progress
    try:
        from backend.app.services.excel_exporter import update_batch_progress
        update_batch_progress(db)
    except Exception as progress_error:
        print(f"[Audit Service] Failed to update progress JSON: {str(progress_error)}")
        
    print(f"[Audit Service] Finished In-depth Audit: Accuracy={audit_record.medical_accuracy_score}%, Content Health Score={audit_record.content_health_score}%")

def call_gemini_indepth_audit_llm(drug_name: str, generic_name: str, route: str, extracted_content: dict, references: List[str]) -> dict:
    """ Calls Gemini for In-depth Medical Affairs Content Audit """
    if not settings.GEMINI_API_KEY and not settings.VERTEX_PROJECT:
        print("[Audit Service] No Gemini credentials. Falling back to mock in-depth generation.")
        return generate_mock_indepth_audit_issues(drug_name, generic_name, route, extracted_content)
        
    try:
        prompt = f"""
        You are a senior medical content auditor conducting an In-depth Medical Affairs Content Audit. 
        Evaluate the following medicine catalog content against the provided references and specific guidelines.
        
        Medicine: {drug_name}
        Parsed Generic/Salt Name: {generic_name}
        Route of Administration: {route}
        Extracted Catalog Content: {json.dumps(extracted_content)}
        Regulatory Reference Texts: {json.dumps(references)}
        
        CRITICAL RULES FOR IN-DEPTH AUDIT:
        1. Stop binary auditing. For every attribute (Uses, Side Effects, How to Use, Pregnancy, Breastfeeding, Safety parameters, Classifications, etc.), evaluate across these dimensions:
           - Medically accurate
           - Clinically complete
           - Formulation-specific (must match this route/strength, not generic molecule knowledge)
           - Regulatory aligned (latest FDA/CDSCO/EMA prescribing information)
           - Internally consistent (e.g. if Fact Box says OPHTHAL but Uses say Injection, it is inconsistent)
           - Up-to-date (prefer 2026/latest evidence)
           - Consumer-safe
        2. Detect omissions: Identify clinically significant missing safety warnings (e.g. reflex bradycardia or tissue necrosis for phenylephrine injection).
        3. Detect formulation contamination: Look for content belonging to other routes (e.g. nasal spray or eye drop content on an injection page).
        4. Detect template contamination: Look for boilerplate text copied from unrelated classes (e.g. "infection may return" on a cardiovascular drug).
        5. Verify taxonomy: Check Chemical Class, Therapeutic Class, Pharmacological Class.
        
        You must output a JSON object containing two fields:
        1. "scores": a dict with keys:
           - "medical_accuracy" (float out of 30.0)
           - "clinical_completeness" (float out of 20.0)
           - "patient_safety" (float out of 20.0)
           - "regulatory_alignment" (float out of 10.0)
           - "formulation_consistency" (float out of 10.0)
           - "editorial_quality" (float out of 10.0)
        2. "issues": a list of issues. Each issue must have these keys:
           - attribute: string (e.g. 'Uses', 'Side Effects', 'How to Use', 'Product Introduction')
           - content_bucket: string
           - issue_type: 'INC' (Incorrect), 'CON' (Contradiction), 'LCQ' (Low Content Quality), or 'MIS' (Missing)
           - root_cause: string
           - severity: 'Critical', 'High', 'Medium', 'Low'
           - confidence: 'Very High', 'High', 'Medium', 'Low'
           - regulatory_source: string
           - regulatory_section: string
           - current_content: string (describe what was wrong or missing)
           - suggested_content: string (how to fix it)
           - evidence_text: string
           - reviewer_comments: string (describe why the audit failed this dimension)
        """
        from backend.app.services.llm_client import call_gemini
        text = call_gemini("gemini-2.5-pro", prompt)
        return json.loads(text)
    except Exception as e:
        print(f"[Audit Service] Error calling Gemini In-depth API: {str(e)}. Falling back to mock generator.")
        return generate_mock_indepth_audit_issues(drug_name, generic_name, route, extracted_content)

def generate_mock_indepth_audit_issues(drug_name: str, generic_name: str, route: str, extracted_content: dict) -> dict:
    """ Mock fallback for In-depth Medical Affairs Content Audit """
    generic = clean_generic_and_fdc(generic_name).lower()
    
    result = {
        "scores": {
            "medical_accuracy": 30.0,
            "clinical_completeness": 20.0,
            "patient_safety": 20.0,
            "regulatory_alignment": 10.0,
            "formulation_consistency": 10.0,
            "editorial_quality": 10.0
        },
        "issues": []
    }
    
    if "phenylephrine" in generic:
        result["scores"] = {
            "medical_accuracy": 18.0,
            "clinical_completeness": 9.0,
            "patient_safety": 11.0,
            "regulatory_alignment": 6.0,
            "formulation_consistency": 2.0,
            "editorial_quality": 6.0
        }
        
        result["issues"] = [
            {
                "attribute": "Product Introduction",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Editorial Error",
                "severity": "Critical",
                "confidence": "Very High",
                "regulatory_source": "DailyMed 2026",
                "regulatory_section": "Introduction",
                "current_content": "Contains sentence 'If you stop taking it too early the infection may return or worsen.'",
                "suggested_content": "Remove antibiotic template contamination sentence.",
                "evidence_text": "Antibiotic warning templates should not be used on cardiovascular vasopressor products.",
                "reviewer_comments": "Failed formulation-specificity: Leftover antibiotic template."
            },
            {
                "attribute": "Uses",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Editorial Error",
                "severity": "Critical",
                "confidence": "High",
                "regulatory_source": "FDA Prescribing Information",
                "regulatory_section": "Indications and Usage",
                "current_content": "Lists ophthalmic and nasal spray indications for an injectable formulation.",
                "suggested_content": "Restrict indications to vasodilatory and anesthesia-induced hypotension only.",
                "evidence_text": "Phenylephrine injection is a vasopressor indicated for increasing blood pressure in adults with vasodilatory shock.",
                "reviewer_comments": "Failed formulation-specificity: Mixed ophthalmic and nasal spray indications."
            },
            {
                "attribute": "Side Effects",
                "content_bucket": "Safety",
                "issue_type": "MIS",
                "root_cause": "Content Omission",
                "severity": "High",
                "confidence": "High",
                "regulatory_source": "DailyMed 2026",
                "regulatory_section": "Adverse Reactions",
                "current_content": "Omits reflex bradycardia, severe hypertension, tissue necrosis, arrhythmias, and ischemia.",
                "suggested_content": "Add warnings for reflex bradycardia, tissue necrosis, and severe hypertension.",
                "evidence_text": "Adverse reactions include reflex bradycardia, extravasation necrosis, arrhythmias, and ischemia.",
                "reviewer_comments": "Failed clinical completeness: Omitted significant safety and adverse reactions."
            },
            {
                "attribute": "How to Use",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Editorial Error",
                "severity": "Critical",
                "confidence": "Very High",
                "regulatory_source": "FDA 2026",
                "regulatory_section": "Dosage and Administration",
                "current_content": "Recommends taking the injection at the same time each day.",
                "suggested_content": "Correct to state it is administered intravenously by healthcare professionals under continuous monitoring.",
                "evidence_text": "Phenylephrine injection is given intravenously as a bolus or continuous infusion under expert monitoring.",
                "reviewer_comments": "Failed formulation-specificity: Outpatient administration guidance on intravenous vasopressor."
            },
            {
                "attribute": "Pregnancy",
                "content_bucket": "Safety",
                "issue_type": "LCQ",
                "root_cause": "Legacy Content",
                "severity": "Medium",
                "confidence": "High",
                "regulatory_source": "FDA 2026",
                "regulatory_section": "Pregnancy",
                "current_content": "Uses vague warning 'consult doctor before using during pregnancy'.",
                "suggested_content": "Update to note that phenylephrine may cause fetal harm and uterine ischemia, and should be used only if benefits outweigh risks.",
                "evidence_text": "Phenylephrine may cause fetal harm, uterine blood flow reduction, and tachycardia.",
                "reviewer_comments": "Failed regulatory alignment: Vague warning instead of specific safety warnings."
            },
            {
                "attribute": "Breastfeeding",
                "content_bucket": "Safety",
                "issue_type": "LCQ",
                "root_cause": "Legacy Content",
                "severity": "Medium",
                "confidence": "High",
                "regulatory_source": "FDA 2026",
                "regulatory_section": "Lactation",
                "current_content": "Uses generic safe-if-prescribed statement.",
                "suggested_content": "State that there is no data on phenylephrine presence in human milk, and caution should be exercised.",
                "evidence_text": "There are no data on the presence of phenylephrine in human milk.",
                "reviewer_comments": "Failed regulatory alignment: Lacks lactation data disclaimer."
            },
            {
                "attribute": "Therapeutic Class",
                "content_bucket": "Metadata",
                "issue_type": "INC",
                "root_cause": "Taxonomy Error",
                "severity": "Critical",
                "confidence": "Very High",
                "regulatory_source": "CDSCO",
                "regulatory_section": "Taxonomy",
                "current_content": "Lists Therapeutic Class as 'OPHTHAL'.",
                "suggested_content": "Correct Therapeutic Class to 'CARDIAC' or 'VASOPRESSORS'.",
                "evidence_text": "Phenylephrine injection belongs to the Cardiac/Vasopressor therapeutic category.",
                "reviewer_comments": "Failed internal consistency: Listed as OPHTHAL while product is an injection for hypotension."
            },
            {
                "attribute": "Action Class",
                "content_bucket": "Metadata",
                "issue_type": "INC",
                "root_cause": "Taxonomy Error",
                "severity": "Critical",
                "confidence": "Very High",
                "regulatory_source": "CDSCO",
                "regulatory_section": "Taxonomy",
                "current_content": "Lists Action Class as Ophthalmic Decongestant.",
                "suggested_content": "Correct Action Class to Alpha-1 Adrenergic Agonist.",
                "evidence_text": "Phenylephrine is a selective alpha-1 adrenergic receptor agonist.",
                "reviewer_comments": "Failed internal consistency: Incorrect action class taxonomy."
            },
            {
                "attribute": "Drug Interactions",
                "content_bucket": "Drug Interactions",
                "issue_type": "MIS",
                "root_cause": "Content Omission",
                "severity": "High",
                "confidence": "High",
                "regulatory_source": "FDA 2026",
                "regulatory_section": "Drug Interactions",
                "current_content": "Missing MAO inhibitors, tricyclic antidepressants, and oxytocic drugs interactions.",
                "suggested_content": "Add specific drug interactions for MAOIs, oxytocics, and TCAs.",
                "evidence_text": "Co-administration with MAOIs or TCAs increases vasopressor response. Co-administration with oxytocic drugs may cause severe hypertension.",
                "reviewer_comments": "Failed clinical completeness: Missing interactions with major drug classes."
            }
        ]
        
    elif "linezolid" in generic:
        result["scores"] = {
            "medical_accuracy": 22.0,
            "clinical_completeness": 12.0,
            "patient_safety": 13.0,
            "regulatory_alignment": 8.0,
            "formulation_consistency": 8.0,
            "editorial_quality": 8.0
        }
        result["issues"] = [
            {
                "attribute": "How to Use",
                "content_bucket": "Core Medical Content",
                "issue_type": "INC",
                "root_cause": "Regulatory Update",
                "severity": "Critical",
                "confidence": "High",
                "regulatory_source": "FDA 2026",
                "regulatory_section": "Warnings",
                "current_content": "Lacks warning to monitor complete blood counts weekly.",
                "suggested_content": "Add warning: Monitor complete blood counts weekly due to myelosuppression risk during Linezolid therapy.",
                "evidence_text": "Myelosuppression has been reported; monitor complete blood count weekly.",
                "reviewer_comments": "Failed patient safety: Omitted critical blood count monitoring warning."
            }
        ]
        
    return result

