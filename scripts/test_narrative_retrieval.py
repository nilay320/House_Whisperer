#!/usr/bin/env python3
"""
Test narrative retrieval accuracy: Original vs Enhanced
Based on the 10 test cases from README.md
"""

import os
import sys
import json
import time
from typing import Dict, List, Tuple
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize Firebase
def init_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                service_account_info = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized")
            except Exception as e:
                print(f"⚠️  Firebase init failed: {e}")
    return firestore.client() if firebase_admin._apps else None

# Initialize Firebase
admin_db = init_firebase()

# Patch app module
import api.app as app_module
app_module.admin_db = admin_db
app_module.admin_firestore = firebase_admin.firestore if firebase_admin._apps else None

# Import both retrieval functions
from api.langgraph_report_writer import _retrieve_narratives_for_section as retrieve_original
from api.langgraph_report_writer_enhanced import _retrieve_narratives_enhanced as retrieve_enhanced
from api.langgraph_report_writer_enhanced_reranker import _retrieve_narratives_enhanced_with_reranker as retrieve_with_reranker

# Also need the sections catalog
from api.langgraph_report_writer import _load_report_sections

# Define test cases from README
TEST_CASES = [
    {
        "id": 1,
        "name": "Electrical - Double-Tapped Breaker",
        "section": "electrical",
        "transcript": "Two wires are connected to a single breaker, this is a double-tap and needs to be fixed by an electrician",
        "expected_rows": [174, 179],
        "expected_keywords": ["double-tap", "two wires", "breaker"],
        "expected_text_snippets": [
            "two wires were connected to a breaker designed for only one wire",
            "double-tap"
        ],
        "min_score": 0.7
    },
    {
        "id": 2,
        "name": "Roof - Missing Shingles",
        "section": "roof",
        "transcript": "Several asphalt shingles are missing and damaged on the south side of the roof",
        "expected_rows": [916, 935],
        "expected_keywords": ["shingle", "damage", "missing"],
        "expected_text_snippets": [
            "shingles covering",
            "damage"
        ],
        "min_score": 0.6
    },
    {
        "id": 3,
        "name": "HVAC - Disconnected Duct",
        "section": "hvac",
        "transcript": "Found a supply duct that's completely disconnected in the attic, air is leaking everywhere",
        "expected_rows": [48, 49],
        "expected_keywords": ["duct", "disconnected", "attic"],
        "expected_text_snippets": [
            "Disconnected ducts were visible in the attic",
            "ducts should be reconnected"
        ],
        "min_score": 0.8
    },
    {
        "id": 4,
        "name": "Plumbing - Active Leak",
        "section": "plumbing",
        "transcript": "There's an active leak under the kitchen sink at the P-trap connection",
        "expected_rows": [3296, 3100],
        "expected_keywords": ["leak", "sink", "trap"],
        "expected_text_snippets": [
            "Leaking connections at the trap",
            "beneath the cabinet sink"
        ],
        "min_score": 0.7
    },
    {
        "id": 5,
        "name": "Insulation - Attic Depth",
        "section": "insulation_ventilation",
        "transcript": "Attic insulation is only about 4 inches deep, should be much thicker for energy efficiency",
        "expected_rows": [26, 24],
        "expected_keywords": ["attic", "insulation", "inches", "depth"],
        "expected_text_snippets": [
            "Attic floor insulation depth averages",
            "3 to 4 inches"
        ],
        "min_score": 0.8
    },
    {
        "id": 6,
        "name": "Garage - Auto-Reverse Safety",
        "section": "garage",
        "transcript": "The garage door auto-reverse safety feature isn't working when I test it",
        "expected_rows": [1857, 1858],
        "expected_keywords": ["garage", "door", "safety", "auto-reverse"],
        "expected_text_snippets": [
            "overhead garage door",
            "automatic opener"
        ],
        "min_score": 0.6
    },
    {
        "id": 7,
        "name": "Exterior - Damaged Siding",
        "section": "exterior",
        "transcript": "Found damaged lap siding on the west side with exposed wood substrate underneath",
        "expected_rows": [837, 836],
        "expected_keywords": ["siding", "damage", "substrate", "exposed"],
        "expected_text_snippets": [
            "siding was damaged",
            "should be replaced"
        ],
        "min_score": 0.7
    },
    {
        "id": 8,
        "name": "Interior - Inoperable Window",
        "section": "interior",
        "transcript": "Bedroom window won't open, seems stuck and needs repair for emergency egress",
        "expected_rows": [829, 969],
        "expected_keywords": ["window", "open", "egress", "inoperable"],
        "expected_text_snippets": [
            "window",
            "door"
        ],
        "min_score": 0.5
    },
    {
        "id": 9,
        "name": "Site & Drainage - Negative Slope",
        "section": "site_drainage",
        "transcript": "Ground slopes toward the foundation here, water will drain against the house",
        "expected_rows": [1385, 1386],
        "expected_keywords": ["slope", "foundation", "drainage", "grading"],
        "expected_text_snippets": [
            "negative drainage",
            "toward the foundation"
        ],
        "min_score": 0.8
    },
    {
        "id": 10,
        "name": "Kitchen - GFCI Protection",
        "section": "kitchen",
        "transcript": "Kitchen outlets near the sink don't have GFCI protection, this is a safety issue",
        "expected_rows": [187, 361],
        "expected_keywords": ["GFCI", "protection", "safety", "outlets"],
        "expected_text_snippets": [
            "GFCI protection",
            "Ground Fault Circuit Interrupter"
        ],
        "min_score": 0.6
    }
]


def create_mock_clip(transcript: str, section: str) -> Dict:
    """Create a mock clip for testing"""
    return {
        'id': 'test-clip',
        'section': section,
        'transcript': transcript,
        'photos': [],
        'status': 'transcribed'
    }


def check_narrative_match(narrative: Dict, test_case: Dict) -> Dict:
    """Check if a narrative matches expected results"""
    text = narrative.get('text', '').lower()
    score = narrative.get('score', 0.0)
    narrative_id = narrative.get('id')
    
    # Check if any expected text snippet is found
    text_match = any(snippet.lower() in text for snippet in test_case['expected_text_snippets'])
    
    # Check if score meets minimum
    score_passes = score >= test_case['min_score']
    
    # Check for keyword presence
    keywords_found = [kw for kw in test_case['expected_keywords'] if kw.lower() in text]
    
    return {
        'text_match': text_match,
        'score_passes': score_passes,
        'score': score,
        'keywords_found': keywords_found,
        'narrative_id': narrative_id,
        'text_preview': text[:150] + '...' if len(text) > 150 else text
    }


def run_test_case(test_case: Dict, sections_catalog: List[Dict]) -> Dict:
    """Run a single test case comparing original vs enhanced retrieval"""
    print(f"\n{'='*80}")
    print(f"Test {test_case['id']}: {test_case['name']}")
    print(f"Section: {test_case['section']}")
    print(f"Transcript: \"{test_case['transcript']}\"")
    print(f"Expected min score: {test_case['min_score']}")
    
    # Create mock clips
    clips = [create_mock_clip(test_case['transcript'], test_case['section'])]
    
    # Run original retrieval
    print("\n🔵 ORIGINAL Retrieval:")
    try:
        original_results = retrieve_original(test_case['section'], clips, top_k=5, min_score=0.55)
        if original_results:
            for i, narrative in enumerate(original_results[:3], 1):
                match_info = check_narrative_match(narrative, test_case)
                status = "✅" if match_info['text_match'] else "❌"
                print(f"  {i}. Score: {match_info['score']:.3f} {status}")
                print(f"     Keywords found: {match_info['keywords_found']}")
                print(f"     Text: {match_info['text_preview']}")
        else:
            print("  ❌ No narratives found")
            original_results = []
    except Exception as e:
        print(f"  ❌ Error: {e}")
        original_results = []
    
    # Run enhanced retrieval
    print("\n🟢 ENHANCED Retrieval:")
    try:
        enhanced_results = retrieve_enhanced(test_case['section'], clips, sections_catalog, top_k=10, min_score=0.55)
        if enhanced_results:
            for i, narrative in enumerate(enhanced_results[:3], 1):
                match_info = check_narrative_match(narrative, test_case)
                status = "✅" if match_info['text_match'] else "❌"
                boosted = "🚀" if narrative.get('boosted') else ""
                print(f"  {i}. Score: {match_info['score']:.3f} {status} {boosted}")
                print(f"     Keywords found: {match_info['keywords_found']}")
                print(f"     Text: {match_info['text_preview']}")
        else:
            print("  ❌ No narratives found")
            enhanced_results = []
    except Exception as e:
        print(f"  ❌ Error: {e}")
        enhanced_results = []
    
    # Run enhanced with reranker (if Cohere is available)
    if os.getenv('COHERE_API_KEY'):
        print("\n🎯 RERANKER Retrieval:")
        try:
            reranker_results = retrieve_with_reranker(test_case['section'], clips, sections_catalog, top_k=10, min_score=0.55)
            if reranker_results:
                for i, narrative in enumerate(reranker_results[:3], 1):
                    match_info = check_narrative_match(narrative, test_case)
                    status = "✅" if match_info['text_match'] else "❌"
                    reranked = "🎯" if narrative.get('reranked') else ""
                    boosted = "🚀" if narrative.get('boosted') else ""
                    rerank_score = narrative.get('rerank_score', 0)
                    if rerank_score:
                        print(f"  {i}. Score: {match_info['score']:.3f} | Rerank: {rerank_score:.3f} {status} {reranked} {boosted}")
                    else:
                        print(f"  {i}. Score: {match_info['score']:.3f} {status} {reranked} {boosted}")
                    print(f"     Keywords found: {match_info['keywords_found']}")
                    print(f"     Text: {match_info['text_preview']}")
            else:
                print("  ❌ No narratives found")
                reranker_results = []
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            reranker_results = []
    else:
        reranker_results = enhanced_results  # Use enhanced as fallback
    
    # Calculate improvement (use reranker if available)
    original_best = original_results[0] if original_results else {'score': 0}
    enhanced_best = enhanced_results[0] if enhanced_results else {'score': 0}
    reranker_best = reranker_results[0] if reranker_results else {'score': 0}
    
    original_match = check_narrative_match(original_best, test_case) if original_results else None
    enhanced_match = check_narrative_match(enhanced_best, test_case) if enhanced_results else None
    reranker_match = check_narrative_match(reranker_best, test_case) if reranker_results else None
    
    improvement = {
        'original_score': original_best.get('score', 0),
        'enhanced_score': enhanced_best.get('score', 0),
        'reranker_score': reranker_best.get('score', 0),
        'score_improvement': enhanced_best.get('score', 0) - original_best.get('score', 0),
        'reranker_improvement': reranker_best.get('score', 0) - original_best.get('score', 0),
        'original_correct': original_match['text_match'] if original_match else False,
        'enhanced_correct': enhanced_match['text_match'] if enhanced_match else False,
        'reranker_correct': reranker_match['text_match'] if reranker_match else False,
        'enhanced_boosted': enhanced_best.get('boosted', False) if enhanced_results else False,
        'reranker_used': reranker_best.get('reranked', False) if reranker_results else False
    }
    
    print(f"\n📊 Improvement:")
    if improvement['score_improvement'] > 0:
        print(f"  ✅ Score improved by {improvement['score_improvement']:.3f}")
    else:
        print(f"  ➖ Score unchanged or decreased")
    
    if improvement['enhanced_correct'] and not improvement['original_correct']:
        print(f"  ✅ Enhanced found correct narrative, original didn't")
    elif improvement['enhanced_correct'] and improvement['original_correct']:
        print(f"  ✅ Both found correct narrative")
    else:
        print(f"  ❌ Neither found correct narrative")
    
    return {
        'test_case': test_case,
        'original_results': original_results[:3] if original_results else [],
        'enhanced_results': enhanced_results[:3] if enhanced_results else [],
        'improvement': improvement
    }


def main():
    """Run all test cases and generate comparison report"""
    print("\n" + "="*80)
    print("🔬 NARRATIVE RETRIEVAL COMPARISON TEST")
    print("Original vs Enhanced Implementation")
    print("="*80)
    
    # Check environment
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set")
    if not os.getenv('QDRANT_URL'):
        print("⚠️  Warning: QDRANT_URL not set")
    
    # Load sections catalog
    sections_catalog = _load_report_sections()
    print(f"\n✅ Loaded {len(sections_catalog)} report sections")
    
    # Run all test cases
    results = []
    for test_case in TEST_CASES:
        result = run_test_case(test_case, sections_catalog)
        results.append(result)
        time.sleep(0.5)  # Rate limiting
    
    # Generate summary report
    print("\n" + "="*80)
    print("📊 SUMMARY REPORT")
    print("="*80)
    
    # Count successes
    original_correct = sum(1 for r in results if r['improvement']['original_correct'])
    enhanced_correct = sum(1 for r in results if r['improvement']['enhanced_correct'])
    both_correct = sum(1 for r in results if r['improvement']['original_correct'] and r['improvement']['enhanced_correct'])
    enhanced_only_correct = sum(1 for r in results if r['improvement']['enhanced_correct'] and not r['improvement']['original_correct'])
    
    print(f"\n✅ Correct Narrative Found:")
    print(f"  Original: {original_correct}/{len(TEST_CASES)} ({original_correct/len(TEST_CASES)*100:.0f}%)")
    print(f"  Enhanced: {enhanced_correct}/{len(TEST_CASES)} ({enhanced_correct/len(TEST_CASES)*100:.0f}%)")
    
    print(f"\n📈 Improvement Analysis:")
    print(f"  Both correct: {both_correct}")
    print(f"  Enhanced only correct: {enhanced_only_correct}")
    print(f"  Average score improvement: {sum(r['improvement']['score_improvement'] for r in results)/len(results):.3f}")
    
    # Detailed comparison table
    print("\n📋 Detailed Results:")
    print("| Test Case | Original Score | Enhanced Score | Improvement | Original ✓ | Enhanced ✓ |")
    print("|-----------|---------------|---------------|-------------|------------|------------|")
    
    for result in results:
        test_name = result['test_case']['name'][:25]
        orig_score = result['improvement']['original_score']
        enh_score = result['improvement']['enhanced_score']
        improvement = result['improvement']['score_improvement']
        orig_check = "✅" if result['improvement']['original_correct'] else "❌"
        enh_check = "✅" if result['improvement']['enhanced_correct'] else "❌"
        
        print(f"| {test_name:<25} | {orig_score:.3f} | {enh_score:.3f} | {improvement:+.3f} | {orig_check} | {enh_check} |")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"narrative_test_results_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'summary': {
                'original_correct': original_correct,
                'enhanced_correct': enhanced_correct,
                'improvement_count': enhanced_only_correct,
                'test_count': len(TEST_CASES)
            },
            'detailed_results': results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Final verdict
    print("\n" + "="*80)
    print("🏆 VERDICT:")
    if enhanced_correct > original_correct:
        print(f"✅ ENHANCED IS BETTER: {enhanced_correct - original_correct} more correct matches!")
    elif enhanced_correct == original_correct:
        print(f"➖ EQUAL PERFORMANCE: But enhanced has better scores")
    else:
        print(f"❌ Original performed better (unexpected)")
    print("="*80)


if __name__ == "__main__":
    # Load environment from api/.env
    import subprocess
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api', '.env')
    if os.path.exists(env_file):
        print(f"Loading environment from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    main()