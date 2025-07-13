# 🌐 Vercel Deployment Guide

Complete guide to deploy your React app to Vercel with Firebase integration and environment variables.

## 🚀 Quick Deploy

### **Option 1: Vercel CLI**
```bash
cd frontend
npm install
vercel login
vercel --prod
```

### **Option 2: GitHub Integration**
1. Push your code to GitHub
2. Connect your repository to Vercel
3. Configure environment variables (see below)
4. Deploy automatically

## 🔧 Environment Variables Setup

### **Step 1: Get Firebase Configuration**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to Project Settings (gear icon)
4. Scroll to "Your apps" section
5. Copy the config values

### **Step 2: Set Environment Variables in Vercel**

#### **Via Vercel Dashboard**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Add each variable:

```bash
# Firebase Configuration
REACT_APP_FIREBASE_API_KEY=your-api-key-here
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Backend API URL
REACT_APP_BACKEND_API_URL=https://your-backend-api.com
```

#### **Via Vercel CLI**
```bash
# Set environment variables
vercel env add REACT_APP_FIREBASE_API_KEY
vercel env add REACT_APP_FIREBASE_AUTH_DOMAIN
vercel env add REACT_APP_FIREBASE_PROJECT_ID
vercel env add REACT_APP_FIREBASE_STORAGE_BUCKET
vercel env add REACT_APP_FIREBASE_MESSAGING_SENDER_ID
vercel env add REACT_APP_FIREBASE_APP_ID
vercel env add REACT_APP_BACKEND_API_URL
```

### **Step 3: Environment Variable Best Practices**

#### **Security**
- ✅ Never commit `.env` files to version control
- ✅ Use Vercel's environment variable system
- ✅ Rotate API keys regularly
- ✅ Use different keys for development/production

#### **Naming Convention**
```bash
# React apps require REACT_APP_ prefix
REACT_APP_FIREBASE_API_KEY=your-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-domain
```

#### **Validation**
The Firebase service includes validation:
```javascript
// This will throw an error if any required variables are missing
const validateFirebaseConfig = () => {
  const requiredVars = [
    'REACT_APP_FIREBASE_API_KEY',
    'REACT_APP_FIREBASE_AUTH_DOMAIN',
    // ... other variables
  ];
  
  const missingVars = requiredVars.filter(varName => !process.env[varName]);
  
  if (missingVars.length > 0) {
    throw new Error(`Missing Firebase configuration: ${missingVars.join(', ')}`);
  }
};
```

## 🔄 Redeploy After Environment Variable Changes

### **Automatic Redeploy**
- Environment variables are automatically applied to new deployments
- Existing deployments continue using old variables until redeployed

### **Manual Redeploy**
```bash
# Redeploy with new environment variables
vercel --prod

# Or trigger via GitHub
git commit --allow-empty -m "Trigger redeploy"
git push origin main
```

### **Force Redeploy**
```bash
# Force a fresh deployment
vercel --force --prod
```

## 🔐 Secure Firebase Configuration

### **API Key Restrictions**
1. Go to Firebase Console → Project Settings → General
2. Scroll to "Your apps" section
3. Click on your web app
4. Add authorized domains:
   ```
   your-app.vercel.app
   your-app-git-username.vercel.app
   localhost (for development)
   ```

### **Firebase Security Rules**
Deploy the security rules from `firebase-security-rules.md`:
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize Firebase (if not already done)
firebase init

# Deploy security rules
firebase deploy --only storage,firestore:rules
```

## 🧪 Testing Environment Variables

### **Local Testing**
```bash
# Create .env.local for local development
cp frontend/env.example frontend/.env.local
# Edit .env.local with your actual values

# Start development server
cd frontend
npm start
```

### **Production Testing**
```bash
# Deploy to preview
vercel

# Test the preview URL
# Check browser console for Firebase initialization messages
```

### **Environment Variable Debugging**
```javascript
// Add this to your component to debug
console.log('Firebase Config:', {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY ? '✅ Set' : '❌ Missing',
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN ? '✅ Set' : '❌ Missing',
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID ? '✅ Set' : '❌ Missing',
  // ... other variables
});
```

## 📊 Monitoring & Analytics

### **Vercel Analytics**
1. Go to Vercel Dashboard → Project Settings → Analytics
2. Enable Vercel Analytics
3. Monitor performance and errors

### **Firebase Analytics**
```javascript
// Add to your app
import { getAnalytics, logEvent } from "firebase/analytics";

const analytics = getAnalytics(app);
logEvent(analytics, "app_opened");
```

## 🆘 Troubleshooting

### **Common Issues**

#### **Environment Variables Not Loading**
```bash
# Check if variables are set
vercel env ls

# Redeploy to apply changes
vercel --prod
```

#### **Firebase Initialization Errors**
```javascript
// Check browser console for:
// - Missing environment variables
// - Invalid Firebase config
// - Network connectivity issues
```

#### **CORS Errors**
```javascript
// In Firebase Console → Authentication → Settings → Authorized domains
// Add your Vercel domain:
// your-app.vercel.app
```

#### **Build Failures**
```bash
# Check build logs
vercel logs

# Common fixes:
# - Ensure all environment variables are set
# - Check for syntax errors in code
# - Verify Firebase configuration
```

## ✅ Deployment Checklist

- [ ] Firebase project created and configured
- [ ] Environment variables set in Vercel
- [ ] Firebase security rules deployed
- [ ] Authorized domains configured
- [ ] App deployed to Vercel
- [ ] Authentication working
- [ ] File uploads working
- [ ] Error monitoring configured
- [ ] Analytics enabled

## 🎉 Success!

Your React app is now deployed on Vercel with:
- ✅ Secure Firebase integration
- ✅ Environment variables properly configured
- ✅ Automatic deployments from GitHub
- ✅ Performance monitoring
- ✅ Error tracking

**Next Steps:**
1. Test all functionality
2. Set up monitoring and alerts
3. Configure custom domain (optional)
4. Set up CI/CD pipeline 