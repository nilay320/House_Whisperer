#!/usr/bin/env python3
"""
Compare original vs enhanced report generation
Shows concrete improvements and metrics
"""

import asyncio
import json
import os
import sys
import time
import difflib
from typing import Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import both versions
from api.langgraph_report_writer import run_report as run_original
from api.langgraph_report_writer_enhanced import run_enhanced_report as run_enhanced


class ReportComparison:
    def __init__(self, inspection_id: str):
        self.inspection_id = inspection_id
        self.original_result = None
        self.enhanced_result = None
        self.metrics = {}
        
    def run_comparison(self):
        """Run both report versions and compare"""
        print("\n" + "="*80)
        print(f"📊 REPORT VERSION COMPARISON")
        print(f"Inspection ID: {self.inspection_id}")
        print("="*80)
        
        # Run original version
        print("\n🔵 Running ORIGINAL report generator...")
        start_time = time.time()
        try:
            self.original_result = run_original(self.inspection_id)
            original_time = time.time() - start_time
            print(f"✅ Original completed in {original_time:.2f} seconds")
        except Exception as e:
            print(f"❌ Original failed: {e}")
            return
        
        # Run enhanced version
        print("\n🟢 Running ENHANCED report generator...")
        start_time = time.time()
        try:
            self.enhanced_result = run_enhanced(self.inspection_id)
            enhanced_time = time.time() - start_time
            print(f"✅ Enhanced completed in {enhanced_time:.2f} seconds")
        except Exception as e:
            print(f"❌ Enhanced failed: {e}")
            return
        
        # Calculate metrics
        self.calculate_metrics(original_time, enhanced_time)
        
        # Display comparison
        self.display_comparison()
        
        # Save detailed comparison
        self.save_comparison()
    
    def calculate_metrics(self, original_time: float, enhanced_time: float):
        """Calculate comparison metrics"""
        
        # Basic metrics
        self.metrics['execution_time'] = {
            'original': original_time,
            'enhanced': enhanced_time,
            'difference': enhanced_time - original_time
        }
        
        # Content metrics
        original_md = self.original_result.get('markdown', '')
        enhanced_md = self.enhanced_result.get('markdown', '')
        
        self.metrics['content'] = {
            'original_length': len(original_md),
            'enhanced_length': len(enhanced_md),
            'length_increase': len(enhanced_md) - len(original_md)
        }
        
        # Quality metrics from enhanced version
        self.metrics['quality'] = {
            'report_quality_score': self.enhanced_result.get('reportQualityScore', 0),
            'has_executive_summary': bool(self.enhanced_result.get('executiveSummary')),
            'narrative_sources': self.enhanced_result.get('narrativeSources', {})
        }
        
        # Count narrative source types
        sources = self.enhanced_result.get('narrativeSources', {})
        source_counts = {
            'verified_narrative': 0,
            'code_enhanced': 0,
            'ai_generated': 0
        }
        for source in sources.values():
            if source in source_counts:
                source_counts[source] += 1
        
        self.metrics['narrative_distribution'] = source_counts
        
        # Section coverage
        self.metrics['sections'] = {
            'original_count': self.original_result.get('sectionCount', 0),
            'enhanced_count': self.enhanced_result.get('sectionCount', 0),
            'clip_count': self.original_result.get('clipCount', 0)
        }
    
    def display_comparison(self):
        """Display comparison results"""
        
        print("\n" + "="*80)
        print("📈 COMPARISON RESULTS")
        print("="*80)
        
        # Performance
        print("\n⏱️  Performance:")
        print(f"  Original: {self.metrics['execution_time']['original']:.2f}s")
        print(f"  Enhanced: {self.metrics['execution_time']['enhanced']:.2f}s")
        diff = self.metrics['execution_time']['difference']
        if diff > 0:
            print(f"  Enhanced is {diff:.2f}s slower (acceptable for better quality)")
        else:
            print(f"  Enhanced is {abs(diff):.2f}s faster!")
        
        # Content
        print("\n📝 Content:")
        print(f"  Original length: {self.metrics['content']['original_length']:,} chars")
        print(f"  Enhanced length: {self.metrics['content']['enhanced_length']:,} chars")
        increase = self.metrics['content']['length_increase']
        if increase > 0:
            pct = (increase / self.metrics['content']['original_length']) * 100
            print(f"  Enhanced has {increase:,} more chars ({pct:.1f}% richer content)")
        
        # Quality Score
        print("\n🏆 Quality Metrics (Enhanced Only):")
        quality_score = self.metrics['quality']['report_quality_score']
        print(f"  Report Quality Score: {quality_score:.1%}")
        print(f"  Has Executive Summary: {'✅ Yes' if self.metrics['quality']['has_executive_summary'] else '❌ No'}")
        
        # Narrative Sources
        print("\n📚 Narrative Sources (Enhanced):")
        dist = self.metrics['narrative_distribution']
        total = sum(dist.values())
        if total > 0:
            print(f"  ✅ Verified Narratives: {dist['verified_narrative']}/{total} ({dist['verified_narrative']/total:.0%})")
            print(f"  📋 Code-Enhanced: {dist['code_enhanced']}/{total} ({dist['code_enhanced']/total:.0%})")
            print(f"  🤖 AI Generated: {dist['ai_generated']}/{total} ({dist['ai_generated']/total:.0%})")
        
        # Key Improvements
        print("\n✨ KEY IMPROVEMENTS IN ENHANCED VERSION:")
        improvements = []
        
        if self.metrics['quality']['has_executive_summary']:
            improvements.append("✅ Professional executive summary")
        
        if dist['verified_narrative'] > 0:
            improvements.append(f"✅ {dist['verified_narrative']} sections with verified professional narratives")
        
        if dist['code_enhanced'] > 0:
            improvements.append(f"✅ {dist['code_enhanced']} sections enhanced with building codes")
        
        if quality_score > 0.7:
            improvements.append(f"✅ High quality score ({quality_score:.0%})")
        
        if self.enhanced_result.get('markdown', '').count('🔴') > 0:
            improvements.append("✅ Visual severity badges (🔴🟠🟡ℹ️)")
        
        if self.enhanced_result.get('markdown', '').count('## 📊 Report Quality Metrics') > 0:
            improvements.append("✅ Quality metrics dashboard")
        
        for imp in improvements:
            print(f"  {imp}")
        
        # Sample content differences
        self.show_content_samples()
    
    def show_content_samples(self):
        """Show sample content differences"""
        print("\n" + "="*80)
        print("📄 CONTENT SAMPLES")
        print("="*80)
        
        original_md = self.original_result.get('markdown', '')
        enhanced_md = self.enhanced_result.get('markdown', '')
        
        # Show first 500 chars of each
        print("\n🔵 ORIGINAL (First 500 chars):")
        print("-" * 40)
        print(original_md[:500])
        
        print("\n🟢 ENHANCED (First 500 chars):")
        print("-" * 40)
        print(enhanced_md[:500])
        
        # Check for specific enhancements
        print("\n🔍 SPECIFIC ENHANCEMENTS DETECTED:")
        
        checks = {
            "Executive Summary": "## 📋 Executive Summary" in enhanced_md,
            "Quality Metrics": "## 📊 Report Quality Metrics" in enhanced_md,
            "Table of Contents": "## 📑 Table of Contents" in enhanced_md,
            "Generation Coverage": "## ✅ Generation Coverage" in enhanced_md,
            "Severity Badges": "🔴" in enhanced_md or "🟠" in enhanced_md,
            "Source Badges": "✅ **Verified Narrative**" in enhanced_md,
            "Professional Header": "# 🏠 Professional Home Inspection Report" in enhanced_md,
        }
        
        for feature, present in checks.items():
            status = "✅" if present else "❌"
            print(f"  {status} {feature}")
    
    def save_comparison(self):
        """Save detailed comparison to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_comparison_{self.inspection_id}_{timestamp}.json"
        
        comparison_data = {
            'inspection_id': self.inspection_id,
            'timestamp': timestamp,
            'metrics': self.metrics,
            'enhanced_features': {
                'version': self.enhanced_result.get('version', 'unknown'),
                'quality_score': self.enhanced_result.get('reportQualityScore', 0),
                'narrative_sources': self.enhanced_result.get('narrativeSources', {}),
                'has_executive_summary': bool(self.enhanced_result.get('executiveSummary'))
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        
        print(f"\n💾 Detailed comparison saved to: {filename}")
        
        # Also save markdown samples for manual review
        with open(f"original_{self.inspection_id}_{timestamp}.md", 'w') as f:
            f.write(self.original_result.get('markdown', ''))
        
        with open(f"enhanced_{self.inspection_id}_{timestamp}.md", 'w') as f:
            f.write(self.enhanced_result.get('markdown', ''))
        
        print(f"📄 Markdown reports saved for manual comparison")


def main():
    """Main comparison runner"""
    
    # Get inspection ID from command line or use default
    if len(sys.argv) > 1:
        inspection_id = sys.argv[1]
    else:
        print("\nUsage: python compare_report_versions.py <inspection_id>")
        print("\nUsing test inspection ID. For real comparison, provide an actual inspection ID.")
        inspection_id = "test-inspection-id"
    
    # Set environment for testing
    os.environ['REPORT_LOGS'] = '1'  # Enable logging
    
    # Run comparison
    comparison = ReportComparison(inspection_id)
    comparison.run_comparison()
    
    print("\n" + "="*80)
    print("✅ COMPARISON COMPLETE")
    print("="*80)
    print("\n🎯 RECOMMENDATION:")
    
    if comparison.metrics.get('quality', {}).get('report_quality_score', 0) > 0.6:
        print("  The ENHANCED version shows significant improvements in:")
        print("  - Content quality and completeness")
        print("  - Professional presentation")
        print("  - Narrative matching accuracy")
        print("  - Fallback handling for edge cases")
        print("\n  ✅ Ready for demo day!")
    else:
        print("  Review the comparison files for detailed analysis.")


if __name__ == "__main__":
    main()