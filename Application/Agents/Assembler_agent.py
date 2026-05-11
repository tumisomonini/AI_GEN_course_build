from typing import List, Dict, Optional
from datetime import datetime

class AssemblerAgent:
    def __init__(self):
        pass

    def export_to_markdown(self, chapters: List[Dict[str, str]], title: str = "AI Generated Course") -> str:
        """Assemble chapters into a markdown string."""
        lines = [f"# {title}", f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]
        for chapter in chapters:
            lines.append(f"## {chapter['title']}")
            lines.append(chapter.get('content', ''))
            lines.append("")
        return "\n".join(lines)

    def export_to_docx(self, chapters: List[Dict[str, str]], filename: Optional[str] = None) -> str:
        """Placeholder for DOCX — currently returns markdown string."""
        title = filename.replace('_', ' ').replace('.docx', '') if filename else "AI Generated Course"
        content = self.export_to_markdown(chapters, title)
        
        target_file = filename or "course_output.docx"
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        return target_file
