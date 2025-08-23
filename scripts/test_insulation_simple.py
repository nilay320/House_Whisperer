#!/usr/bin/env python3
"""
Simple test to verify the Cohere reranker finds the correct insulation narrative.
This is a standalone test that doesn't require Firebase or the full app.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "api" / ".env")

def test_insulation_with_reranker():
    """Test that reranker finds the correct 3-4 inch insulation narrative"""
    
    print("\n" + "="*60)
    print("🧪 INSULATION NARRATIVE TEST - COHERE RERANKER")
    print("="*60)
    
    # The critical test case
    test_clip = {
        'transcript': 'Attic insulation is only about 4 inches deep',
        'image_url': 'https://example.com/insulation.jpg',
        'object': 'insulation',
        'area': 'attic',
        'section': 'insulation_ventilation'  # Correct section key from config
    }
    
    print(f"\n📝 Input: '{test_clip['transcript']}'")
    print(f"   Expected: Should find '3-4 inch depth' narrative\n")
    
    # Check if Cohere is available
    if not os.getenv('COHERE_API_KEY'):
        print("❌ No COHERE_API_KEY found in api/.env")
        print("   Add your Cohere API key to test the reranker")
        return False
    
    try:
        # Import the enhanced version first to avoid circular imports
        import langgraph_report_writer_enhanced
        # Then import the reranker version
        import langgraph_report_writer_enhanced_reranker
        _retrieve_narratives_enhanced_with_reranker = langgraph_report_writer_enhanced_reranker._retrieve_narratives_enhanced_with_reranker
        
        # Test retrieval with correct section key
        narratives = _retrieve_narratives_enhanced_with_reranker('insulation_ventilation', [test_clip], [])
        
        if not narratives:
            print("❌ No narratives found")
            return False
        
        # Check the best narrative
        best = narratives[0]
        text = best.get('text', '')
        score = best.get('rerank_score', best.get('score', 0))
        reranked = best.get('reranked', False)
        
        # Check if it found the correct narrative (multiple variations)
        found_correct = any([
            '3-4' in text.lower(),
            '3 to 4' in text.lower(),
            'three to four' in text.lower(),
            '3-4 inch' in text.lower(),
            '3 to 4 inch' in text.lower()
        ])
        
        if found_correct:
            print(f"✅ SUCCESS! Found the correct narrative")
            print(f"   Score: {score:.3f} {'🎯 (Reranked)' if reranked else ''}")
            print(f"   Text: {text[:150]}...")
            
            # Show top 3 for context
            if len(narratives) > 1:
                print("\n   Top 3 narratives:")
                for i, n in enumerate(narratives[:3], 1):
                    rscore = n.get('rerank_score', n.get('score', 0))
                    ntext = n.get('text', '')[:100]
                    print(f"   {i}. Score {rscore:.3f}: {ntext}...")
            
            return True
        else:
            print(f"❌ FAILED - Did not find '3-4 inch' narrative")
            print(f"   Got instead: {text[:150]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test execution"""
    
    print("\n🚀 TESTING COHERE RERANKER FOR INSULATION CASE")
    print("This validates the key improvement that reranker brings")
    
    success = test_insulation_with_reranker()
    
    print("\n" + "="*60)
    if success:
        print("✨ TEST PASSED - Reranker found the correct narrative!")
        print("🎉 Ready for demo day!")
    else:
        print("⚠️  Test failed - Check your COHERE_API_KEY")
    print("="*60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())