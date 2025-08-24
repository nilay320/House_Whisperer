#!/usr/bin/env python3
"""
Check inspection details in Firestore
"""
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase if not already done
if not firebase_admin._apps:
    firebase_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON', '{}')
    if firebase_json and firebase_json != '{}':
        try:
            service_account = json.loads(firebase_json)
            cred = credentials.Certificate(service_account)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized")
        except Exception as e:
            print(f"❌ Firebase init error: {e}")
            exit(1)

def check_inspection(inspection_id: str):
    """Check inspection details"""
    
    db = firestore.client()
    
    print(f"\n🔍 Checking inspection: {inspection_id}")
    
    # Get inspection document
    inspection_ref = db.collection('inspections').document(inspection_id)
    inspection_doc = inspection_ref.get()
    
    if not inspection_doc.exists:
        print("❌ Inspection not found")
        return
    
    inspection_data = inspection_doc.to_dict()
    print(f"✅ Inspection found")
    print(f"   • Created: {inspection_data.get('createdAt', 'unknown')}")
    print(f"   • Status: {inspection_data.get('status', 'unknown')}")
    
    # Get clips
    clips_ref = inspection_ref.collection('clips')
    clips = list(clips_ref.stream())
    
    print(f"\n📎 Clips: {len(clips)} total")
    
    # Group by section
    sections = {}
    for clip_doc in clips:
        clip_data = clip_doc.to_dict()
        section = clip_data.get('section', 'unknown')
        if section not in sections:
            sections[section] = []
        transcript = clip_data.get('transcript', '')[:100]
        sections[section].append(transcript)
    
    print(f"\n📂 Sections found:")
    for section, transcripts in sections.items():
        print(f"   • {section}: {len(transcripts)} clips")
        if transcripts and transcripts[0]:
            print(f"     Sample: \"{transcripts[0]}...\"")

if __name__ == "__main__":
    inspection_id = "dfe0104e-afe0-40e4-976d-220441f56982"
    check_inspection(inspection_id)