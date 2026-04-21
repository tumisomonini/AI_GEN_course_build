from typing import Dict, List, Any, Tuple
import re
from collections import Counter
import statistics

_JUNK_LINE_PATTERNS = re.compile(
    r'^(copyright|privacy|terms|cookie|navigation|menu|footer|header|\d{4}-\d{4}|page \d+|http)',
    re.IGNORECASE
)
_OUTLIER_PATTERNS = re.compile(r'[!@#$%^&*()_+=\[\]{}|;:\'",<>?\/\\]{3,}', re.IGNORECASE)

def clean_raw_text(raw_syllabus: str) -> Tuple[str, Dict[str, int]]:
    """
    Comprehensive raw text cleaning:
    - Null/empty line removal
    - Outlier lines (too short/long, high special chars, patterns)
    - Normalization (consistent separators)
    - Repetition reduction
    """
    if not raw_syllabus or not raw_syllabus.strip():
        return '', {'removed_null': 1, 'lines_kept': 0}
    
    lines = raw_syllabus.split('\n')
    cleaned_lines = []
    line_lengths = []
    
    stats = {
        'total_lines': len(lines),
        'removed_null': 0,
        'removed_short': 0,
        'removed_long': 0,
        'removed_junk': 0,
        'removed_outlier': 0,
        'removed_duplicate': 0,
        'lines_kept': 0
    }
    
    seen_lines = Counter()
    for line in lines:
        line = line.strip()
        if not line:
            stats['removed_null'] += 1
            continue
        
        l_len = len(line)
        line_lengths.append(l_len)
        
        # Outlier length (mean ± 2 std)
        if line_lengths:
            mean_len = statistics.mean(line_lengths)
            std_len = statistics.stdev(line_lengths) if len(line_lengths) > 1 else 0
            if l_len < 5 or l_len > 300 or abs(l_len - mean_len) > 2 * std_len:
                stats['removed_short' if l_len < 5 else 'removed_long' if l_len > 300 else 'removed_outlier'] += 1
                continue
        
        # Junk patterns
        if _JUNK_LINE_PATTERNS.search(line) or line.isdigit():
            stats['removed_junk'] += 1
            continue
        
        # High special chars
        spec_ratio = len(_OUTLIER_PATTERNS.findall(line)) / max(len(line), 1)
        if spec_ratio > 0.3:
            stats['removed_outlier'] += 1
            continue
        
        # Duplicate lines (top 3 most common)
        seen_lines[line] += 1
        if seen_lines[line] > 3:
            stats['removed_duplicate'] += 1
            continue
        
        cleaned_lines.append(line)
        stats['lines_kept'] += 1
    
    cleaned_text = '\n\n'.join(cleaned_lines)
    stats['avg_line_len'] = round(statistics.mean(line_lengths) if line_lengths else 0, 1)
    
    return cleaned_text, stats

def clean_syllabus_dict(structured: Dict[str, List[str]]) -> Tuple[Dict[str, List[str]], Dict[str, Any]]:
    """
    Clean parsed syllabus dict:
    - Remove empty/short items
    - Deduplicate (exact)
    - Outlier removal per field
    - Add cleaning stats
    """
    cleaned_struct = {}
    overall_stats = {'fields_cleaned': [], 'total_items': 0, 'items_kept': 0}
    
    for field, items in structured.items():
        if not isinstance(items, list):
            cleaned_struct[field] = items
            continue
        
        clean_items = []
        item_lens = []
        seen = set()
        
        field_stats = {'field': field, 'total': len(items), 'kept': 0, 'removed_short': 0, 'deduped': 0}
        
        for item in items:
            item_str = str(item).strip()
            if len(item_str) < 10 or not item_str:
                field_stats['removed_short'] += 1
                continue
            
            if item_str in seen:
                field_stats['deduped'] += 1
                continue
            
            clean_items.append(item_str)
            seen.add(item_str)
            item_lens.append(len(item_str))
            field_stats['kept'] += 1
        
        # Outlier removal (per field)
        if len(clean_items) > 3 and item_lens:
            mean_len = statistics.mean(item_lens)
            std_len = statistics.stdev(item_lens)
            final_items = [it for i, it in enumerate(clean_items) if abs(len(it) - mean_len) <= 2 * std_len]
            field_stats['removed_outlier'] = len(clean_items) - len(final_items)
            clean_items = final_items[:15]  # Cap per field
        
        cleaned_struct[field] = clean_items
        overall_stats['fields_cleaned'].append(field_stats)
        overall_stats['total_items'] += field_stats['total']
        overall_stats['items_kept'] += field_stats['kept']
    
    return cleaned_struct, overall_stats

def log_cleaning_stats(stats: Dict[str, Any], stage: str = 'raw') -> None:
    """
    Print structured cleaning metrics.
    """
    print(f"🧹 ETL {stage.upper()} Cleaning: {stats}")
