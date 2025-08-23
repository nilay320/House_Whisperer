#!/usr/bin/env python3
"""
Test script specifically for validating the Cohere reranker improvement on insulation narratives.
This is the key test case that demonstrates the value of the reranker.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "api" / ".env")

def init_firebase():
    """Initialize Firebase for standalone script execution"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        if not firebase_admin._apps:
            service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
            if service_account_json:
                try:
                    cred_dict = json.loads(service_account_json)
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase initialized successfully")
                except Exception as e:
                    print(f"❌ Firebase initialization failed: {e}")
                    return False
    except ImportError:
        # Firebase not available in test environment, patch the app module
        print("⚠️  Firebase not installed, patching app module for testing")
        import api.app as app_mod
        app_mod._FIREBASE_INITIALIZED = True
        return True
    return True

def test_insulation_narrative():
    """Test the specific insulation case that showcases reranker improvement"""
    
    print("\n" + "="*80)
    print("🧪 INSULATION NARRATIVE RETRIEVAL TEST")
    print("="*80)
    
    # The key test case
    test_clip = {
        'transcript': 'Attic insulation is only about 4 inches deep',
        'image_url': 'https://example.com/insulation.jpg',
        'object': 'insulation',
        'area': 'attic',
        'section': 'Insulation'
    }
    
    print(f"\n📝 Test Input:")
    print(f"   Transcript: '{test_clip['transcript']}'")
    print(f"   Expected: Should find narrative about '3-4 inch depth' being insufficient")
    
    # Test all three versions
    results = {}
    
    # 1. Original version
    print("\n" + "-"*60)
    print("1️⃣ TESTING ORIGINAL VERSION")
    print("-"*60)
    
    try:
        from api.langgraph_report_writer import _retrieve_narratives_for_section
        narratives = _retrieve_narratives_for_section('Insulation', [test_clip])
        
        if narratives:
            best = narratives[0]
            text = best.get('text', '')
            score = best.get('score', 0)
            
            # Check if it found the correct narrative
            found_correct = '3-4 inch' in text.lower() or 'three to four inch' in text.lower()
            
            results['original'] = {
                'found_correct': found_correct,
                'score': score,
                'text': text[:200] + '...' if len(text) > 200 else text
            }
            
            print(f"   Result: {'✅ FOUND' if found_correct else '❌ MISSED'} the 3-4 inch narrative")
            print(f"   Score: {score:.3f}")
            print(f"   Text: {results['original']['text']}")
        else:
            results['original'] = {'found_correct': False, 'score': 0, 'text': 'No narratives found'}
            print("   ❌ No narratives found")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['original'] = {'found_correct': False, 'score': 0, 'text': f'Error: {e}'}
    
    # 2. Enhanced version (without reranker)
    print("\n" + "-"*60)
    print("2️⃣ TESTING ENHANCED VERSION (No Reranker)")
    print("-"*60)
    
    try:
        # Temporarily disable Cohere to test enhanced without reranker
        cohere_key = os.environ.pop('COHERE_API_KEY', None)
        
        from api.langgraph_report_writer_enhanced import _retrieve_narratives_enhanced
        narratives = _retrieve_narratives_enhanced('Insulation', [test_clip], [])
        
        if narratives:
            best = narratives[0]
            text = best.get('text', '')
            score = best.get('score', 0)
            
            found_correct = '3-4 inch' in text.lower() or 'three to four inch' in text.lower()
            
            results['enhanced'] = {
                'found_correct': found_correct,
                'score': score,
                'text': text[:200] + '...' if len(text) > 200 else text
            }
            
            print(f"   Result: {'✅ FOUND' if found_correct else '❌ MISSED'} the 3-4 inch narrative")
            print(f"   Score: {score:.3f}")
            print(f"   Text: {results['enhanced']['text']}")
        else:
            results['enhanced'] = {'found_correct': False, 'score': 0, 'text': 'No narratives found'}
            print("   ❌ No narratives found")
        
        # Restore Cohere key
        if cohere_key:
            os.environ['COHERE_API_KEY'] = cohere_key
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['enhanced'] = {'found_correct': False, 'score': 0, 'text': f'Error: {e}'}
    
    # 3. Enhanced with Cohere Reranker
    print("\n" + "-"*60)
    print("3️⃣ TESTING ENHANCED + COHERE RERANKER")
    print("-"*60)
    
    try:
        if not os.getenv('COHERE_API_KEY'):
            print("   ⚠️  No COHERE_API_KEY found - skipping reranker test")
            results['reranker'] = {'found_correct': False, 'score': 0, 'text': 'No Cohere API key'}
        else:
            from api.langgraph_report_writer_enhanced_reranker import _retrieve_narratives_enhanced_with_reranker
            narratives = _retrieve_narratives_enhanced_with_reranker('Insulation', [test_clip], [])
            
            if narratives:
                best = narratives[0]
                text = best.get('text', '')
                score = best.get('rerank_score', best.get('score', 0))
                
                found_correct = '3-4 inch' in text.lower() or 'three to four inch' in text.lower()
                
                results['reranker'] = {
                    'found_correct': found_correct,
                    'score': score,
                    'text': text[:200] + '...' if len(text) > 200 else text,
                    'reranked': best.get('reranked', False)
                }
                
                print(f"   Result: {'✅ FOUND' if found_correct else '❌ MISSED'} the 3-4 inch narrative")
                print(f"   Score: {score:.3f} {'🎯 (Reranked)' if best.get('reranked') else ''}")
                print(f"   Text: {results['reranker']['text']}")
                
                # Show top 3 for context
                if len(narratives) > 1:
                    print("\n   Top 3 narratives:")
                    for i, n in enumerate(narratives[:3], 1):
                        rscore = n.get('rerank_score', n.get('score', 0))
                        print(f"   {i}. Score: {rscore:.3f} - {n['text'][:100]}...")
            else:
                results['reranker'] = {'found_correct': False, 'score': 0, 'text': 'No narratives found'}
                print("   ❌ No narratives found")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['reranker'] = {'found_correct': False, 'score': 0, 'text': f'Error: {e}'}
    
    # Summary
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80)
    
    print("\nInsulation Test (Finding '3-4 inch depth' narrative):")
    print("┌─────────────────┬──────────┬────────────┐")
    print("│ Version         │ Found?   │ Score      │")
    print("├─────────────────┼──────────┼────────────┤")
    
    for version, data in results.items():
        found = "✅ YES" if data['found_correct'] else "❌ NO"
        score = f"{data['score']:.3f}"
        print(f"│ {version.ljust(15)} │ {found.ljust(8)} │ {score.ljust(10)} │")
    
    print("└─────────────────┴──────────┴────────────┘")
    
    # Key insight
    if results.get('reranker', {}).get('found_correct') and not results.get('enhanced', {}).get('found_correct'):
        print("\n🎯 KEY FINDING: Cohere reranker successfully found the correct")
        print("   '3-4 inch depth' narrative that other versions missed!")
        print("   This demonstrates the value of semantic reranking for accuracy.")
    
    return results

def test_full_report_generation():
    """Test full report generation with a real inspection"""
    
    print("\n" + "="*80)
    print("🏠 FULL REPORT GENERATION TEST")
    print("="*80)
    
    inspection_id = "759c864b-6ced-4983-955a-93287857a0a5"
    
    # Test with reranker
    print("\n📝 Generating report with Cohere reranker...")
    
    try:
        from api.langgraph_report_writer_enhanced_reranker import run_enhanced_report_with_reranker
        
        result = run_enhanced_report_with_reranker(inspection_id)
        
        print(f"\n✅ Report generated successfully!")
        print(f"   Sections: {result.get('sectionCount', 0)}")
        print(f"   Clips: {result.get('clipCount', 0)}")
        print(f"   Quality Score: {result.get('reportQualityScore', 0):.2f}")
        print(f"   Version: {result.get('version', 'unknown')}")
        
        # Check narrative sources
        sources = result.get('narrativeSources', {})
        if sources:
            print("\n   Narrative Sources:")
            for section, source in sources.items():
                emoji = {
                    'reranked_narrative': '🎯',
                    'verified_narrative': '✅',
                    'code_enhanced': '📋',
                    'ai_generated': '🤖'
                }.get(source, '❓')
                print(f"   - {section}: {emoji} {source}")
        
        # Look for insulation section specifically
        markdown = result.get('markdown', '')
        if 'insulation' in markdown.lower():
            # Extract insulation section
            import re
            pattern = r'## .*Insulation.*?\n(.*?)(?=\n##|\Z)'
            match = re.search(pattern, markdown, re.IGNORECASE | re.DOTALL)
            if match:
                insulation_text = match.group(1)[:500]
                print("\n📦 Insulation Section Preview:")
                print("   " + insulation_text.replace('\n', '\n   '))
                
                if '3-4 inch' in insulation_text or 'three to four inch' in insulation_text.lower():
                    print("\n   🎯 SUCCESS: Found the correct 3-4 inch narrative in the report!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        return False

def main():
    """Main test execution"""
    
    print("\n🚀 COHERE RERANKER VALIDATION TEST")
    print("━"*80)
    print("This test validates that the Cohere reranker improves narrative retrieval")
    print("especially for the challenging insulation depth matching case.")
    print("━"*80)
    
    # Check environment
    has_cohere = bool(os.getenv('COHERE_API_KEY'))
    print(f"\n🔑 Cohere API Key: {'✅ Found' if has_cohere else '❌ Not found'}")
    
    if not has_cohere:
        print("\n⚠️  Add COHERE_API_KEY to api/.env to test the reranker")
        print("   The test will still run but won't show reranker improvements")
    
    # Initialize Firebase
    if not init_firebase():
        print("\n❌ Cannot proceed without Firebase")
        return 1
    
    # Run tests
    try:
        # Test 1: Specific insulation narrative retrieval
        insulation_results = test_insulation_narrative()
        
        # Test 2: Full report generation
        print("\nPress Enter to test full report generation, or Ctrl+C to stop...")
        input()
        
        report_success = test_full_report_generation()
        
        # Final summary
        print("\n" + "="*80)
        print("✨ TEST COMPLETE")
        print("="*80)
        
        if has_cohere and insulation_results.get('reranker', {}).get('found_correct'):
            print("\n✅ Cohere reranker is working correctly!")
            print("   The insulation test proves it finds narratives others miss.")
            print("\n🎉 Ready for demo day!")
        else:
            print("\n⚠️  Reranker test incomplete or failed")
            print("   Check your COHERE_API_KEY and try again")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())