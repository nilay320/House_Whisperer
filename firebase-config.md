# Firebase Configuration Guide

## 🔥 Firebase Project Setup

### 1. Create Firebase Project
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Name: `house-whisperer-ai`
4. Enable Google Analytics (optional)
5. Click "Create project"

### 2. Enable Authentication
1. In Firebase Console, go to "Authentication" → "Sign-in method"
2. Enable "Email/Password"
3. Enable "Google" (add your domain to authorized domains)
4. Configure OAuth consent screen if needed

### 3. Enable Storage
1. Go to "Storage" → "Get started"
2. Choose "Start in test mode" (we'll add security rules later)
3. Select a location (choose closest to your users)

### 4. Security Rules for Storage
```javascript
// storage.rules
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Allow authenticated users to read/write their own files
    match /users/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow authenticated users to upload inspection reports
    match /inspections/{inspectionId}/{allPaths=**} {
      allow read, write: if request.auth != null;
    }
    
    // Allow public read access to shared reports (optional)
    match /public/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```

### 5. Get Firebase Config
1. Go to Project Settings (gear icon)
2. Scroll to "Your apps" section
3. Add Web app: `house-whisperer-web`
4. Add Android app: `house-whisperer-mobile`
5. Copy the config for each platform

## 📱 Platform-Specific Setup

### Web App Configuration
```javascript
// frontend/src/services/firebase.js
const firebaseConfig = {
  apiKey: "your-api-key",
  authDomain: "house-whisperer-ai.firebaseapp.com",
  projectId: "house-whisperer-ai",
  storageBucket: "house-whisperer-ai.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef123456"
};
```

### Mobile App Configuration
```javascript
// mobile-app/app.json
{
  "expo": {
    "name": "House Whisperer AI",
    "slug": "house-whisperer-mobile",
    "version": "1.0.0",
    "platforms": ["ios", "android"],
    "icon": "./assets/icon.png",
    "splash": {
      "image": "./assets/splash.png",
      "resizeMode": "contain",
      "backgroundColor": "#ffffff"
    },
    "updates": {
      "fallbackToCacheTimeout": 0
    },
    "assetBundlePatterns": [
      "**/*"
    ],
    "ios": {
      "supportsTablet": true,
      "bundleIdentifier": "com.housewhisperer.mobile"
    },
    "android": {
      "adaptiveIcon": {
        "foregroundImage": "./assets/adaptive-icon.png",
        "backgroundColor": "#FFFFFF"
      },
      "package": "com.housewhisperer.mobile"
    },
    "web": {
      "favicon": "./assets/favicon.png"
    },
    "plugins": [
      [
        "expo-av",
        {
          "microphonePermission": "Allow House Whisperer to access your microphone."
        }
      ],
      [
        "expo-camera",
        {
          "cameraPermission": "Allow House Whisperer to access your camera."
        }
      ],
      [
        "expo-image-picker",
        {
          "photosPermission": "Allow House Whisperer to access your photos."
        }
      ]
    ]
  }
}
```

## 🔐 Environment Variables

### Web App (.env.local)
```bash
REACT_APP_FIREBASE_API_KEY=your-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=house-whisperer-ai.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=house-whisperer-ai
REACT_APP_FIREBASE_STORAGE_BUCKET=house-whisperer-ai.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456
REACT_APP_BACKEND_API_URL=https://your-backend-api.com
```

### Mobile App (app.config.js)
```javascript
export default {
  expo: {
    name: "House Whisperer AI",
    slug: "house-whisperer-mobile",
    version: "1.0.0",
    extra: {
      firebaseApiKey: process.env.FIREBASE_API_KEY,
      firebaseAuthDomain: process.env.FIREBASE_AUTH_DOMAIN,
      firebaseProjectId: process.env.FIREBASE_PROJECT_ID,
      firebaseStorageBucket: process.env.FIREBASE_STORAGE_BUCKET,
      firebaseMessagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID,
      firebaseAppId: process.env.FIREBASE_APP_ID,
      backendApiUrl: process.env.BACKEND_API_URL,
    },
  },
};
``` 