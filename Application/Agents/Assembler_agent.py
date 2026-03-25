from typing import List, Dict
from docx import Document

class AssemblerAgent:
    @staticmethod
    def export_to_docx(chapters: List[Dict[str, str]], filename: str):
        doc = Document()
        doc.add_heading("Course Syllabus", level=1)
        for chapter in chapters:
            doc.add_heading(chapter["title"], level=2)
            doc.add_paragraph(chapter["content"])
        doc.save(filename)