#!/bin/bash

# 🚀 House Whisperer AI Deployment Script
# This script automates the deployment of both web and mobile applications

set -e  # Exit on any error

echo "🏠 House Whisperer AI - Deployment Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js v16 or higher."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed."
        exit 1
    fi
    
    if ! command -v vercel &> /dev/null; then
        print_warning "Vercel CLI is not installed. Installing..."
        npm install -g vercel
    fi
    
    if ! command -v expo &> /dev/null; then
        print_warning "Expo CLI is not installed. Installing..."
        npm install -g @expo/cli
    fi
    
    if ! command -v eas &> /dev/null; then
        print_warning "EAS CLI is not installed. Installing..."
        npm install -g eas-cli
    fi
    
    print_success "All dependencies are installed!"
}

# Deploy web app to Vercel
deploy_web_app() {
    print_status "Deploying web app to Vercel..."
    
    cd frontend
    
    # Check if .env.local exists
    if [ ! -f .env.local ]; then
        print_warning ".env.local not found. Please create it with your Firebase configuration."
        echo "Example .env.local:"
        echo "REACT_APP_FIREBASE_API_KEY=your-api-key"
        echo "REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com"
        echo "REACT_APP_FIREBASE_PROJECT_ID=your-project-id"
        echo "REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com"
        echo "REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789"
        echo "REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456"
        echo "REACT_APP_BACKEND_API_URL=https://your-backend-api.com"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing web app dependencies..."
    npm install
    
    # Build the app
    print_status "Building web app..."
    npm run build
    
    # Deploy to Vercel
    print_status "Deploying to Vercel..."
    if vercel --prod --yes; then
        print_success "Web app deployed successfully!"
    else
        print_error "Failed to deploy web app to Vercel."
        exit 1
    fi
    
    cd ..
}

# Deploy mobile app with Expo
deploy_mobile_app() {
    print_status "Setting up mobile app for deployment..."
    
    cd mobile-app
    
    # Check if .env exists
    if [ ! -f .env ]; then
        print_warning ".env not found. Please create it with your Firebase configuration."
        echo "Example .env:"
        echo "FIREBASE_API_KEY=your-api-key"
        echo "FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com"
        echo "FIREBASE_PROJECT_ID=your-project-id"
        echo "FIREBASE_STORAGE_BUCKET=your-project.appspot.com"
        echo "FIREBASE_MESSAGING_SENDER_ID=123456789"
        echo "FIREBASE_APP_ID=1:123456789:web:abcdef123456"
        echo "BACKEND_API_URL=https://your-backend-api.com"
        exit 1
    fi
    
    # Install dependencies
    print_status "Installing mobile app dependencies..."
    npm install
    
    # Login to Expo (if not already logged in)
    print_status "Checking Expo login..."
    if ! expo whoami &> /dev/null; then
        print_warning "Please log in to Expo:"
        expo login
    fi
    
    # Configure EAS
    print_status "Configuring EAS..."
    if [ ! -f eas.json ]; then
        eas build:configure
    fi
    
    # Build for development
    print_status "Building mobile app for development..."
    if eas build --platform all --profile development; then
        print_success "Mobile app built successfully!"
    else
        print_error "Failed to build mobile app."
        exit 1
    fi
    
    cd ..
}

# Main deployment function
main() {
    echo ""
    print_status "Starting deployment process..."
    
    # Check dependencies
    check_dependencies
    
    # Deploy web app
    deploy_web_app
    
    # Deploy mobile app
    deploy_mobile_app
    
    echo ""
    print_success "🎉 Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Configure environment variables in Vercel dashboard"
    echo "2. Set up Firebase security rules"
    echo "3. Test both applications"
    echo "4. Submit mobile app to app stores (optional)"
    echo ""
    echo "For detailed instructions, see DEPLOYMENT.md"
}

# Run main function
main "$@" 