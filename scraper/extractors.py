import re
from bs4 import BeautifulSoup
from typing import Dict, List, Any

def extract_product_name(soup: BeautifulSoup) -> str:
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    title = soup.find('title')
    if title:
        return title.get_text(strip=True).split('-')[0].strip()
    return ""

def extract_generic_name(soup: BeautifulSoup) -> str:
    # Try exact match on 'Composition:' first
    elem = soup.find(string=re.compile(r'^Composition:$', re.I))
    if elem:
        sibling = elem.parent.find_next_sibling()
        if sibling:
            return sibling.get_text(strip=True)
            
    # Sibling search for 'Salt Composition'
    for elem in soup.find_all(string=re.compile(r'Salt Composition', re.I)):
        sibling = elem.parent.find_next_sibling()
        if sibling:
            return sibling.get_text(strip=True)
        # Search nested links
        links = elem.parent.find_next_siblings('a') or elem.parent.find_all('a')
        if links:
            return ", ".join([a.get_text(strip=True) for a in links])
            
    # Class fallback
    salt_elem = soup.select_one('[class*="SaltInfo__salt-orange"]') or soup.select_one('[class*="saltInfo"]')
    if salt_elem:
        return salt_elem.get_text(strip=True)
        
    return ""

def extract_dosage_form_and_strength(soup: BeautifulSoup, name: str) -> tuple[str, str]:
    dosage_form = ""
    strength = ""
    
    # Try finding strength (e.g. 650mg, 500 mg, 10ml, 5% w/w)
    strength_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|%|units|iu))', name, re.I)
    if strength_match:
        strength = strength_match.group(1)
    else:
        # Check salt composition text
        generic = extract_generic_name(soup)
        strength_match = re.search(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|%|units|iu))', generic, re.I)
        if strength_match:
            strength = strength_match.group(1)
        
    dosage_forms = ['tablet', 'capsule', 'syrup', 'injection', 'gel', 'cream', 'ointment', 'drops', 'inhaler', 'suspension', 'emulsion']
    for form in dosage_forms:
        if form in name.lower():
            dosage_form = form.capitalize()
            break
            
    if not dosage_form:
        for text in [name] + [elem.get_text() for elem in soup.find_all(['h2', 'div', 'span'])[:50]]:
            for form in dosage_forms:
                if re.search(r'\b' + form + r'\b', text.lower()):
                    dosage_form = form.capitalize()
                    break
            if dosage_form:
                break
                
    return dosage_form, strength

def extract_manufacturer(soup: BeautifulSoup) -> str:
    # Try exact match on 'Marketer details:' first
    elem = soup.find(string=re.compile(r'^Marketer details:$', re.I))
    if elem:
        sibling = elem.parent.find_next_sibling()
        if sibling:
            return sibling.get_text(strip=True)

    for text_val in ["Marketer", "Manufacturer", "Manufactured By"]:
        elem = soup.find(string=re.compile(text_val, re.I))
        if elem:
            parent = elem.parent
            text_str = parent.get_text(strip=True)
            if ":" in text_str:
                return text_str.split(":", 1)[1].strip()
            sib = parent.find_next_sibling()
            if sib:
                return sib.get_text(strip=True)
                
    marketer_elem = soup.select_one('[class*="DrugHeader__meta-value"]')
    if marketer_elem:
        return marketer_elem.get_text(strip=True)
    return ""

def extract_breadcrumbs(soup: BeautifulSoup) -> List[str]:
    breadcrumbs = []
    container = soup.select_one('[class*="Breadcrumbs__container"]') or soup.select_one('[class*="breadcrumbs"]')
    if container:
        links = container.find_all('a')
        for link in links:
            breadcrumbs.append(link.get_text(strip=True))
        active = container.find(class_=re.compile(r'active|current', re.I))
        if active:
            breadcrumbs.append(active.get_text(strip=True))
    else:
        for elem in soup.find_all(class_=re.compile(r'breadcrumb', re.I)):
            items = elem.find_all(['a', 'span', 'li'])
            for item in items:
                txt = item.get_text(strip=True)
                if txt and txt not in breadcrumbs and '/' not in txt and '>' not in txt:
                    breadcrumbs.append(txt)
    return [b for b in breadcrumbs if b]

def extract_image_urls(soup: BeautifulSoup) -> List[str]:
    images = []
    container = soup.select_one('[class*="ProductImage__container"]') or soup.select_one('[class*="image-container"]')
    if container:
        imgs = container.find_all('img')
        for img in imgs:
            src = img.get('src') or img.get('data-src')
            if src and src.startswith('http'):
                images.append(src)
                
    for img in soup.find_all('img'):
        alt = img.get('alt', '')
        src = img.get('src') or img.get('data-src')
        if src and src.startswith('http') and ('dolo' in alt.lower() or 'medicine' in src.lower() or 'drug' in src.lower() or 'products' in src.lower()):
            if src not in images:
                images.append(src)
                
    return list(set(images))

def extract_section_text(soup: BeautifulSoup, section_keywords: List[str]) -> str:
    for keyword in section_keywords:
        headings = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(re.escape(keyword), re.I))
        for heading in headings:
            content = []
            curr = heading.find_next()
            while curr:
                if curr.name in ['h1', 'h2', 'h3'] and curr.get_text(strip=True) != heading.get_text(strip=True):
                    break
                if curr.name in ['p', 'li', 'span'] or (curr.name == 'div' and not curr.find(['p', 'h1', 'h2', 'h3', 'li'])):
                    txt = curr.get_text(strip=True)
                    if txt and txt not in content and len(txt) > 3:
                        content.append(txt)
                curr = curr.find_next()
            if content:
                return "\n".join(content)
                
    for keyword in section_keywords:
        normalized = keyword.lower().replace(' ', '-')
        elem = soup.select_one(f'[id*="{normalized}"], [class*="{normalized}"]')
        if elem:
            return elem.get_text(strip=True)
            
    return ""

def extract_side_effects(soup: BeautifulSoup) -> List[str]:
    effects = []
    section_elem = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Side [Ee]ffects', re.I))
    if section_elem:
        list_elem = section_elem.find_next(['ul', 'ol'])
        if list_elem:
            for li in list_elem.find_all('li'):
                effects.append(li.get_text(strip=True))
                
    if not effects:
        text = extract_section_text(soup, ["Side Effects", "Common side effects"])
        if text:
            lines = [line.strip('•-* ') for line in text.split('\n') if line.strip()]
            effects = [l for l in lines if len(l) > 3]
            
    return effects

def extract_safety_advice(soup: BeautifulSoup) -> Dict[str, Dict[str, str]]:
    safety = {
        "alcohol": {"risk": "Unknown", "description": ""},
        "pregnancy": {"risk": "Unknown", "description": ""},
        "breastfeeding": {"risk": "Unknown", "description": ""},
        "driving": {"risk": "Unknown", "description": ""},
        "kidney": {"risk": "Unknown", "description": ""},
        "liver": {"risk": "Unknown", "description": ""},
    }
    
    for key in safety.keys():
        # Find h3 containing warning label (e.g. Alcohol)
        h3_elem = soup.find(lambda tag: tag.name == "h3" and re.search(r'\b' + re.escape(key) + r'\b', tag.get_text(), re.I))
        if h3_elem:
            # Walk up to get card container
            card = h3_elem.parent
            while card and not (card.name == 'div' and any('flexColumn' in c for c in card.get('class', []))):
                card = card.parent
                
            if card:
                # Find risk badge (UNSAFE, SAFE, CAUTION)
                risk_elem = card.find(class_=re.compile(r'Tag__tag|bodyMediumBold', re.I))
                if risk_elem:
                    safety[key]["risk"] = risk_elem.get_text(strip=True).upper()
                    
                desc_elements = []
                summary_elem = card.find(class_=re.compile(r'textSupporting', re.I))
                if summary_elem:
                    desc_elements.append(summary_elem.get_text(strip=True))
                    
                # Look for list item descriptions in grandparent block
                grandparent = card.parent
                if grandparent:
                    for li in grandparent.find_all('li'):
                        desc_elements.append(li.get_text(strip=True))
                        
                safety[key]["description"] = " ".join(desc_elements)
                
    return safety

def extract_quick_tips(soup: BeautifulSoup) -> List[str]:
    tips = []
    section_elem = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Quick [Tt]ips', re.I))
    if section_elem:
        list_elem = section_elem.find_next(['ul', 'ol'])
        if list_elem:
            for li in list_elem.find_all('li'):
                tips.append(li.get_text(strip=True))
                
    if not tips:
        text = extract_section_text(soup, ["Quick Tips"])
        if text:
            lines = [line.strip('•-* ') for line in text.split('\n') if line.strip()]
            tips = [l for l in lines if len(l) > 3]
            
    return tips

def extract_fact_box(soup: BeautifulSoup) -> Dict[str, str]:
    fact_box = {
        "chemical_class": "",
        "therapeutic_class": "",
        "habit_forming": "",
        "action_class": ""
    }
    
    # Search elements with fact item class
    items = soup.select('[class*="ListOfAttributes__factItem"]') or soup.select('[class*="factItem"]')
    for item in items:
        label_elem = item.select_one('[class*="factLabel"]')
        value_elem = item.select_one('[class*="factValue"]')
        if label_elem and value_elem:
            label = label_elem.get_text(strip=True).lower()
            val = value_elem.get_text(strip=True)
            if 'chemical class' in label:
                fact_box["chemical_class"] = val
            elif 'therapeutic class' in label:
                fact_box["therapeutic_class"] = val
            elif 'habit forming' in label:
                fact_box["habit_forming"] = val
            elif 'action class' in label:
                fact_box["action_class"] = val
                
    if not any(fact_box.values()):
        for label, key in [
            ("Chemical Class", "chemical_class"),
            ("Therapeutic Class", "therapeutic_class"),
            ("Habit Forming", "habit_forming"),
            ("Action Class", "action_class")
        ]:
            elem = soup.find(string=re.compile(r'\b' + re.escape(label) + r'\b', re.I))
            if elem:
                parent = elem.parent
                val_elem = parent.find_next(class_=re.compile(r'factValue|bodyMediumBold|value', re.I))
                if val_elem:
                    fact_box[key] = val_elem.get_text(strip=True)
                    
    return fact_box

def extract_drug_interactions(soup: BeautifulSoup) -> str:
    return extract_section_text(soup, ["Drug Interactions", "Interactions", "Interaction with", "Interaction", "Drug-Drug Interactions"])

def extract_substitutes(soup: BeautifulSoup) -> List[str]:
    substitutes = []
    heading = soup.find(['h2', 'h3', 'h4'], string=re.compile(r'substitutes', re.I))
    if heading:
        curr = heading.find_next()
        while curr:
            if curr.name in ['h1', 'h2'] and curr.get_text(strip=True) != heading.get_text(strip=True):
                break
            if curr.name == 'h3':
                txt = curr.get_text(strip=True)
                if txt and txt not in substitutes:
                    substitutes.append(txt)
            curr = curr.find_next()
    return substitutes

def extract_faqs(soup: BeautifulSoup) -> List[Dict[str, str]]:
    faqs = []
    accordions = soup.select('[class*="Faq__question"]') or soup.select('[class*="faq-item"]') or soup.find_all(class_=re.compile(r'faq|FAQ', re.I))
    
    for acc in accordions:
        question_elem = acc.find(['h3', 'h4', 'div', 'span'], class_=re.compile(r'question|q|title', re.I)) or acc
        answer_elem = acc.find_next(['p', 'div'], class_=re.compile(r'answer|a|content', re.I))
        
        q_text = question_elem.get_text(strip=True) if question_elem else ""
        a_text = answer_elem.get_text(strip=True) if answer_elem else ""
        
        if q_text and a_text and (q_text.endswith('?') or len(q_text) > 10) and len(a_text) > 10:
            if {"question": q_text, "answer": a_text} not in faqs:
                faqs.append({"question": q_text, "answer": a_text})
                
    if not faqs:
        for q_elem in soup.find_all(string=re.compile(r'\?$', re.M)):
            q_text = q_elem.strip()
            if len(q_text) > 15:
                next_elem = q_elem.parent.find_next(['p', 'div'])
                if next_elem:
                    a_text = next_elem.get_text(strip=True)
                    if len(a_text) > 20:
                        faqs.append({"question": q_text, "answer": a_text})
                        
    return faqs

def parse_html_to_json(html_content: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Decompose script, style, meta, link, noscript tags to prevent matching them in text searches
    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()
        
    product_name = extract_product_name(soup)
    generic_name = extract_generic_name(soup)
    dosage_form, strength = extract_dosage_form_and_strength(soup, product_name)
    
    safety_data = extract_safety_advice(soup)
    formatted_safety = {}
    for k, v in safety_data.items():
        risk = v.get("risk", "Unknown")
        desc = v.get("description", "")
        if desc:
            formatted_safety[k] = f"Risk Level: {risk}. {desc}"
        else:
            formatted_safety[k] = f"Risk Level: {risk}"
            
    fact_box = extract_fact_box(soup)
    faqs_data = extract_faqs(soup)
    
    # Dynamic FAQ fallbacks for Missed Dose, Overdose, and Dosage
    missed_dose_text = extract_section_text(soup, ["Missed Dose"])
    if not missed_dose_text:
        for faq in faqs_data:
            q = faq.get("question", "").lower()
            if "forget to take" in q or "forget a dose" in q or "missed dose" in q or "miss a dose" in q:
                missed_dose_text = faq.get("answer", "")
                break
                
    overdose_text = extract_section_text(soup, ["Overdose"])
    if not overdose_text:
        for faq in faqs_data:
            q = faq.get("question", "").lower()
            if "take too much" in q or "overdose" in q or "accidental overdose" in q:
                overdose_text = faq.get("answer", "")
                break
                
    dosage_text = extract_section_text(soup, ["Dosage"])
    if not dosage_text:
        for faq in faqs_data:
            q = faq.get("question", "").lower()
            if "how to take" in q or "how much" in q or "how many" in q or "dose of" in q:
                dosage_text = faq.get("answer", "")
                break
    
    structured_data = {
        "medicine_name": product_name,
        "generic_name": generic_name,
        "dosage_form": dosage_form,
        "strength": strength,
        "product_summary": extract_section_text(soup, ["Product Summary", "Summary"]),
        "product_introduction": extract_section_text(soup, ["Product Introduction", "Introduction"]),
        "uses": extract_section_text(soup, ["Uses of", "Uses", "What is it prescribed for?"]),
        "benefits": extract_section_text(soup, ["Benefits of", "Benefits", "Key Benefits"]),
        "side_effects": extract_side_effects(soup),
        "how_to_use": extract_section_text(soup, ["How to use", "How to Use", "Directions for Use"]),
        "how_it_works": extract_section_text(soup, ["works", "Mechanism of Action"]),
        "dosage": dosage_text,
        "overdose": overdose_text,
        "missed_dose": missed_dose_text,
        "substitutes": extract_substitutes(soup),
        "safety": formatted_safety,
        "quick_tips": extract_quick_tips(soup),
        "fact_box": fact_box,
        "drug_interactions": extract_drug_interactions(soup),
        "faqs": faqs_data,
        "metadata": {
            "manufacturer": extract_manufacturer(soup),
            "breadcrumbs": extract_breadcrumbs(soup),
            "image_urls": extract_image_urls(soup)
        }
    }
    
    return structured_data
