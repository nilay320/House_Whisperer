#!/usr/bin/env python3
"""
Compare original vs enhanced report generation with PDF output
Generates both markdown and PDF for visual comparison
"""

import os
import sys
import time
import json
import markdown
import weasyprint
from datetime import datetime
from typing import Dict, Any, Tuple
from io import BytesIO

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import both versions
from api.langgraph_report_writer import run_report as run_original
from api.langgraph_report_writer_enhanced import run_enhanced_report as run_enhanced


def generate_pdf_from_markdown(markdown_content: str, title: str = "Inspection Report") -> bytes:
    """Convert markdown to PDF using WeasyPrint (matching your existing code)"""
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content, 
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    
    # Create full HTML document with styling (matching your app.py style)
    html_document = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            @page {{
                size: letter;
                margin: 1in;
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                    color: #666;
                }}
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 8.5in;
                margin: 0 auto;
                font-size: 11pt;
            }}
            
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-top: 0;
                page-break-after: avoid;
            }}
            
            h2 {{
                color: #34495e;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 5px;
                margin-top: 24pt;
                page-break-after: avoid;
            }}
            
            h3 {{
                color: #7f8c8d;
                margin-top: 18pt;
                page-break-after: avoid;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                page-break-inside: avoid;
            }}
            
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            
            th {{
                background-color: #f4f4f4;
                font-weight: bold;
            }}
            
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            
            li {{
                margin: 5px 0;
            }}
            
            img {{
                max-width: 100%;
                height: auto;
                display: block;
                margin: 10px 0;
                page-break-inside: avoid;
                page-break-before: auto;
                page-break-after: auto;
            }}
            
            code {{
                background-color: #f4f4f4;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }}
            
            pre {{
                background-color: #f4f4f4;
                padding: 10px;
                border-radius: 5px;
                overflow-x: auto;
                page-break-inside: avoid;
            }}
            
            blockquote {{
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-left: 0;
                color: #666;
                font-style: italic;
            }}
            
            .page-break {{
                page-break-after: always;
            }}
            
            .severity-badge {{
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10pt;
                margin-right: 5px;
            }}
            
            .critical {{ background-color: #e74c3c; color: white; }}
            .major {{ background-color: #e67e22; color: white; }}
            .minor {{ background-color: #f39c12; color: white; }}
            .info {{ background-color: #3498db; color: white; }}
            
            .report-header {{
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 10px;
                margin: 15px 0;
            }}
            
            .metric-card {{
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                border-left: 3px solid #3498db;
            }}
            
            .toc {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            
            .toc ul {{
                list-style-type: none;
                padding-left: 0;
            }}
            
            .toc li {{
                margin: 8px 0;
                padding-left: 20px;
            }}
            
            hr {{
                border: none;
                border-top: 2px solid #ecf0f1;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF using WeasyPrint
    pdf_bytes = weasyprint.HTML(string=html_document).write_pdf()
    return pdf_bytes


class PDFReportComparison:
    def __init__(self, inspection_id: str):
        self.inspection_id = inspection_id
        self.original_result = None
        self.enhanced_result = None
        self.metrics = {}
        self.output_dir = f"pdf_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def run_comparison(self):
        """Run both report versions and generate PDFs"""
        print("\n" + "="*80)
        print(f"📊 PDF REPORT COMPARISON")
        print(f"Inspection ID: {self.inspection_id}")
        print(f"Output Directory: {self.output_dir}")
        print("="*80)
        
        # Generate both versions
        self._generate_reports()
        
        # Generate PDFs
        self._generate_pdfs()
        
        # Calculate metrics
        self._calculate_metrics()
        
        # Display results
        self._display_results()
        
    def _generate_reports(self):
        """Generate both report versions"""
        
        # Original version
        print("\n🔵 Generating ORIGINAL report...")
        start_time = time.time()
        try:
            self.original_result = run_original(self.inspection_id)
            self.original_time = time.time() - start_time
            print(f"✅ Original completed in {self.original_time:.2f}s")
            
            # Save markdown
            with open(f"{self.output_dir}/original.md", 'w') as f:
                f.write(self.original_result.get('markdown', ''))
                
        except Exception as e:
            print(f"❌ Original failed: {e}")
            return
        
        # Enhanced version
        print("\n🟢 Generating ENHANCED report...")
        start_time = time.time()
        try:
            self.enhanced_result = run_enhanced(self.inspection_id)
            self.enhanced_time = time.time() - start_time
            print(f"✅ Enhanced completed in {self.enhanced_time:.2f}s")
            
            # Save markdown
            with open(f"{self.output_dir}/enhanced.md", 'w') as f:
                f.write(self.enhanced_result.get('markdown', ''))
                
        except Exception as e:
            print(f"❌ Enhanced failed: {e}")
            return
    
    def _generate_pdfs(self):
        """Generate PDF versions of both reports"""
        
        print("\n📄 Generating PDFs...")
        
        # Original PDF
        try:
            print("  Creating original.pdf...")
            original_md = self.original_result.get('markdown', '')
            original_pdf = generate_pdf_from_markdown(original_md, "Original Report")
            
            with open(f"{self.output_dir}/original.pdf", 'wb') as f:
                f.write(original_pdf)
            
            print(f"  ✅ Original PDF: {len(original_pdf):,} bytes")
            
        except Exception as e:
            print(f"  ❌ Original PDF failed: {e}")
        
        # Enhanced PDF
        try:
            print("  Creating enhanced.pdf...")
            enhanced_md = self.enhanced_result.get('markdown', '')
            enhanced_pdf = generate_pdf_from_markdown(enhanced_md, "Enhanced Report")
            
            with open(f"{self.output_dir}/enhanced.pdf", 'wb') as f:
                f.write(enhanced_pdf)
            
            print(f"  ✅ Enhanced PDF: {len(enhanced_pdf):,} bytes")
            
        except Exception as e:
            print(f"  ❌ Enhanced PDF failed: {e}")
    
    def _calculate_metrics(self):
        """Calculate comparison metrics"""
        
        original_md = self.original_result.get('markdown', '')
        enhanced_md = self.enhanced_result.get('markdown', '')
        
        # Content metrics
        self.metrics['content'] = {
            'original_length': len(original_md),
            'enhanced_length': len(enhanced_md),
            'length_increase_pct': ((len(enhanced_md) - len(original_md)) / len(original_md) * 100) if original_md else 0
        }
        
        # Feature detection
        self.metrics['features'] = {
            'executive_summary': '## 📋 Executive Summary' in enhanced_md,
            'quality_metrics': '## 📊 Report Quality Metrics' in enhanced_md,
            'table_of_contents': '## 📑 Table of Contents' in enhanced_md,
            'severity_badges': any(badge in enhanced_md for badge in ['🔴', '🟠', '🟡', 'ℹ️']),
            'source_tracking': 'Verified Narrative' in enhanced_md or 'Code-Enhanced' in enhanced_md,
            'professional_header': '# 🏠 Professional Home Inspection Report' in enhanced_md
        }
        
        # Quality metrics
        self.metrics['quality'] = {
            'report_quality_score': self.enhanced_result.get('reportQualityScore', 0),
            'sections': self.enhanced_result.get('sectionCount', 0),
            'clips': self.enhanced_result.get('clipCount', 0)
        }
        
        # Narrative sources
        sources = self.enhanced_result.get('narrativeSources', {})
        source_counts = {'verified_narrative': 0, 'code_enhanced': 0, 'ai_generated': 0}
        for source in sources.values():
            if source in source_counts:
                source_counts[source] += 1
        self.metrics['narrative_sources'] = source_counts
    
    def _display_results(self):
        """Display comparison results"""
        
        print("\n" + "="*80)
        print("📈 COMPARISON RESULTS")
        print("="*80)
        
        # Performance
        print("\n⏱️  Performance:")
        print(f"  Original: {self.original_time:.2f}s")
        print(f"  Enhanced: {self.enhanced_time:.2f}s")
        
        # Content
        print("\n📝 Content:")
        print(f"  Original: {self.metrics['content']['original_length']:,} characters")
        print(f"  Enhanced: {self.metrics['content']['enhanced_length']:,} characters")
        print(f"  Increase: +{self.metrics['content']['length_increase_pct']:.1f}%")
        
        # Features
        print("\n✨ Enhanced Features:")
        for feature, present in self.metrics['features'].items():
            status = "✅" if present else "❌"
            feature_name = feature.replace('_', ' ').title()
            print(f"  {status} {feature_name}")
        
        # Quality
        print("\n🏆 Quality Metrics:")
        quality_score = self.metrics['quality']['report_quality_score']
        print(f"  Report Quality Score: {quality_score:.1%}")
        print(f"  Sections: {self.metrics['quality']['sections']}")
        print(f"  Clips: {self.metrics['quality']['clips']}")
        
        # Narrative Sources
        print("\n📚 Narrative Source Distribution:")
        sources = self.metrics['narrative_sources']
        total = sum(sources.values())
        if total > 0:
            for source, count in sources.items():
                source_name = source.replace('_', ' ').title()
                print(f"  {source_name}: {count}/{total} ({count/total:.0%})")
        
        # File locations
        print("\n" + "="*80)
        print("📁 OUTPUT FILES GENERATED:")
        print("="*80)
        print(f"\n📂 Directory: {self.output_dir}/")
        print("\n📄 Markdown Files:")
        print(f"  • original.md")
        print(f"  • enhanced.md")
        print("\n📑 PDF Files:")
        print(f"  • original.pdf")
        print(f"  • enhanced.pdf")
        
        # Save metrics
        with open(f"{self.output_dir}/metrics.json", 'w') as f:
            json.dump(self.metrics, f, indent=2)
        print("\n📊 Metrics:")
        print(f"  • metrics.json")
        
        print("\n" + "="*80)
        print("💡 VIEWING RECOMMENDATIONS:")
        print("="*80)
        print("\n1. Open PDFs side-by-side:")
        print(f"   open {self.output_dir}/original.pdf")
        print(f"   open {self.output_dir}/enhanced.pdf")
        print("\n2. Or use your PDF viewer's compare feature")
        print("\n3. For markdown diff:")
        print(f"   code -d {self.output_dir}/original.md {self.output_dir}/enhanced.md")


def main():
    """Main runner"""
    
    if len(sys.argv) > 1:
        inspection_id = sys.argv[1]
    else:
        print("\nUsage: python compare_with_pdf.py <inspection_id>")
        print("\nExample: python compare_with_pdf.py abc123")
        inspection_id = input("\nEnter inspection ID: ").strip()
        
        if not inspection_id:
            print("No inspection ID provided. Exiting.")
            return
    
    # Set environment for better output
    os.environ['REPORT_LOGS'] = '1'
    
    # Run comparison
    comparison = PDFReportComparison(inspection_id)
    comparison.run_comparison()
    
    print("\n✅ PDF COMPARISON COMPLETE")
    print(f"\n🎯 Open both PDFs to see the visual improvements:")
    print(f"   open {comparison.output_dir}/*.pdf")


if __name__ == "__main__":
    main()