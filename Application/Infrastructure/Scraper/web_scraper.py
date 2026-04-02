import requests
from bs4 import BeautifulSoup

def scrape_web_syllabus(url: str) -> str:
    if 'wikipedia.org' in url.lower():
        raise ValueError("Wikipedia is blocked - use technical sites like realpython, freecodecamp, docs")

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract syllabus-relevant sections: headings + paragraphs + lists
    syllabus_tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td'])
    lines = [tag.get_text(strip=True) for tag in syllabus_tags if tag.get_text(strip=True)]
    return "\n".join(lines)