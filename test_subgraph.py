#!/usr/bin/env python3
"""
Test script for subgraph implementation
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

# Load environment variables from api/.env
env_path = os.path.join(os.path.dirname(__file__), 'api', '.env')
load_dotenv(env_path)
print(f"📁 Loaded environment from: {env_path}")

# Set environment variables for testing
os.environ['USE_SUBGRAPH_REPORT'] = 'true'
os.environ['ENABLE_QUALITY_LOOP'] = 'true'
os.environ['MAX_QUALITY_ITERATIONS'] = '2'
os.environ['QUALITY_THRESHOLD'] = '0.75'

async def test_subgraph():
    """Test the subgraph implementation"""
    
    print("=" * 60)
    print("TESTING SUBGRAPH IMPLEMENTATION")
    print("=" * 60)
    
    # Import the subgraph module
    from langgraph_report_writer_subgraph import (
        generate_report_with_subgraph,
        get_report_version,
        HAS_COHERE,
        ENABLE_QUALITY_LOOP,
        MAX_QUALITY_ITERATIONS,
        QUALITY_THRESHOLD
    )
    
    # Print configuration
    print("\n📋 CONFIGURATION:")
    print(f"  Version: {get_report_version()}")
    print(f"  Cohere Available: {HAS_COHERE}")
    print(f"  Quality Loop Enabled: {ENABLE_QUALITY_LOOP}")
    print(f"  Max Iterations: {MAX_QUALITY_ITERATIONS}")
    print(f"  Quality Threshold: {QUALITY_THRESHOLD}")
    
    # Test with a mock inspection ID
    inspection_id = "test_inspection_123"
    
    print(f"\n🔍 Testing with inspection: {inspection_id}")
    print("-" * 40)
    
    try:
        # Run the subgraph
        result = await generate_report_with_subgraph(inspection_id)
        
        # Check results
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Report generated successfully!")
            print(f"  Duration: {result.get('duration', 0):.2f} seconds")
            
            # Analyze sections
            sections = result.get("completed_sections", [])
            print(f"\n📊 SECTION ANALYSIS:")
            print(f"  Total sections: {len(sections)}")
            
            if sections:
                # Calculate statistics
                total_iterations = sum(s.get('iterations', 1) for s in sections)
                avg_quality = sum(s.get('quality_score', 0) for s in sections) / len(sections)
                
                print(f"  Average quality score: {avg_quality:.2f}")
                print(f"  Total iterations: {total_iterations}")
                print(f"  Average iterations per section: {total_iterations/len(sections):.1f}")
                
                # Show per-section details
                print(f"\n  SECTION DETAILS:")
                for s in sections:
                    section_key = s.get('section_key', 'unknown')
                    quality = s.get('quality_score', 0)
                    iterations = s.get('iterations', 1)
                    source = s.get('source', 'unknown')
                    
                    # Quality indicator
                    if quality >= 0.8:
                        indicator = "🟢"
                    elif quality >= 0.6:
                        indicator = "🟡"
                    else:
                        indicator = "🔴"
                    
                    print(f"    {indicator} {section_key:15} - Quality: {quality:.2f}, Iterations: {iterations}, Source: {source}")
                    
                    # Show feedback if available
                    feedback = s.get('quality_feedback', {})
                    if feedback and feedback.get('needs_improvement'):
                        print(f"       Feedback: {', '.join(feedback['needs_improvement'])}")
            
            # Show sample of report
            report = result.get("final_report", "")
            if report:
                print(f"\n📄 REPORT PREVIEW (first 500 chars):")
                print("-" * 40)
                print(report[:500])
                if len(report) > 500:
                    print("... [truncated]")
                print("-" * 40)
                print(f"Total report length: {len(report)} characters")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

async def compare_modes():
    """Compare different modes side by side"""
    
    print("\n" + "=" * 60)
    print("COMPARING REPORT GENERATION MODES")
    print("=" * 60)
    
    inspection_id = "test_comparison_456"
    
    # Test 1: Parallel mode (no quality loop)
    print("\n1️⃣ PARALLEL MODE (No Quality Loop):")
    os.environ['USE_SUBGRAPH_REPORT'] = 'false'
    os.environ['USE_PARALLEL_REPORT'] = 'true'
    
    try:
        from langgraph_report_writer_parallel import run_parallel_report
        import time
        
        start = time.time()
        result = run_parallel_report(inspection_id, [])
        duration_parallel = time.time() - start
        
        print(f"  ✅ Duration: {duration_parallel:.2f} seconds")
        print(f"  📊 Sections: {len(result.get('sections', []))}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        duration_parallel = None
    
    # Test 2: Subgraph mode (with quality loop)
    print("\n2️⃣ SUBGRAPH MODE (With Quality Loop):")
    os.environ['USE_SUBGRAPH_REPORT'] = 'true'
    os.environ['ENABLE_QUALITY_LOOP'] = 'true'
    
    try:
        from langgraph_report_writer_subgraph import generate_report_with_subgraph
        
        result = await generate_report_with_subgraph(inspection_id)
        duration_subgraph = result.get('duration', 0)
        sections = result.get('completed_sections', [])
        
        print(f"  ✅ Duration: {duration_subgraph:.2f} seconds")
        print(f"  📊 Sections: {len(sections)}")
        
        if sections:
            avg_quality = sum(s.get('quality_score', 0) for s in sections) / len(sections)
            total_iterations = sum(s.get('iterations', 1) for s in sections)
            print(f"  🎯 Average Quality: {avg_quality:.2f}")
            print(f"  🔄 Total Iterations: {total_iterations}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        duration_subgraph = None
    
    # Comparison
    if duration_parallel and duration_subgraph:
        print("\n📊 COMPARISON:")
        print(f"  Speed difference: {duration_subgraph - duration_parallel:.2f} seconds")
        print(f"  Quality improvement: Enabled with retry logic")
        print(f"  Trade-off: {(duration_subgraph/duration_parallel - 1)*100:.1f}% slower for better quality")

if __name__ == "__main__":
    print("🚀 Starting subgraph tests...\n")
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'QDRANT_URL', 'QDRANT_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"⚠️ Warning: Missing environment variables: {missing}")
        print("   Some features may not work properly\n")
    else:
        print("✅ All required environment variables found\n")
    
    # Run basic test
    print("=" * 60)
    print("PART 1: Basic Subgraph Test")
    print("=" * 60)
    asyncio.run(test_subgraph())
    
    # Run comparison
    print("\n" + "=" * 60)
    print("PART 2: Mode Comparison")
    print("=" * 60)
    asyncio.run(compare_modes())
    
    print("\n✅ All tests complete!")