#!/bin/bash
# Script to ingest NC Building Codes when you return

echo "🚀 Starting NC Building Codes ingestion..."
echo "⚠️  This will take approximately 30-45 minutes for 18,441 chunks"
echo ""

cd frontend/scripts
python python_ingest.py NC_Codes

echo ""
echo "✅ Ingestion complete!"
echo "📊 Check the collection status:"
echo "python -c \"from qdrant_client import QdrantClient; import os; from dotenv import load_dotenv; load_dotenv('../.env.local'); client = QdrantClient(url=os.getenv('QDRANT_URL'), api_key=os.getenv('QDRANT_API_KEY')); print(f'Collection has {client.get_collection(\"inspector-standards\").points_count} points')\""