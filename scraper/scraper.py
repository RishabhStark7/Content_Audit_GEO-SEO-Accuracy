import os
import re
import json
import argparse
import datetime
import uuid
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
try:
    from scraper.extractors import parse_html_to_json
except ModuleNotFoundError:
    from extractors import parse_html_to_json

# Default storage directory
ARCHIVE_DIR = Path("E:/Content-Governance/data/archive")

def slugify(value: str) -> str:
    """ Convert URL or string to a filesystem-friendly name """
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-')

def get_medicine_slug_from_url(url: str) -> str:
    """ Extracts the last segment of the 1mg URL as a slug """
    parts = url.rstrip('/').split('/')
    if parts:
        last = parts[-1]
        # Remove any query parameters
        last = last.split('?')[0]
        return last
    return "medicine-" + str(uuid.uuid4())[:8]

def expand_sections(page) -> None:
    """ Automatically expand all 'Read More', 'Show More', and FAQ accordion sections """
    print("[Scraper] Expanding all dynamic sections...")
    
    # 1. Expand "Read More" / "Show More" buttons
    # We look for buttons/links containing 'read more', 'show more', 'expand'
    read_more_selectors = [
        "text=/read more/i",
        "text=/show more/i",
        "text=/expand/i",
        "[class*='read-more']",
        "[class*='show-more']",
        "[class*='ReadMore']",
        "[class*='ShowMore']"
    ]
    
    for selector in read_more_selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()
            for i in range(count):
                elem = elements.nth(i)
                if elem.is_visible() and elem.is_enabled():
                    # Check if already expanded or if it's actually clickable
                    elem.click(timeout=1000)
                    page.wait_for_timeout(200)
        except Exception as e:
            # Ignore failures to click specific items
            pass

    # 2. Expand FAQ accordion sections
    # Frequently, FAQ questions can be clicked to toggle answers
    faq_selectors = [
        "[class*='Faq__question']",
        "[class*='faq-item']",
        "[class*='Faq'] [class*='question']"
    ]
    
    for selector in faq_selectors:
        try:
            elements = page.locator(selector)
            count = elements.count()
            for i in range(count):
                elem = elements.nth(i)
                if elem.is_visible() and elem.is_enabled():
                    # Attempt click to expand
                    elem.click(timeout=1000)
                    page.wait_for_timeout(200)
        except Exception as e:
            pass
            
    # Wait a moment for any final dynamic transitions
    page.wait_for_timeout(1000)
    print(f"[Scraper] URL after expanding sections: {page.url}")

def scrape_medicine(url: str, version_id: str = None) -> dict:
    """ Scrape a medicine page, capture all artifacts, and return parsed data """
    if not version_id:
        version_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        
    slug = get_medicine_slug_from_url(url)
    output_dir = ARCHIVE_DIR / version_id / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[Scraper] Starting scrape for URL: {url}")
    print(f"[Scraper] Target directory: {output_dir}")
    
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    with sync_playwright() as p:
        # Launch browser in headless mode to support PDF generation
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--no-sandbox"]
        )
        
        # Emulate a desktop viewport
        context = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            # Open webpage with generous timeout
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Wait for network idle or extra seconds to let Javascript run
            page.wait_for_timeout(3000)
            
            # Scroll down slowly to trigger lazy loading of below-the-fold content
            print("[Scraper] Scrolling down to trigger lazy-loaded sections...")
            for i in range(12):
                page.evaluate("window.scrollBy(0, 800)")
                page.wait_for_timeout(300)
                
            # Scroll back to the top so PDF/screenshot captures are clean from start of page
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            
            # Expand dynamic sections
            expand_sections(page)
            
            # 1. Capture HTML
            html_content = page.content()
            html_path = output_dir / "page.html"
            html_path.write_text(html_content, encoding="utf-8")
            
            # 2. Capture full-page screenshot
            screenshot_path = output_dir / "screenshot.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            
            # 3. Generate PDF snapshot
            pdf_path = output_dir / "page.pdf"
            page.pdf(path=str(pdf_path), format="A4", print_background=True)
            
            # 4. Extract structured content
            structured_data = parse_html_to_json(html_content)
            
            # Add version and audit trail to JSON
            structured_data["version_id"] = version_id
            structured_data["audit_timestamp"] = timestamp
            structured_data["source_url"] = url
            
            json_path = output_dir / "structured.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
                
            # Create a summary meta.json file
            meta = {
                "url": url,
                "slug": slug,
                "version_id": version_id,
                "timestamp": timestamp,
                "medicine_name": structured_data["medicine_name"],
                "generic_name": structured_data["generic_name"],
                "html_path": str(html_path.relative_to(ARCHIVE_DIR.parent)),
                "pdf_path": str(pdf_path.relative_to(ARCHIVE_DIR.parent)),
                "screenshot_path": str(screenshot_path.relative_to(ARCHIVE_DIR.parent)),
                "json_path": str(json_path.relative_to(ARCHIVE_DIR.parent))
            }
            meta_path = output_dir / "meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
                
            print(f"[Scraper] Scraping completed successfully for {url}")
            return meta
            
        except Exception as e:
            print(f"[Scraper] Error scraping {url}: {str(e)}")
            # Write error log
            error_path = output_dir / "error.txt"
            error_path.write_text(f"Timestamp: {timestamp}\nError: {str(e)}")
            raise e
        finally:
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Tata 1mg medicine page and extract medical governance data.")
    parser.add_argument("--url", type=str, required=True, help="The Tata 1mg medicine URL")
    parser.add_argument("--version-id", type=str, default=None, help="Optional version ID for archiving")
    args = parser.parse_args()
    
    try:
        result = scrape_medicine(args.url, args.version_id)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Failed to scrape: {e}")
        exit(1)
