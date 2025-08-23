#!/usr/bin/env python3
"""
Compare original vs enhanced report generation with PDF output
Properly initializes Firebase for standalone execution
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

# Initialize Firebase BEFORE importing report writers
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
def init_firebase():
    """Initialize Firebase Admin SDK for standalone script"""
    try:
        # Check if already initialized
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
    except ValueError:
        # Not initialized, set it up
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                service_account_info = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_info)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized from environment variable")
            except Exception as e:
                print(f"❌ Failed to initialize Firebase from env: {e}")
                # Try loading from file
                init_from_file()
        else:
            init_from_file()
    
    return firestore.client()

def init_from_file():
    """Try to initialize from common credential file locations"""
    possible_paths = [
        'service-account.json',
        '../service-account.json',
        'api/service-account.json',
        os.path.expanduser('~/service-account.json'),
        'credentials/firebase.json',
        '../credentials/firebase.json'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                cred = credentials.Certificate(path)
                firebase_admin.initialize_app(cred)
                print(f"✅ Firebase initialized from file: {path}")
                return
            except Exception as e:
                continue
    
    print("⚠️  Warning: Firebase not initialized. Reports may be empty.")
    print("   Set FIREBASE_SERVICE_ACCOUNT_JSON environment variable or place service-account.json in project root")

# Initialize Firebase first
admin_db = init_firebase()

# Now patch the app module to include admin_db
import api.app as app_module
app_module.admin_db = admin_db
app_module.admin_firestore = firebase_admin.firestore

# Import both versions AFTER Firebase is initialized
from api.langgraph_report_writer import run_report as run_original
from api.langgraph_report_writer_enhanced import run_enhanced_report as run_enhanced


def generate_pdf_from_markdown(markdown_content: str, title: str = "Inspection Report") -> bytes:
    """Convert markdown to PDF using WeasyPrint"""
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content, 
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    
    # Create full HTML document with styling
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


def validate_inspection(inspection_id: str) -> bool:
    """Check if inspection exists and has clips"""
    if not admin_db:
        print("⚠️  Cannot validate inspection without Firebase connection")
        return True  # Try anyway
    
    try:
        # Check if inspection exists
        insp_doc = admin_db.collection('inspections').document(inspection_id).get()
        if not insp_doc.exists:
            print(f"❌ Inspection '{inspection_id}' not found in database")
            return False
        
        # Check for clips
        clips = admin_db.collection('inspections').document(inspection_id).collection('clips').limit(1).get()
        if not clips:
            print(f"⚠️  Inspection exists but has no clips")
            return False
        
        print(f"✅ Found inspection with clips")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not validate inspection: {e}")
        return True  # Try anyway


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
        
        # Validate inspection exists
        if not validate_inspection(self.inspection_id):
            print("\n⚠️  Proceeding anyway, but reports may be empty")
        
        # Generate both versions
        self._generate_reports()
        
        # Only generate PDFs if we have content
        if self.original_result or self.enhanced_result:
            self._generate_pdfs()
            self._calculate_metrics()
            self._display_results()
        else:
            print("\n❌ No report content generated. Check inspection ID and Firebase connection.")
        
    def _generate_reports(self):
        """Generate both report versions"""
        
        # Original version
        print("\n🔵 Generating ORIGINAL report...")
        start_time = time.time()
        try:
            self.original_result = run_original(self.inspection_id)
            self.original_time = time.time() - start_time
            
            if self.original_result.get('markdown'):
                print(f"✅ Original completed in {self.original_time:.2f}s")
                # Save markdown
                with open(f"{self.output_dir}/original.md", 'w') as f:
                    f.write(self.original_result.get('markdown', ''))
            else:
                print(f"⚠️  Original returned no content (check Firebase connection)")
                
        except Exception as e:
            print(f"❌ Original failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Enhanced version
        print("\n🟢 Generating ENHANCED report...")
        start_time = time.time()
        try:
            self.enhanced_result = run_enhanced(self.inspection_id)
            self.enhanced_time = time.time() - start_time
            
            if self.enhanced_result.get('markdown'):
                print(f"✅ Enhanced completed in {self.enhanced_time:.2f}s")
                # Save markdown
                with open(f"{self.output_dir}/enhanced.md", 'w') as f:
                    f.write(self.enhanced_result.get('markdown', ''))
            else:
                print(f"⚠️  Enhanced returned no content")
                
        except Exception as e:
            print(f"❌ Enhanced failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _generate_pdfs(self):
        """Generate PDF versions of both reports"""
        
        print("\n📄 Generating PDFs...")
        
        # Original PDF
        if self.original_result and self.original_result.get('markdown'):
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
        if self.enhanced_result and self.enhanced_result.get('markdown'):
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
        
        original_md = self.original_result.get('markdown', '') if self.original_result else ''
        enhanced_md = self.enhanced_result.get('markdown', '') if self.enhanced_result else ''
        
        if not original_md and not enhanced_md:
            print("⚠️  No content to compare")
            return
        
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
        
        # Quality metrics from enhanced
        if self.enhanced_result:
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
        
        if not self.metrics:
            return
        
        print("\n" + "="*80)
        print("📈 COMPARISON RESULTS")
        print("="*80)
        
        # Performance
        if hasattr(self, 'original_time') and hasattr(self, 'enhanced_time'):
            print("\n⏱️  Performance:")
            print(f"  Original: {self.original_time:.2f}s")
            print(f"  Enhanced: {self.enhanced_time:.2f}s")
        
        # Content
        if 'content' in self.metrics:
            print("\n📝 Content:")
            print(f"  Original: {self.metrics['content']['original_length']:,} characters")
            print(f"  Enhanced: {self.metrics['content']['enhanced_length']:,} characters")
            if self.metrics['content']['original_length'] > 0:
                print(f"  Increase: +{self.metrics['content']['length_increase_pct']:.1f}%")
        
        # Features
        if 'features' in self.metrics:
            print("\n✨ Enhanced Features:")
            for feature, present in self.metrics['features'].items():
                status = "✅" if present else "❌"
                feature_name = feature.replace('_', ' ').title()
                print(f"  {status} {feature_name}")
        
        # Quality
        if 'quality' in self.metrics:
            print("\n🏆 Quality Metrics:")
            quality_score = self.metrics['quality']['report_quality_score']
            print(f"  Report Quality Score: {quality_score:.1%}")
            print(f"  Sections: {self.metrics['quality']['sections']}")
            print(f"  Clips: {self.metrics['quality']['clips']}")
        
        # Narrative Sources
        if 'narrative_sources' in self.metrics:
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
        
        files_generated = []
        for file in ['original.md', 'enhanced.md', 'original.pdf', 'enhanced.pdf']:
            if os.path.exists(f"{self.output_dir}/{file}"):
                files_generated.append(file)
        
        if files_generated:
            print("\n📄 Files:")
            for file in files_generated:
                print(f"  • {file}")
        
        # Save metrics
        if self.metrics:
            with open(f"{self.output_dir}/metrics.json", 'w') as f:
                json.dump(self.metrics, f, indent=2)
            print(f"  • metrics.json")
        
        print("\n" + "="*80)
        print("💡 VIEWING RECOMMENDATIONS:")
        print("="*80)
        
        if 'original.pdf' in files_generated and 'enhanced.pdf' in files_generated:
            print("\n1. Open PDFs side-by-side:")
            print(f"   open {self.output_dir}/original.pdf")
            print(f"   open {self.output_dir}/enhanced.pdf")
            print("\n2. Or open both at once:")
            print(f"   open {self.output_dir}/*.pdf")


def main():
    """Main runner"""
    
    # Check for required environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set. AI features will not work.")
    
    if not os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON') and not os.path.exists('service-account.json'):
        print("⚠️  Warning: Firebase credentials not found.")
        print("   Set FIREBASE_SERVICE_ACCOUNT_JSON or place service-account.json in project root")
    
    if len(sys.argv) > 1:
        inspection_id = sys.argv[1]
    else:
        print("\nUsage: python compare_with_pdf_fixed.py <inspection_id>")
        print("\nExample: python compare_with_pdf_fixed.py 759c864b-6ced-4983-955a-93287857a0a5")
        inspection_id = input("\nEnter inspection ID: ").strip()
        
        if not inspection_id:
            print("No inspection ID provided. Exiting.")
            return
    
    # Set environment for better output
    os.environ['REPORT_LOGS'] = '1'
    
    # Run comparison
    comparison = PDFReportComparison(inspection_id)
    comparison.run_comparison()
    
    print("\n✅ COMPARISON COMPLETE")
    
    # Show how to view results
    pdf_files = [f for f in os.listdir(comparison.output_dir) if f.endswith('.pdf')]
    if pdf_files:
        print(f"\n🎯 View PDFs:")
        print(f"   open {comparison.output_dir}/*.pdf")


if __name__ == "__main__":
    main()