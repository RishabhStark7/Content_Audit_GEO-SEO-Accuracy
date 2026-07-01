import re
import json
import os
from bs4 import BeautifulSoup  # type: ignore  # pyrefly: ignore
from typing import Dict, List, Any

# Benchmark Dictionary of top 5 brands for key generic drug + route combinations in India
BENCHMARK_BRANDS = {
    ("paracetamol", "oral"): ["Calpol", "Dolo 650", "Crocin", "Pacimol", "Sumo L"],
    ("paracetamol", "injection"): ["Perfalgan", "Neomol", "Febrinil", "Kabimol", "Paracip IV"],
    ("paracetamol", "topical"): ["Thermacare", "Dynapar Gel", "Volini"],
    ("amoxicillin", "oral"): ["Mox", "Novamox", "Almox", "Moxikind", "Amoxycillin-Kid"],
    ("amoxicillin", "injection"): ["Clavam Injection", "Augmentin Injection", "Moxclav Injection", "Amoxyclav Injection", "Novamox Injection"],
    ("ibuprofen", "oral"): ["Brufen", "Ibugesic", "Combiflam", "Ibucon", "Anaflam"],
    ("pantoprazole", "oral"): ["Pan", "Pantocid", "Pantodac", "Pantosec", "Nupenta"],
    ("pantoprazole", "injection"): ["Pan IV", "Pantocid IV", "Pantodac IV", "Pantocork IV", "Pentalink IV"],
    ("atorvastatin", "oral"): ["Atorva", "Lipvas", "Tonact", "Storvas", "Lipicure"]
}

STANDARD_KEYWORDS = [
    "side effects", "precautions", "dosage", "when to take", "how it works",
    "pregnancy safety", "alcohol interactions", "kidney precautions", "liver precautions",
    "driving safety", "composition", "alternative brands", "benefits"
]

def clean_generic_name(generic_name: str) -> str:
    """ Clean generic name to its base form (e.g. 'Paracetamol (650mg)' -> 'paracetamol') """
    if not generic_name:
        return "unknown"
    # Take first word or up to parenthesis/plus/comma
    name = generic_name.split('(')[0].split('+')[0].split(',')[0].strip()
    return name.lower()

def determine_route(dosage_form: str) -> str:
    """ Determine the administration route from the dosage form """
    if not dosage_form:
        return "oral"
    form_lower = dosage_form.lower()
    if any(i in form_lower for i in ["eye", "ophthalmic", "ear"]):
        return "ophthalmic"
    elif "nasal" in form_lower:
        return "nasal"
    elif any(i in form_lower for i in ["injection", "infusion", "iv", "vial", "ampoule"]):
        return "injection"
    elif any(t in form_lower for t in ["gel", "cream", "ointment", "spray", "topical", "lotion"]):
        return "topical"
    elif any(s in form_lower for s in ["syrup", "suspension", "liquid", "drops"]):
        return "oral"
    else:
        return "oral"

def get_benchmark_brands(generic: str, route: str) -> List[str]:
    """ Retrieve top 5 brands for a given drug + route combination """
    key = (generic, route)
    if key in BENCHMARK_BRANDS:
        return BENCHMARK_BRANDS[key]
    
    # Dynamic fallback generator if not in dictionary
    title_case_generic = generic.capitalize()
    return [
        f"{title_case_generic} Cipla",
        f"{title_case_generic} Sun",
        f"{title_case_generic} Abbott",
        f"{title_case_generic} Lupin",
        f"{title_case_generic} Alkem"
    ]

def evaluate_content_seo_geo_score(html_content: str, structured_data: dict, route: str) -> tuple[float, list[str]]:
    """
    Computes a merged Content-Led SEO & GEO Score out of 100 points.
    Formula:
    - Technical SEO parameters: Max 20 points (headings structure, meta description)
    - Generative AI markup: Max 20 points (JSON-LD schema, lists/bullets layout)
    - Content-Led Keyword Density: Max 30 points (occurrence frequency of 13 standard keywords)
    - Route-Subjective Prompts Coverage: Max 30 points (evaluated out of relevant layman queries)
    """
    score = 0.0
    soup = BeautifulSoup(html_content, 'lxml')
    text_content = flatten_text(structured_data).lower()
    
    # 1. Technical SEO & Generative Parameters (Max 40 points)
    # Heading structure (Max 10 pts)
    h1s = soup.find_all('h1')
    if len(h1s) == 1:
        score += 10.0
    elif len(h1s) > 1:
        score += 5.0
        
    # Meta description (Max 10 pts)
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
    if meta_desc:
        content_val = meta_desc.get('content')
        if content_val and len(str(content_val)) > 50:
            score += 10.0
        else:
            score += 5.0
            
    # JSON-LD Schema markup (Max 10 pts)
    schemas = soup.find_all('script', type='application/ld+json')
    if any(any(ctx in s.get_text() for ctx in ['"FAQPage"', '"Drug"', '"BreadcrumbList"']) for s in schemas):
        score += 10.0
        
    # Readability list layouts (Max 10 pts)
    if structured_data.get('quick_tips') or structured_data.get('side_effects'):
        score += 10.0

    # 2. Content-Led Keyword Density (Max 30 points)
    distinct_kws = 0
    total_freq = 0
    for kw in STANDARD_KEYWORDS:
        freq = len(re.findall(r'\b' + re.escape(kw) + r'\b', text_content))
        if freq > 0:
            distinct_kws += 1
            total_freq += freq
            
    if distinct_kws >= 8:
        score += 20.0
    elif distinct_kws >= 4:
        score += 10.0
        
    if total_freq >= 15:
        score += 10.0
    elif total_freq >= 8:
        score += 5.0

    # 3. Route-Subjective layman query prompts (Max 30 points)
    generic_clean = clean_generic_name(structured_data.get("generic_name", ""))
    title_case_drug = generic_clean.capitalize()
    
    if route == "injection":
        prompts = [
            f"What is the correct dose of {title_case_drug} {route}?",
            f"What are the common side effects of {title_case_drug}?",
            f"Are there any serious drug interactions with {title_case_drug}?",
            f"Is {title_case_drug} safe during pregnancy?",
            f"What are the cheap alternative brand substitutes for {title_case_drug}?",
            f"How exactly does {title_case_drug} work to cure my symptoms?"
        ]
        match_keys = [
            ["dosage", "dose", "correct dose", "amount", "administer"],
            ["side effect", "adverse", "vomit", "nausea", "pain", "swelling"],
            ["interaction", "drug interaction", "contraindication", "avoid"],
            ["pregnancy", "pregnant", "breastfeed", "lactat", "womb"],
            ["alternative", "substitute", "brand substitute", "similar brand", "cheap"],
            ["mechanism", "works", "mechanism of action", "symptoms", "cures", "how exactly"]
        ]
    elif route == "topical":
        prompts = [
            f"What is the correct application of {title_case_drug} {route}?",
            f"Is {title_case_drug} safe to apply on the skin?",
            f"What are the common local side effects of {title_case_drug}?",
            f"What are the cheap alternative brand substitutes for {title_case_drug}?",
            f"How exactly does {title_case_drug} work to cure my symptoms?"
        ]
        match_keys = [
            ["dosage", "apply", "application", "thin layer", "amount"],
            ["skin", "face", "apply", "cream", "gel", "ointment", "external"],
            ["side effect", "adverse", "irritation", "burning", "redness", "itching"],
            ["alternative", "substitute", "brand substitute", "similar brand", "cheap"],
            ["mechanism", "works", "mechanism of action", "symptoms", "cures", "how exactly"]
        ]
    elif route == "ophthalmic":
        prompts = [
            f"What is the correct dose / drop count of {title_case_drug} {route}?",
            f"Is {title_case_drug} safe to use with contact lenses?",
            f"What are the common eye side effects of {title_case_drug}?",
            f"What are the cheap alternative brand substitutes for {title_case_drug}?",
            f"How exactly does {title_case_drug} work to cure my symptoms?"
        ]
        match_keys = [
            ["drops", "instill", "correct dose", "amount"],
            ["contact lenses", "contacts", "lens", "glasses"],
            ["side effect", "adverse", "stinging", "burning", "blurred vision", "irritation"],
            ["alternative", "substitute", "brand substitute", "similar brand", "cheap"],
            ["mechanism", "works", "mechanism of action", "symptoms", "cures", "how exactly"]
        ]
    elif route == "nasal":
        prompts = [
            f"What is the correct sprays count of {title_case_drug} {route}?",
            f"Is {title_case_drug} safe for long term nasal use?",
            f"What are the common nasal side effects of {title_case_drug}?",
            f"What are the cheap alternative brand substitutes for {title_case_drug}?",
            f"How exactly does {title_case_drug} work to cure my symptoms?"
        ]
        match_keys = [
            ["sprays", "nostril", "instill", "dose", "amount"],
            ["long term", "rebound", "congestion", "addiction", "habit"],
            ["side effect", "adverse", "dryness", "nosebleed", "sneezing", "irritation"],
            ["alternative", "substitute", "brand substitute", "similar brand", "cheap"],
            ["mechanism", "works", "mechanism of action", "symptoms", "cures", "how exactly"]
        ]
    else:  # default oral
        prompts = [
            f"What is the correct dose of {title_case_drug} {route}?",
            f"How many times a day should I take {title_case_drug}?",
            f"Is {title_case_drug} safe during pregnancy?",
            f"What are the common side effects of {title_case_drug}?",
            f"Can I drink alcohol after taking {title_case_drug}?",
            f"Are there any serious drug interactions with {title_case_drug}?",
            f"What happens if I take a double dose of {title_case_drug}?",
            f"Can I buy {title_case_drug} without a prescription in India?",
            f"What are the cheap alternative brand substitutes for {title_case_drug}?",
            f"How exactly does {title_case_drug} work to cure my symptoms?"
        ]
        match_keys = [
            ["dosage", "dose", "correct dose", "amount"],
            ["times a day", "daily", "frequency", "how often", "schedule"],
            ["pregnancy", "pregnant", "breastfeed", "lactat", "womb"],
            ["side effect", "adverse", "vomit", "nausea", "headache", "rash"],
            ["alcohol", "liquor", "drink", "beer", "wine"],
            ["interaction", "drug interaction", "contraindication", "avoid"],
            ["overdose", "toxicity", "excessive", "double dose", "accidental"],
            ["prescription", "rx", "otc", "without a prescription", "over the counter"],
            ["alternative", "substitute", "brand substitute", "similar brand", "cheap"],
            ["mechanism", "works", "mechanism of action", "symptoms", "cures", "how exactly"]
        ]
        
    covered_count = 0
    missing_prompts = []
    for pr, keys in zip(prompts, match_keys):
        if any(k in text_content for k in keys):
            covered_count += 1
        else:
            missing_prompts.append(pr)
            
    coverage_score = (covered_count / len(prompts)) * 30.0
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
    """ Performs complete SEO/GEO gap analysis """
    generic_raw = structured_data.get("generic_name", "")
    generic_clean = clean_generic_name(generic_raw)
    route = determine_route(structured_data.get("dosage_form", ""))
    
    benchmark_brands = get_benchmark_brands(generic_clean, route)
    text_content = flatten_text(structured_data).lower()
    
    # 1. Identify missing keywords
    missing_keywords = []
    target_keywords = STANDARD_KEYWORDS + [b.lower() for b in benchmark_brands]
    for kw in target_keywords:
        if kw not in text_content:
            missing_keywords.append(kw)
    missing_keywords = missing_keywords[:10]
    
    # 2. Evaluate merged SEO-GEO score and identify missing prompts
    score, missing_prompts = evaluate_content_seo_geo_score(html_content, structured_data, route)
    
    return {
        "generic_drug": generic_clean,
        "route_of_administration": route,
        "benchmark_brands": benchmark_brands,
        "seo_score": score,
        "geo_score": score,
        "missing_keywords": missing_keywords,
        "missing_prompts": missing_prompts
    }

from sqlalchemy.orm import Session  # type: ignore  # pyrefly: ignore
from backend.app.models.models import AuditRecord
from pathlib import Path
from backend.app.core.config import settings

def run_seo_geo_ai_audit(db: Session, audit_record: AuditRecord):
    """
    Module 5: AI-based SEO & Prompts Audit.
    Performs generative optimization analysis and prompt coverage checks,
    updating the scores in the database.
    """
    print(f"[SEO & Prompts Audit] Triggered for audit: {audit_record.id}")
    
    # 1. Load HTML and JSON content
    json_absolute_path = os.path.join(settings.DATA_DIR, audit_record.json_path)
    html_absolute_path = os.path.join(settings.DATA_DIR, audit_record.html_path)
    
    if not os.path.exists(json_absolute_path) or not os.path.exists(html_absolute_path):
        print(f"[SEO & Prompts Audit] Error: Files not found for audit {audit_record.id}")
        return
        
    with open(json_absolute_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    with open(html_absolute_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # 2. Token Governance: Truncate content to avoid token overflow
    raw_text = flatten_text(data)
    max_char_limit = 8000
    if len(raw_text) > max_char_limit:
        print(f"[Token Governance] WARNING: Input text is {len(raw_text)} chars. Truncating to {max_char_limit} chars to conserve tokens.")
        raw_text = raw_text[:max_char_limit]
        
    # 3. Call AI or run local heuristic fallback
    if not settings.GEMINI_API_KEY and not settings.VERTEX_PROJECT:
        print("[SEO & Prompts Audit] No Gemini key set. Falling back to local rules analysis.")
        results = analyze_seo_geo(html_content, data)
    else:
        try:
            print("[SEO & Prompts Audit] Calling Gemini 2.5 Pro for analysis...")
            prompt = (
                f"Analyze the following medical product page content to determine SEO and Generative Engine Optimization (GEO) coverage.\n"
                f"Identify missing keywords that are highly relevant to the Indian userbase (e.g. safety warnings, pregnancy safety, side effects, cheap alternatives, precautions, composition).\n"
                f"Identify missing search engine query prompts that are layman-friendly and highly realistic for what an end user in India would search (e.g. 'Can I drink alcohol?', 'Is it safe during pregnancy?', 'cheap alternatives', 'correct dose'). Avoid technical jargon or queries about manufacturers.\n"
                f"Make sure to keep the calculated scores bounded: seo_score and geo_score MUST be integers between 0 and 100.\n\n"
                f"Page Content:\n{raw_text}\n\n"
                f"Response format MUST be a valid JSON dictionary containing keys:\n"
                f"- 'seo_score' (integer 0-100)\n"
                f"- 'geo_score' (integer 0-100)\n"
                f"- 'missing_keywords' (list of strings)\n"
                f"- 'missing_prompts' (list of strings)\n"
                f"- 'suggestions' (list of strings)"
            )
            
            from backend.app.services.llm_client import call_gemini
            text_out = call_gemini("gemini-2.5-flash", prompt)
            results = json.loads(text_out)
        except Exception as err:
            print(f"[SEO & Prompts Audit] Gemini API failed: {str(err)}. Using fallback.")
            results = analyze_seo_geo(html_content, data)
            
    # 4. Save results to Database (Merge SEO and GEO scores)
    avg_score = (float(results.get("seo_score", 0.0)) + float(results.get("geo_score", 0.0))) / 2.0
    merged_score = max(0.0, min(100.0, avg_score))
    
    audit_record.seo_score = merged_score
    audit_record.geo_score = merged_score
    
    # Store merged score back to results so that report file contains it too
    results["seo_score"] = merged_score
    results["geo_score"] = merged_score
    
    # Save the detailed SEO/GEO JSON report
    slug_dir = os.path.dirname(json_absolute_path)
    report_file = os.path.join(slug_dir, "seo_geo_report.json")
    with open(report_file, "w", encoding="utf-8") as rf:
        json.dump(results, rf, indent=2, ensure_ascii=False)
        
    audit_record.seo_geo_report_path = str(Path(report_file).relative_to(settings.DATA_DIR))
    db.commit()
    print(f"[SEO & Prompts Audit] Complete. SEO: {audit_record.seo_score}, GEO: {audit_record.geo_score}")
