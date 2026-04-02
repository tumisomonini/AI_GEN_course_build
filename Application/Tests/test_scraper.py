import pytest
from unittest.mock import patch
from Application.Ports.scraper import scrape_relevant_syllabi

class DummyResult:
    def __init__(self, href, title):
        self.href = href
        self.title = title

def test_scrape_relevant_syllabi_parallel(monkeypatch):
    dummy_results = [
        {'href': 'https://example.com/syllabus1', 'title': 'syl1'},
        {'href': 'https://example.com/syllabus2', 'title': 'syl2'},
        {'href': 'https://example.com/syllabus3.pdf', 'title': 'syl3-pdf'},
    ]

    class FakeDDGS:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_value, traceback):
            return False
        def text(self, query, max_results):
            return dummy_results

    monkeypatch.setattr('Application.Ports.scraper.DDGS', FakeDDGS)
    monkeypatch.setattr('Application.Ports.scraper.scrape_web_syllabus', lambda url: 'module1\nmodule2')
    monkeypatch.setattr('Application.Ports.scraper.scrape_pdf_syllabus', lambda url: 'pdfmodule')

    result = scrape_relevant_syllabi('Test Course', max_results=3)

    assert isinstance(result, list)
    assert len(result) == 3
    assert all('source_url' in entry for entry in result)
    assert any(entry['source_url'].endswith('.pdf') for entry in result)
