#!/usr/bin/env python3
"""
Test script to demonstrate triggering Inspector RAG (code-enhanced narratives)
"""

import os
import sys
from pathlib import Path

# Setup paths and environment
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
os.chdir(Path(__file__).parent.parent / "api")

from dotenv import load_dotenv
load_dotenv()

# Enable debug logging to see the cascade
os.environ['REPORT_LOGS'] = '1'

def test_inspector_rag_trigger():
    """Test triggering the Inspector RAG fallback"""
    
    print("\n" + "="*70)
    print("🔬 INSPECTOR RAG TRIGGER TEST")
    print("="*70)
    print("\nThis test demonstrates how to trigger code-enhanced narratives")
    print("from the Inspector RAG system.\n")
    
    # Import the enhanced report writer
    from langgraph_report_writer_enhanced import (
        _retrieve_narratives_enhanced,
        _query_inspector_rag
    )
    
    # Test cases designed to trigger RAG
    test_cases = [
        {
            'name': 'Sparse Section (site_drainage)',
            'section': 'site_drainage',
            'clips': [{
                'transcript': 'Foundation drainage is inadequate, water pooling observed within 6 feet of structure',
                'image_url': 'test.jpg'
            }]
        },
        {
            'name': 'Technical Code Citation',
            'section': 'electrical',
            'clips': [{
                'transcript': 'NEC 210.8(A)(3) violation - garage receptacles lack GFCI protection required by code',
                'image_url': 'test.jpg'
            }]
        },
        {
            'name': 'Uncommon Issue in Sparse Section',
            'section': 'environmental',
            'clips': [{
                'transcript': 'Vermiculite insulation present in attic, potential asbestos concern',
                'image_url': 'test.jpg'
            }]
        },
        {
            'name': 'Building Code Specific',
            'section': 'garage',
            'clips': [{
                'transcript': 'IRC R302.5.1 fire separation requirements not met between garage and living space',
                'image_url': 'test.jpg'
            }]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"📋 Test: {test_case['name']}")
        print(f"   Section: {test_case['section']}")
        print(f"   Transcript: {test_case['clips'][0]['transcript'][:60]}...")
        print(f"{'='*60}")
        
        # Step 1: Try database narratives
        print("\n1️⃣ Trying database narratives...")
        narratives = _retrieve_narratives_enhanced(
            test_case['section'], 
            test_case['clips'], 
            []
        )
        
        if narratives:
            best_score = narratives[0].get('score', 0)
            print(f"   Best match score: {best_score:.3f}")
            print(f"   Narrative: {narratives[0].get('text', '')[:100]}...")
            
            if best_score >= 0.7:
                print(f"   ✅ Would use verified narrative (score >= 0.7)")
            else:
                print(f"   ⚠️ Score too low (< 0.7), would trigger fallback")
        else:
            print("   ❌ No narratives found, would trigger fallback")
            best_score = 0
        
        # Step 2: Test Inspector RAG (if score < 0.7)
        if best_score < 0.7:
            print("\n2️⃣ Triggering Inspector RAG...")
            rag_result = _query_inspector_rag(
                test_case['section'], 
                test_case['clips']
            )
            
            if rag_result:
                confidence = rag_result.get('confidence', 0)
                print(f"   RAG confidence: {confidence:.3f}")
                print(f"   RAG response: {rag_result.get('text', '')[:150]}...")
                
                if confidence > 0.6:
                    print(f"   📋 Would use CODE-ENHANCED narrative!")
                else:
                    print(f"   Score too low, would generate with GPT-4")
            else:
                print("   ❌ RAG not available or no result")
                print("   🤖 Would fall back to GPT-4 generation")
    
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print("""
    The cascade for narrative selection:
    1. Database narrative (score >= 0.7) → ✅ Verified
    2. Database narrative (score < 0.7) → Try RAG
    3. Inspector RAG (confidence > 0.6) → 📋 Code-Enhanced  
    4. Fallback → 🤖 AI Generated
    
    To trigger Inspector RAG:
    - Use sections with few narratives (site_drainage, environmental)
    - Use technical language with code citations
    - Describe uncommon or specific issues
    """)

if __name__ == "__main__":
    test_inspector_rag_trigger()