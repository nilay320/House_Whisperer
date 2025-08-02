#!/usr/bin/env python3
"""Compare PDF extraction methods to ensure no content is lost."""

import os
import sys
import pymupdf4llm

# Add the old pdf-parse equivalent
import fitz  # PyMuPDF

def extract_with_pymupdf4llm(file_path: str) -> str:
    """Extract using pymupdf4llm (our current method)."""
    text = pymupdf4llm.to_markdown(file_path)
    return text.replace('\x00', '').strip()

def extract_with_basic_pymupdf(file_path: str) -> str:
    """Extract using basic PyMuPDF (similar to pdf-parse)."""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    # Clean similar to how pdf-parse would
    text = ' '.join(text.split())  # Normalize whitespace
    return text.strip()

def analyze_extraction_difference():
    """Analyze the difference between extraction methods."""
    file_path = os.path.join(
        os.path.dirname(__file__), 
        "../../docs/data/SOP/InterNACHI SOP.pdf"
    )
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    print("📄 Analyzing InterNACHI SOP.pdf extraction methods\n")
    
    # Method 1: pymupdf4llm (current)
    print("🔧 Method 1: pymupdf4llm (current Python method)")
    text1 = extract_with_pymupdf4llm(file_path)
    print(f"   Length: {len(text1)} characters")
    print(f"   Preview: {text1[:200]}...")
    
    # Method 2: Basic PyMuPDF (similar to pdf-parse)
    print("\n🔧 Method 2: Basic PyMuPDF (similar to old pdf-parse)")
    text2 = extract_with_basic_pymupdf(file_path)
    print(f"   Length: {len(text2)} characters")
    print(f"   Preview: {text2[:200]}...")
    
    # Analysis
    print(f"\n📊 Analysis:")
    print(f"   pymupdf4llm: {len(text1)} chars")
    print(f"   Basic PyMuPDF: {len(text2)} chars")
    print(f"   Difference: {len(text2) - len(text1)} chars ({((len(text2) - len(text1))/len(text2)*100):.1f}%)")
    
    # Check what's different
    print(f"\n🔍 Content Analysis:")
    
    # Check for key sections
    key_sections = [
        "STANDARDS OF PRACTICE",
        "ELECTRICAL",
        "PLUMBING", 
        "HEATING",
        "INSPECTION",
        "REQUIREMENTS",
        "INSPECTOR",
        "LIMITATIONS"
    ]
    
    print("   Key sections present:")
    for section in key_sections:
        in_method1 = section.upper() in text1.upper()
        in_method2 = section.upper() in text2.upper()
        status1 = "✅" if in_method1 else "❌"
        status2 = "✅" if in_method2 else "❌"
        print(f"      {section}: pymupdf4llm {status1} | Basic PyMuPDF {status2}")
    
    # Check for any major content loss
    if len(text2) - len(text1) > 1000:
        print(f"\n⚠️  WARNING: Large difference detected!")
        print("   Checking what might be missing...")
        
        # Sample some content that's in method 2 but not method 1
        words2 = set(text2.lower().split())
        words1 = set(text1.lower().split())
        missing_words = words2 - words1
        
        if missing_words:
            print(f"   Words in basic extraction but not pymupdf4llm: {len(missing_words)}")
            if len(missing_words) < 20:
                print(f"   Missing words: {sorted(list(missing_words))}")
    else:
        print(f"\n✅ Difference is reasonable - likely just formatting cleanup")
    
    # Word count comparison
    words1 = len(text1.split())
    words2 = len(text2.split())
    print(f"\n📝 Word count:")
    print(f"   pymupdf4llm: {words1} words")
    print(f"   Basic PyMuPDF: {words2} words")
    print(f"   Word difference: {words2 - words1} words")
    
    return text1, text2

if __name__ == "__main__":
    analyze_extraction_difference()