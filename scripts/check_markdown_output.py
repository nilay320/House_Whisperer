#!/usr/bin/env python3
"""
Check what markdown is actually being generated
"""

import os
import sys
from pathlib import Path

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
os.chdir(Path(__file__).parent.parent / "api")

# Load environment
from dotenv import load_dotenv
load_dotenv()

def check_markdown():
    """Generate a simple test to see what markdown is produced"""
    
    # Create a minimal test state
    test_state = {
        'inspection_id': 'test-123',
        'grouped': {
            'insulation_ventilation': [
                {'transcript': 'Attic insulation is only about 4 inches deep', 'image_url': 'test.jpg'}
            ]
        },
        'sections_catalog': [
            {'key': 'insulation_ventilation', 'label': 'Insulation & Ventilation'}
        ],
        'narratives_by_section': {
            'insulation_ventilation': [
                {'text': 'Test narrative about insulation', 'score': 0.8}
            ]
        },
        'narrative_sources': {
            'insulation_ventilation': 'reranked_narrative'
        },
        'section_severity': {
            'insulation_ventilation': 'info'
        },
        'quality_scores': {
            'insulation_ventilation': 0.8
        }
    }
    
    try:
        from langgraph_report_writer_enhanced import _render_enhanced_markdown
        
        markdown, _, _, _, _, _ = _render_enhanced_markdown(
            test_state['inspection_id'],
            test_state['grouped'],
            test_state['sections_catalog'],
            test_state['narratives_by_section'],
            test_state['narrative_sources'],
            test_state['section_severity'],
            test_state['quality_scores']
        )
        
        print("Generated Markdown:")
        print("="*60)
        print(markdown)
        print("="*60)
        
        # Check for tables
        if '|' in markdown:
            print("\n⚠️  WARNING: Found pipe character!")
            lines = markdown.split('\n')
            for i, line in enumerate(lines, 1):
                if '|' in line:
                    print(f"   Line {i}: {line}")
        else:
            print("\n✅ No table syntax found")
        
        return markdown
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    check_markdown()