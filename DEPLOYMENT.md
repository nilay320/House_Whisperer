# 🚀 Deployment Guide: House Whisperer AI

Complete guide to deploy your full-stack Home Inspection AI Assistant with serverless architecture.

## 📋 Prerequisites

- [Node.js](https://nodejs.org/) (v16 or higher)
- [Vercel CLI](https://vercel.com/cli) (`npm i -g vercel`)
- [Expo CLI](https://docs.expo.dev/get-started/installation/) (`npm i -g @expo/cli`)
- [EAS CLI](https://docs.expo.dev/eas/) (`npm i -g eas-cli`)
- Firebase project (see `firebase-config.md`)

## 🔥 Step 1: Firebase Setup

### 1.1 Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create project: `house-whisperer-ai`
3. Enable Authentication (Email/Password + Google)
4. Enable Storage (start in test mode)
5. Get your Firebase config

### 1.2 Set Up Security Rules
```javascript
// storage.rules
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /users/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /inspections/{inspectionId}/{allPaths=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## 🌐 Step 2: Web App Deployment (Vercel)

### 2.1 Prepare Environment Variables
Create `.env.local` in `frontend/`:
```bash
REACT_APP_FIREBASE_API_KEY=your-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=house-whisperer-ai.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=house-whisperer-ai
REACT_APP_FIREBASE_STORAGE_BUCKET=house-whisperer-ai.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456
REACT_APP_BACKEND_API_URL=https://your-backend-api.com
```

### 2.2 Deploy to Vercel

#### Option A: Vercel CLI
```bash
cd frontend
npm install
vercel login
vercel --prod
```

#### Option B: GitHub Integration
1. Push code to GitHub
2. Connect repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy automatically

### 2.3 Configure Vercel Environment Variables
In Vercel dashboard → Project Settings → Environment Variables:
```
REACT_APP_FIREBASE_API_KEY=@firebase-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=@firebase-auth-domain
REACT_APP_FIREBASE_PROJECT_ID=@firebase-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=@firebase-storage-bucket
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=@firebase-messaging-sender-id
REACT_APP_FIREBASE_APP_ID=@firebase-app-id
REACT_APP_BACKEND_API_URL=@backend-api-url
```

## 📱 Step 3: Mobile App Deployment (Expo)

### 3.1 Install Dependencies
```bash
cd mobile-app
npm install
```

### 3.2 Configure EAS
```bash
eas login
eas build:configure
```

### 3.3 Set Environment Variables
Create `.env` in `mobile-app/`:
```bash
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=house-whisperer-ai.firebaseapp.com
FIREBASE_PROJECT_ID=house-whisperer-ai
FIREBASE_STORAGE_BUCKET=house-whisperer-ai.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456
BACKEND_API_URL=https://your-backend-api.com
```

### 3.4 Build and Deploy

#### Development Build
```bash
eas build --platform all --profile development
```

#### Production Build
```bash
eas build --platform all --profile production
```

#### Submit to App Stores
```bash
# iOS App Store
eas submit --platform ios

# Google Play Store
eas submit --platform android
```

## 🔧 Step 4: Backend Integration

### 4.1 Update Backend API
Ensure your FastAPI backend can:
- Accept Firebase ID tokens for authentication
- Process files from Firebase Storage URLs
- Return AI-generated reports

### 4.2 CORS Configuration
```python
# In your FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-vercel-app.vercel.app",
        "https://your-expo-app.expo.dev"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Step 5: Testing

### 5.1 Web App Testing
1. Visit your Vercel deployment URL
2. Test authentication flow
3. Test PDF upload functionality
4. Test chatbot widget
5. Verify Firebase integration

### 5.2 Mobile App Testing
1. Install Expo Go on your device
2. Scan QR code from `expo start`
3. Test voice recording
4. Test photo capture
5. Test file uploads to Firebase

## 📊 Step 6: Monitoring

### 6.1 Vercel Analytics
- Enable Vercel Analytics in dashboard
- Monitor performance and errors
- Track user interactions

### 6.2 Firebase Analytics
```javascript
// Add to your apps
import { getAnalytics, logEvent } from "firebase/analytics";

const analytics = getAnalytics(app);
logEvent(analytics, "app_opened");
```

### 6.3 Error Tracking
```javascript
// Add Sentry or similar
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-sentry-dsn",
  environment: process.env.NODE_ENV,
});
```

## 🔐 Step 7: Security

### 7.1 Firebase Security Rules
Update storage rules for production:
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /inspections/{inspectionId}/{allPaths=**} {
      allow read, write: if request.auth != null 
        && request.auth.uid == resource.metadata.userId;
    }
  }
}
```

### 7.2 Environment Variables
- Never commit `.env` files
- Use Vercel/Expo environment variables
- Rotate API keys regularly

## 🚀 Step 8: CI/CD Pipeline

### 8.1 GitHub Actions (Optional)
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: cd frontend && npm install && npm run build
      - uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

## 📈 Step 9: Performance Optimization

### 9.1 Web App
- Enable Vercel Edge Functions
- Use React.lazy() for code splitting
- Optimize images with next/image
- Enable service worker for caching

### 9.2 Mobile App
- Use Expo Updates for OTA updates
- Optimize bundle size
- Enable Hermes engine
- Use FastImage for images

## 🆘 Troubleshooting

### Common Issues

**Web App Issues:**
- Firebase config not loading: Check environment variables
- CORS errors: Update backend CORS settings
- Build failures: Check Node.js version compatibility

**Mobile App Issues:**
- EAS build failures: Check app.config.js syntax
- Firebase not working: Verify config in app.config.js
- Permission errors: Check plugin configurations

**Firebase Issues:**
- Storage upload fails: Check security rules
- Auth not working: Verify domain in Firebase console
- Quota exceeded: Upgrade Firebase plan

## ✅ Success Checklist

- [ ] Firebase project created and configured
- [ ] Web app deployed to Vercel
- [ ] Mobile app built with EAS
- [ ] Environment variables set correctly
- [ ] Authentication working on both platforms
- [ ] File upload to Firebase working
- [ ] Backend API integrated
- [ ] Security rules implemented
- [ ] Monitoring and analytics enabled
- [ ] Performance optimized
- [ ] Error tracking configured

## 🎉 Deployment Complete!

Your full-stack Home Inspection AI Assistant is now deployed with:
- ✅ Serverless web app on Vercel
- ✅ Mobile app ready for app stores
- ✅ Firebase authentication and storage
- ✅ Backend API integration
- ✅ Production-ready security

**Next Steps:**
1. Monitor performance and errors
2. Gather user feedback
3. Iterate and improve features
4. Scale as needed 