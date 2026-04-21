import pytest
from unittest.mock import patch
from Application.Ports.scraper import scrape_relevant_syllabi

class DummyResult:
    def __init__(self, href, title):
        self.href = href
        self.title = title

def test_cleaner_raw_text():
    from Application.Infrastructure.ETL.cleaner import clean_raw_text
    
    raw = '''junk line
    Copyright 2024
        
    Module 1: Introduction
        
    Normal content line
    Short
    VERYLONGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG line outlier
        
    Duplicate
    Duplicate
    Duplicate
    http://link.com
    12345'''
    
    cleaned, stats = clean_raw_text(raw)
    assert 'Module 1: Introduction' in cleaned
    assert stats['removed_junk'] >= 1
    assert stats['removed_short'] >= 1
    assert stats['removed_long'] >= 1
    assert stats['removed_duplicate'] >= 1
    assert stats['lines_kept'] > 0

def test_cleaner_syllabus_dict():
    from Application.Infrastructure.ETL.cleaner import clean_syllabus_dict
    
    dirty = {
        'main_topics': ['short', 'Topic 1', 'Topic 1', 'Very long outlier topic.....................................................', '', 'Topic 2']
    }
    
    cleaned, stats = clean_syllabus_dict(dirty)
    topics = cleaned['main_topics']
    assert len(topics) < len(dirty['main_topics'])
    assert 'Topic 1' in topics
    assert 'Topic 2' in topics
    assert stats['total_items'] == 6
    assert stats['items_kept'] >= 2

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
    monkeypatch.setattr('Application.Ports.scraper.scrape_web_syllabus', lambda url: 'module1\\nmodule2\\n junk \\n duplicate\\n duplicate')
    monkeypatch.setattr('Application.Ports.scraper.scrape_pdf_syllabus', lambda url: 'pdfmodule')

    result = scrape_relevant_syllabi('Test Course', max_results=3)

    assert isinstance(result, list)
    assert len(result) == 3
    assert all('source_url' in entry for entry in result)
    for entry in result:
        if '_cleaning_stats' in entry:
            raw_stats = entry['_cleaning_stats']['raw']
            assert raw_stats['lines_kept'] > 0
            assert raw_stats['removed_duplicate'] > 0
    assert any(entry['source_url'].endswith('.pdf') for entry in result)
