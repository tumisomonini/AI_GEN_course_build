import pytest
from unittest.mock import patch
from Application.Ports.scraper import scrape_relevant_syllabi, get_scraper
from Application.Infrastructure.Scraper.scraper_core import Scraper

class DummyResult:
    def __init__(self, href, title):
        self.href = href
        self.title = title

def test_scraper_initialization():
    """Verify that get_scraper() returns an initialized Scraper with expected attributes."""
    # Reset singleton to force fresh initialization
    import Application.Ports.scraper as scraper_module
    scraper_module._default_scraper = None

    scraper = get_scraper()
    assert isinstance(scraper, Scraper)
    assert scraper.headless is True
    assert isinstance(scraper.user_agent, str) and len(scraper.user_agent) > 0
    assert hasattr(scraper, 'session')
    assert hasattr(scraper, 'redis_client')
    assert scraper.timeout == 30

    # Calling get_scraper again should return the same singleton
    assert get_scraper() is scraper

    # Cleanup
    scraper.close()
    scraper_module._default_scraper = None

def test_cleaner_raw_text():
    from Application.Infrastructure.ETL.cleaner import clean_raw_text
    
    raw = '''junk line
    Copyright 2024
        
    Module 1: Introduction
        
    Normal content line.
    Shrt
    VERYLONGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG line outlier

    Duplicate
    Duplicate
    Duplicate
    http://link.com
    12345'''
    
    cleaned, stats = clean_raw_text(raw)
    assert 'Module 1: Introduction' in cleaned
    # Check that counts are tracked, but don't enforce specific junk vs short counts
    # as they depend on internal cleaner threshold logic
    total_removed = stats['removed_junk'] + stats['removed_short'] + stats['removed_long']
    assert total_removed > 0
    assert stats['lines_kept'] > 0

def test_cleaner_syllabus_dict():
    from Application.Infrastructure.ETL.cleaner import clean_syllabus_dict
    
    dirty = {
        'main_topics': ['Topic 1: Fundamentals of Python Programming', 'Topic 1: Fundamentals of Python Programming', 'Topic 2: Intermediate Data Structures in Python', '']
    }
    
    cleaned, stats = clean_syllabus_dict(dirty)
    topics = cleaned['main_topics']
    assert len(topics) == 2
    assert any('Topic 1' in t for t in topics)
    assert any('Topic 2' in t for t in topics)
    assert stats['total_items'] == 4
    assert stats['items_kept'] == 2

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

    monkeypatch.setattr('Application.Infrastructure.Scraper.scraper_core.Scraper.redis_client', None) # Bypass cache
    monkeypatch.setattr('Application.Infrastructure.Scraper.scraper_core.DDGS', FakeDDGS)
    monkeypatch.setattr('Application.Infrastructure.Scraper.scraper_core.Scraper.scrape_web', lambda self, url: 'module1\nmodule2\n junk \n duplicate\n duplicate')
    monkeypatch.setattr('Application.Infrastructure.Scraper.scraper_core.Scraper.scrape_pdf', lambda self, url: 'pdfmodule')

    result = scrape_relevant_syllabi('Parallel Scrape Test Course', max_results=3)

    assert isinstance(result, list)
    assert len(result) == 3
    assert all('source_url' in entry for entry in result)
    for entry in result:
        if '_cleaning_stats' in entry:
            raw_stats = entry['_cleaning_stats']['raw'] # Access the 'raw' key
            assert raw_stats['lines_kept'] > 0
            assert raw_stats['removed_duplicate'] >= 1 # Expect at least one duplicate removed
            assert raw_stats['removed_junk'] >= 1 # Expect at least one junk line removed
    assert any(entry['source_url'].endswith('.pdf') for entry in result)
