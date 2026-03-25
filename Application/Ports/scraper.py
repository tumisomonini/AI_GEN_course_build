import requests
from bs4 import BeautifulSoup
import spacy
import re

nlp = spacy.load("en_core_web_sm")

def scrape_web_syllabus(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find("div", class_="syllabus-content").get_text()

def parse_syllabus(text: str) -> Dict[str, List[str]]:
    doc = nlp(text)
    sections = {}
    current_section = None
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if re.match(r"^\d+\.", sent_text):
            current_section = sent_text.split(".")[1].strip()
            sections[current_section] = []
        elif current_section:
            sections[current_section].append(sent_text)
    return sections