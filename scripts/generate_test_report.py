#!/usr/bin/env python3
"""
Generate a test report to see the actual markdown output
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / "api" / ".env"
load_dotenv(env_path)

# Add API directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

def generate_test_report():
    """Generate a test report"""
    
    inspection_id = "759c864b-6ced-4983-955a-93287857a0a5"
    
    print(f"🏠 Generating report for inspection: {inspection_id}")
    print(f"   Using Cohere: {'YES' if os.getenv('COHERE_API_KEY') else 'NO'}")
    
    try:
        # Import the enhanced report (now includes Cohere when available)
        from langgraph_report_writer_enhanced import run_enhanced_report
        
        print("\n📝 Running enhanced report...")
        result = run_enhanced_report(inspection_id)
        
        if result and result.get('markdown'):
            markdown = result['markdown']
            
            # Save to file
            output_file = Path(__file__).parent / "test_report_output.md"
            with open(output_file, 'w') as f:
                f.write(markdown)
            
            print(f"\n✅ Report generated successfully!")
            print(f"   Saved to: {output_file}")
            print(f"   Sections: {result.get('sectionCount', 0)}")
            print(f"   Clips: {result.get('clipCount', 0)}")
            
            # Check for tables
            if '|' in markdown and '---' in markdown:
                print("\n⚠️  WARNING: Markdown contains table syntax!")
                # Find table lines
                lines = markdown.split('\n')
                for i, line in enumerate(lines):
                    if '|' in line and i > 0 and i < len(lines)-1:
                        if '---' in lines[i-1] or '---' in lines[i+1]:
                            print(f"   Line {i}: {line[:80]}...")
            else:
                print("\n✅ No table syntax found in markdown")
            
            return True
        else:
            print("\n❌ No markdown generated")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sys.exit(0 if generate_test_report() else 1)