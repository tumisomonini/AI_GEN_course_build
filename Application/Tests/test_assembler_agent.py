import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from Application.Agents.Assembler_agent import AssemblerAgent
from datetime import datetime

def test_assembler_markdown():
    assembler = AssemblerAgent()
    chapters = [{'title': 'Ch1', 'content': 'Content1'}, {'title': 'Ch2', 'content': 'Content2'}]
    md = assembler.export_to_markdown(chapters, 'Test Course')
    assert '# Test Course' in md
    assert '## Ch1' in md
    assert datetime.now().strftime('%Y-%m-%d') in md  # Date present
    assert len([line for line in md.split('\n') if line.strip()]) > 5

def test_assembler_docx():
    assembler = AssemblerAgent()
    chapters = [{'title': 'Ch1', 'content': 'Content1'}]
    test_filename = 'test_course_output.docx'
    if os.path.exists(test_filename):
        os.remove(test_filename) # Ensure clean slate
    
    returned_filename = assembler.export_to_docx(chapters, test_filename)
    assert returned_filename == test_filename
    assert os.path.exists(test_filename)
    assert os.path.getsize(test_filename) > 0 # Check if file has content
    os.remove(test_filename) # Clean up generated file
