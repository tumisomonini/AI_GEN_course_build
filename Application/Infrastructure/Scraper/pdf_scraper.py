from pypdf import PdfReader

def scrape_pdf_syllabus(file_path: str) -> str:
    with open(file_path, "rb") as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text