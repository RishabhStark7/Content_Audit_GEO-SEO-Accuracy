import re
import json
import os
from bs4 import BeautifulSoup
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

# Standard Indian Pharma demography keywords to look for
STANDARD_KEYWORDS = [
    "dosage", "side effects", "precautions", "marketer", "manufacturer", 
    "composition", "uses", "benefits", "contraindications", "overdose", 
    "pregnancy", "breastfeeding", "alcohol warning", "driving caution", 
    "kidney disease", "liver disease", "chemical class", "habit forming", 
    "action class", "drug interactions"
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
    if any(i in form_lower for i in ["injection", "infusion", "iv", "vial", "ampoule"]):
        return "injection"
    elif any(t in form_lower for t in ["gel", "cream", "ointment", "spray", "topical", "lotion"]):
        return "topical"
    elif any(s in form_lower for s in ["syrup", "suspension", "liquid", "drops"]):
        return "oral" # oral liquid
    else:
        return "oral" # default to oral tablets/capsules

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

def evaluate_seo_score(html_content: str, structured_data: dict) -> int:
    """ Compute SEO score (0-100) """
    score = 0
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 1. Heading structure (Max 20 pts)
    h1s = soup.find_all('h1')
    if len(h1s) == 1:
        score += 20
    elif len(h1s) > 1:
        score += 10 # Deduct if multiple H1s
        
    # 2. Image Alt-tags (Max 20 pts)
    imgs = soup.find_all('img')
    if imgs:
        imgs_with_alt = sum(1 for img in imgs if img.get('alt'))
        alt_ratio = imgs_with_alt / len(imgs)
        score += int(alt_ratio * 20)
    else:
        score += 20 # Perfect score if no images are present to optimize
        
    # 3. Title tag length (Max 20 pts)
    title = soup.find('title')
    if title:
        title_len = len(title.get_text(strip=True))
        if 40 <= title_len <= 70:
            score += 20
        elif 25 <= title_len <= 90:
            score += 10
            
    # 4. Meta description presence (Max 20 pts)
    meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
    if meta_desc:
        content_val = meta_desc.get('content')
        if content_val:
            desc_len = len(str(content_val))
            if desc_len > 100:
                score += 20
            else:
                score += 10
            
    # 5. Content Volume / Word Count (Max 20 pts)
    # Estimate total words in main paragraphs
    body = soup.find('body')
    if body:
        # Decompose non-content first
        clean_soup = BeautifulSoup(html_content, 'lxml')
        for t in clean_soup(["script", "style", "meta", "link", "noscript"]):
            t.decompose()
        words = len(re.findall(r'\b\w+\b', clean_soup.get_text()))
        if words > 800:
            score += 20
        elif words > 400:
            score += 10
            
    return score

def evaluate_geo_score(html_content: str, structured_data: dict, missing_prompts_count: int) -> int:
    """ Compute GEO (Generative Engine Optimization) score (0-100) """
    score = 0
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 1. Schema markup presence (Max 30 pts)
    # Search for ld+json scripts containing common schema contexts
    schemas = soup.find_all('script', type='application/ld+json')
    schema_found = False
    for s in schemas:
        try:
            content = s.get_text()
            if '"FAQPage"' in content or '"Drug"' in content or '"BreadcrumbList"' in content:
                score += 10
                schema_found = True
        except:
            pass
    if schema_found:
        score += 10 # Base points for schema presence
        
    # 2. Q&A / FAQ Structured layout (Max 20 pts)
    if structured_data.get('faqs'):
        score += 20
        
    # 3. Readability & Bullets (Max 20 pts)
    if structured_data.get('quick_tips') or structured_data.get('side_effects'):
        score += 20
        
    # 4. Prompt Coverage (Max 30 pts)
    # If 0 prompts are missing out of 10 -> 30 pts. Each missing prompt deducts 3 pts.
    covered_prompts = max(0, 10 - missing_prompts_count)
    score += (covered_prompts * 3)
    
    return score

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
    
    # Compile entire scraped page text to search for keywords
    text_content = flatten_text(structured_data)
            
    text_content_lower = text_content.lower()
    
    # 1. Identify missing keywords
    missing_keywords = []
    # Mix standard keywords with benchmark brand names
    target_keywords = STANDARD_KEYWORDS + [b.lower() for b in benchmark_brands]
    for kw in target_keywords:
        if kw not in text_content_lower:
            missing_keywords.append(kw)
            
    # Cap missing keywords to top 10
    missing_keywords = missing_keywords[:10]
    
    # 2. Identify missing user query prompts
    # Standard 10 prompts related to a drug + route
    title_case_drug = generic_clean.capitalize()
    standard_prompts = [
        f"What is the recommended dosage of {title_case_drug} {route}?",
        f"How quickly does {title_case_drug} {route} work compared to oral tablets?",
        f"Is {title_case_drug} {route} safe to use during pregnancy and breastfeeding?",
        f"What are the major side effects associated with {title_case_drug} {route}?",
        f"Can {title_case_drug} {route} be consumed along with alcohol?",
        f"What are the critical drug interactions to avoid when taking {title_case_drug}?",
        f"What should I do in case of an accidental overdose of {title_case_drug}?",
        f"Does {title_case_drug} {route} require a doctor's prescription?",
        f"Who is the leading manufacturer/marketer of {title_case_drug} {route} in India?",
        f"How does {title_case_drug} {route} work inside the body (mechanism of action)?"
    ]
    
    # Check coverage of prompts by scanning text for semantic matches
    missing_prompts = []
    prompt_match_keys = [
        ["dosage", "dose", "administer"],
        ["how quickly", "how fast", "onset", "working", "effect"],
        ["pregnancy", "pregnant", "breastfeed", "lactat"],
        ["side effect", "adverse", "vomit", "nausea"],
        ["alcohol", "liquor", "drink"],
        ["interaction", "drug interaction", "contraindication"],
        ["overdose", "toxicity", "excessive"],
        ["prescription", "rx", "otc"],
        ["marketer", "manufacturer", "brand", "company"],
        ["mechanism", "works", "mechanism of action", "analgesic"]
    ]
    
    for prompt, keys in zip(standard_prompts, prompt_match_keys):
        # If none of the keys are found, prompt is missing
        if not any(k in text_content_lower for k in keys):
            missing_prompts.append(prompt)
            
    missing_prompts = missing_prompts[:10]
    
    # Evaluate SEO/GEO scores
    seo_score = evaluate_seo_score(html_content, structured_data)
    geo_score = evaluate_geo_score(html_content, structured_data, len(missing_prompts))
    
    return {
        "generic_drug": generic_clean,
        "route_of_administration": route,
        "benchmark_brands": benchmark_brands,
        "seo_score": seo_score,
        "geo_score": geo_score,
        "missing_keywords": missing_keywords,
        "missing_prompts": missing_prompts
    }

from sqlalchemy.orm import Session
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
                f"Identify missing keywords for India pharma demography (e.g. dosage, side effects, precautions, marketer, safety indicators).\n"
                f"Identify missing search engine query prompts for the drug + route combination.\n\n"
                f"Page Content:\n{raw_text}\n\n"
                f"Response format MUST be a valid JSON dictionary containing keys:\n"
                f"- 'seo_score' (integer 0-100)\n"
                f"- 'geo_score' (integer 0-100)\n"
                f"- 'missing_keywords' (list of strings)\n"
                f"- 'missing_prompts' (list of strings)\n"
                f"- 'suggestions' (list of strings)"
            )
            
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            resp = httpx.post(url, json=payload, timeout=30.0)
            if resp.status_code == 200:
                response_json = resp.json()
                text_out = response_json["candidates"][0]["content"]["parts"][0]["text"]
                results = json.loads(text_out)
            else:
                print(f"[SEO & Prompts Audit] Gemini API failed with status {resp.status_code}. Using fallback.")
                results = analyze_seo_geo(html_content, data)
        except Exception as err:
            print(f"[SEO & Prompts Audit] Gemini API error: {str(err)}. Using fallback.")
            results = analyze_seo_geo(html_content, data)
            
    # 4. Save results to Database
    audit_record.seo_score = float(results.get("seo_score", 0.0))
    audit_record.geo_score = float(results.get("geo_score", 0.0))
    
    # Save the detailed SEO/GEO JSON report
    slug_dir = os.path.dirname(json_absolute_path)
    report_file = os.path.join(slug_dir, "seo_geo_report.json")
    with open(report_file, "w", encoding="utf-8") as rf:
        json.dump(results, rf, indent=2, ensure_ascii=False)
        
    audit_record.seo_geo_report_path = str(Path(report_file).relative_to(settings.DATA_DIR))
    db.commit()
    print(f"[SEO & Prompts Audit] Complete. SEO: {audit_record.seo_score}, GEO: {audit_record.geo_score}")
