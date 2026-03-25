import requests
from bs4 import BeautifulSoup

def scrape_web_syllabus(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.find("div", class_="syllabus-content").get_text()