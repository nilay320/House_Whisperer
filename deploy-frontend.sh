#!/bin/bash

# 🚀 Deploy Home Inspector AI Frontend to Vercel
# This script deploys the frontend with proper environment variables

set -e  # Exit on any error

echo "🚀 Deploying Home Inspector AI Frontend to Vercel..."

# Check if we're in the right directory
if [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

# Change to frontend directory
cd frontend

echo "📦 Installing dependencies..."
npm install

echo "🔧 Building the application..."
npm run build

echo "☁️ Deploying to Vercel..."

# Check if vercel is installed
if ! command -v vercel &> /dev/null; then
    echo "⚠️  Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Deploy to Vercel
vercel --prod

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Set environment variables in Vercel Dashboard:"
echo "   - REACT_APP_FIREBASE_API_KEY"
echo "   - REACT_APP_FIREBASE_AUTH_DOMAIN" 
echo "   - REACT_APP_FIREBASE_PROJECT_ID"
echo "   - REACT_APP_FIREBASE_STORAGE_BUCKET"
echo "   - REACT_APP_FIREBASE_MESSAGING_SENDER_ID"
echo "   - REACT_APP_FIREBASE_APP_ID"
echo "   - REACT_APP_BACKEND_API_URL"
echo ""
echo "2. Redeploy after setting environment variables:"
echo "   vercel --prod --force"
echo ""
echo "3. Test your deployment!"