from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def scrape_web_syllabus(url: str) -> str:
    if 'wikipedia.org' in url.lower():
        raise ValueError("Wikipedia is blocked - use technical sites like realpython, freecodecamp, docs")

    try:
        with sync_playwright() as p:
            # Launching headless browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Navigate and wait for network to be idle (ensures JS content is loaded)
            page.goto(url, wait_until="networkidle", timeout=30000)
            html_content = page.content()
            browser.close()
            
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        raise RuntimeError(f"Playwright scraping failed for {url}: {str(e)}")

    # Extract syllabus-relevant sections: headings + paragraphs + lists
    syllabus_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td'])
    lines = [tag.get_text(strip=True) for tag in syllabus_tags if tag.get_text(strip=True)]
    return "\n".join(lines)