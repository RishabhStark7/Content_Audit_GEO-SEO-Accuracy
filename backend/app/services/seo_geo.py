import re
import json
import os
from bs4 import BeautifulSoup  # type: ignore  # pyrefly: ignore
from typing import Dict, List, Any
from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.models import AuditRecord
from pathlib import Path
from backend.app.core.config import settings

# Benchmark Dictionary of top 5 Indian brands for key generic drug + route combinations
BENCHMARK_BRANDS = {
    ("paracetamol", "oral"): ["Calpol", "Dolo 650", "Crocin", "Pacimol", "Sumo L"],
    ("paracetamol", "injection"): ["Perfalgan", "Neomol", "Febrinil", "Kabimol", "Paracip IV"],
    ("paracetamol", "topical"): ["Thermacare", "Dynapar Gel", "Volini"],
    ("amoxicillin", "oral"): ["Mox", "Novamox", "Almox", "Moxikind", "Amoxycillin-Kid"],
    ("amoxicillin", "injection"): ["Clavam Injection", "Augmentin Injection", "Moxclav Injection", "Amoxyclav Injection", "Novamox Injection"],
    ("linezolid", "oral"): ["Linospan", "Lizolid", "Linox", "Lizomac", "Lizoforce"],
    ("linezolid", "injection"): ["Linospan IV", "Lizolid IV", "Linox IV", "Lizomac IV", "Lizoforce IV"],
    ("ibuprofen", "oral"): ["Brufen", "Ibugesic", "Combiflam", "Ibucon", "Anaflam"],
    ("pantoprazole", "oral"): ["Pan", "Pantocid", "Pantodac", "Pantosec", "Nupenta"],
    ("pantoprazole", "injection"): ["Pan IV", "Pantocid IV", "Pantodac IV", "Pantocork IV", "Pentalink IV"],
    ("atorvastatin", "oral"): ["Atorva", "Lipvas", "Tonact", "Storvas", "Lipicure"]
}

def clean_generic_name(generic_name: str) -> str:
    """ Clean generic name to its base form (e.g. 'Paracetamol (650mg)' -> 'paracetamol') """
    if not generic_name:
        return "unknown"
    name = generic_name.split('(')[0].split('+')[0].split(',')[0].strip()
    return name.lower()

def determine_route(sku_name: str, dosage_form: str) -> str:
    """ Determine the administration route from SKU name and dosage form """
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

def get_benchmark_brands(generic: str, route: str) -> List[str]:
    """ Retrieve top 5 brands for a given drug + route combination """
    key = (generic, route)
    if key in BENCHMARK_BRANDS:
        return BENCHMARK_BRANDS[key]
    
    title_case_generic = generic.capitalize()
    return [
        f"{title_case_generic} Cipla",
        f"{title_case_generic} Sun",
        f"{title_case_generic} Abbott",
        f"{title_case_generic} Lupin",
        f"{title_case_generic} Alkem"
    ]

def evaluate_content_seo_geo_score(structured_data: dict, route: str) -> tuple[float, list[str]]:
    """
    Computes a Content-Led SEO & GEO Score out of 100 points.
    Formula:
    - Competitor Brand / Keyword Coverage: Max 40 points
    - Indian User Route/Drug Value-Add Prompts Coverage: Max 60 points
    """
    score = 0.0
    text_content = flatten_text(structured_data).lower()
    generic_clean = clean_generic_name(structured_data.get("generic_name", ""))
    
    # 1. Competitor Brand Keyword Density (Max 40 points)
    # Check if competitor brand names or their variants are present in content comparisons
    benchmark_brands = get_benchmark_brands(generic_clean, route)
    brands_found = 0
    for brand in benchmark_brands:
        if brand.lower() in text_content:
            brands_found += 1
            
    # Score allocation: 40 points if at least 1 competitor brand keyword is naturally referenced for comparison,
    # otherwise 0 points.
    if brands_found >= 1:
        score += 40.0

    # 2. Value-Addition Prompts Coverage (Max 60 points)
    # Layman-friendly, Indian-user-focused prompts (no generic OTC or composition checks)
    if "paracetamol" in generic_clean:
        prompts = [
            f"How fast does this paracetamol start working compared to Calpol or Dolo 650?",
            f"Should I take this medicine after food to avoid stomach upset?",
            f"Is it safe to take this medicine for viral fever or dengue?",
            f"What is the gap between two doses of paracetamol tablets?",
            f"Can I take this medicine if I have high blood pressure or diabetes?",
            f"What are the liver safety precautions to take with paracetamol in India?"
        ]
        match_keys = [
            ["fast", "quick", "work", "dolo", "calpol", "starts working", "crocin"],
            ["food", "stomach", "after food", "empty stomach", "upset"],
            ["viral", "dengue", "malaria", "typhoid", "dengue fever"],
            ["gap", "hours", "interval", "between two doses", "frequently", "repeat"],
            ["blood pressure", "diabetes", "hypertension", "bp", "sugar"],
            ["liver", "hepatic", "hepatotoxicity", "alcohol", "damage", "overdose"]
        ]
    elif "linezolid" in generic_clean:
        prompts = [
            f"Is it safe to take linezolid tablets for simple throat infections?",
            f"What food items (like cheese or curd) should I avoid while taking linezolid?",
            f"Why is my blood count monitored weekly during linezolid treatment?",
            f"How long should I continue taking linezolid for pneumonia?",
            f"Can linezolid be used for tuberculosis (TB) treatment in India?",
            f"What should I do if I experience numbness or tingling in hands or feet?"
        ]
        match_keys = [
            ["simple", "throat", "cough", "cold", "common infection"],
            ["food", "cheese", "curd", "tyramine", "avoid", "diet"],
            ["blood count", "weekly", "cbc", "myelosuppression", "platelets", "anemia"],
            ["duration", "days", "long", "pneumonia", "continue"],
            ["tuberculosis", "tb", "mdr-tb", "resistant"],
            ["numbness", "tingling", "neuropathy", "feet", "hands", "nerve"]
        ]
    elif "amoxicillin" in generic_clean:
        prompts = [
            f"Should I complete the amoxicillin course even if I feel better?",
            f"Can amoxicillin cure common cold or flu?",
            f"What should I do if I get a skin rash or diarrhea after taking amoxicillin?",
            f"Can I take amoxicillin tablet with milk or juice?",
            f"Is amoxicillin safe for children's dental infections?",
            f"What are the common antibiotic resistance warnings for amoxicillin in India?"
        ]
        match_keys = [
            ["complete", "course", "stop", "feel better", "duration"],
            ["cold", "flu", "viral", "cough", "virus"],
            ["rash", "diarrhea", "loose motion", "allergy", "side effect"],
            ["milk", "juice", "water", "food", "fluid"],
            ["children", "kids", "dental", "tooth", "infection"],
            ["resistance", "antibiotic resistance", "superbug", "misuse", "overuse"]
        ]
    else:
        # Fallback prompts for other generic medicines
        prompts = [
            f"How does this medicine compare to the top brands?",
            f"Should I take this medicine with or without food?",
            f"What is the correct storage condition for this medicine in Indian summer?",
            f"How long does it take for this medicine to show its full effect?",
            f"What are the critical warning signs that require stopping this medicine immediately?",
            f"Can I take this medicine along with my regular blood pressure or diabetes drugs?"
        ]
        match_keys = [
            ["compare", "alternative", "brand", "better", "substitute"],
            ["food", "empty stomach", "after food", "meals"],
            ["storage", "cool", "heat", "summer", "temperature", "light"],
            ["long", "effect", "action", "work", "absorb"],
            ["warning", "stop", "immediate", "emergency", "doctor", "severe"],
            ["regular", "blood pressure", "diabetes", "interaction", "co-administration"]
        ]
        
    covered_count = 0
    missing_prompts = []
    for pr, keys in zip(prompts, match_keys):
        if any(k in text_content for k in keys):
            covered_count += 1
        else:
            missing_prompts.append(pr)
            
    coverage_score = (covered_count / len(prompts)) * 60.0
    score += coverage_score
    
    return max(0.0, min(100.0, score)), missing_prompts

def flatten_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    elif isinstance(data, list):
        return " ".join(flatten_text(item) for item in data)
    elif isinstance(data, dict):
        return " ".join(flatten_text(val) for val in data.values())
    return ""

def analyze_seo_geo(html_content: str, structured_data: dict) -> dict:
    """ Performs complete SEO/GEO gap analysis without meta-tag constraints """
    generic_raw = structured_data.get("generic_name", "")
    generic_clean = clean_generic_name(generic_raw)
    
    medicine_name = structured_data.get("medicine_name", "")
    dosage_form = structured_data.get("dosage_form", "")
    route = determine_route(medicine_name, dosage_form)
    
    benchmark_brands = get_benchmark_brands(generic_clean, route)
    
    # Evaluate score and identify missing prompts
    score, missing_prompts = evaluate_content_seo_geo_score(structured_data, route)
    
    # Missing keywords: competitor brands or specific warning points not covered in the text
    missing_keywords = []
    text_content = flatten_text(structured_data).lower()
    for brand in benchmark_brands:
        if brand.lower() not in text_content:
            missing_keywords.append(brand)
            
    # Append value-add key clinical parameters if missing
    for clinical_kw in ["dosing frequency", "food interactions", "viral infections", "storage instructions", "safety warnings"]:
        if clinical_kw not in text_content:
            missing_keywords.append(clinical_kw)
            
    return {
        "generic_drug": generic_clean,
        "route_of_administration": route,
        "benchmark_brands": benchmark_brands,
        "seo_score": score,
        "geo_score": score,
        "missing_keywords": missing_keywords[:10],
        "missing_prompts": missing_prompts
    }

def run_seo_geo_ai_audit(db: Session, audit_record: AuditRecord):
    """
    Module 5: AI-based SEO & Prompts Audit using Indian user value-addition points.
    """
    print(f"[SEO & Prompts Audit] Triggered for audit: {audit_record.id}")
    
    # 1. Load JSON content
    json_absolute_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
    if not os.path.exists(json_absolute_path):
        print(f"[SEO & Prompts Audit] Error: Structured JSON not found for audit {audit_record.id}")
        return
        
    with open(json_absolute_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    raw_text = flatten_text(data)
    
    # 2. Call AI or run local heuristic fallback
    if not settings.GEMINI_API_KEY and not settings.VERTEX_PROJECT:
        print("[SEO & Prompts Audit] No Gemini key/Vertex project set. Falling back to local rules analysis.")
        results = analyze_seo_geo("", data)
    else:
        try:
            print("[SEO & Prompts Audit] Calling Gemini for analysis...")
            medicine_name = data.get("medicine_name", "")
            dosage_form = data.get("dosage_form", "")
            route = determine_route(medicine_name, dosage_form)
            generic_clean = clean_generic_name(data.get("generic_name", ""))
            benchmark_brands = get_benchmark_brands(generic_clean, route)
            
            prompt = (
                f"Analyze the following medical product page content to determine SEO and GEO (Generative Engine Optimization) coverage.\n\n"
                f"SKU: {medicine_name}\n"
                f"Generic/Salt: {generic_clean}\n"
                f"Route of Administration: {route}\n"
                f"Top Competitor Brands: {', '.join(benchmark_brands)}\n\n"
                f"CRITICAL RULES:\n"
                f"1. DO NOT evaluate or score generic HTML elements like meta description, title tags, or H1 structures.\n"
                f"2. Evaluate brand/keyword coverage: Check if the content references top competitor brands for comparison or contains key clinical keywords.\n"
                f"3. Evaluate layman-friendly, Indian-user-focused prompts that are highly relevant to this drug and route (e.g. food interactions, duration, speed of action, safety in specific conditions like viral fever).\n"
                f"4. DO NOT suggest general prompts like 'can I get it without prescription' or 'what is the composition'. Only identify value-add points.\n"
                f"5. Store a final seo_score and geo_score between 0 and 100.\n\n"
                f"Page Content:\n{raw_text}\n\n"
                f"Response format MUST be a valid JSON dictionary containing keys:\n"
                f"- 'seo_score' (integer 0-100)\n"
                f"- 'geo_score' (integer 0-100)\n"
                f"- 'missing_keywords' (list of strings representing specific missing brands or clinical terms)\n"
                f"- 'missing_prompts' (list of strings representing value-add layman queries that are not addressed in the text)\n"
                f"- 'suggestions' (list of strings for improvements)"
            )
            
            from backend.app.services.llm_client import call_gemini
            text_out = call_gemini("gemini-2.5-flash", prompt)
            results = json.loads(text_out)
        except Exception as err:
            print(f"[SEO & Prompts Audit] Gemini API failed: {str(err)}. Using fallback.")
            results = analyze_seo_geo("", data)
            
    # 3. Save results to Database
    avg_score = (float(results.get("seo_score", 0.0)) + float(results.get("geo_score", 0.0))) / 2.0
    merged_score = max(0.0, min(100.0, avg_score))
    
    audit_record.seo_score = merged_score
    audit_record.geo_score = merged_score
    
    results["seo_score"] = merged_score
    results["geo_score"] = merged_score
    
    # Save the detailed SEO/GEO JSON report
    slug_dir = os.path.dirname(json_absolute_path)
    report_file = os.path.join(slug_dir, "seo_geo_report.json")
    with open(report_file, "w", encoding="utf-8") as rf:
        json.dump(results, rf, indent=2, ensure_ascii=False)
        
    audit_record.seo_geo_report_path = str(Path(report_file).relative_to(settings.DATA_DIR))
    db.commit()
    print(f"[SEO & Prompts Audit] Complete. SEO/GEO: {audit_record.seo_score}")
