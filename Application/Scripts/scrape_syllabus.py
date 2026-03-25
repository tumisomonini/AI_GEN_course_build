from infrastructure.scraper.web_scraper import scrape_web_syllabus
from infrastructure.scraper.pdf_scraper import scrape_pdf_syllabus
from application.ports.scraper import parse_syllabus

def scrape_and_structure(url: str = None, file_path: str = None) -> Dict[str, List[str]]:
    if url:
        raw_syllabus = scrape_web_syllabus(url)
    elif file_path:
        raw_syllabus = scrape_pdf_syllabus(file_path)
    else:
        raise ValueError("Provide either a URL or file path.")
    return parse_syllabus(raw_syllabus)

if __name__ == "__main__":
    structured_syllabus = scrape_and_structure(url="https://example.edu/course-syllabus")
    print(structured_syllabus)