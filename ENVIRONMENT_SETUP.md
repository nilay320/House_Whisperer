# 🔧 Environment Variables Setup Guide

## Step 2: Update Environment Variables in Both Apps

### **Web App (.env.local)**

Create the file `frontend/.env.local` with your Firebase config:

```bash
# Firebase Configuration
REACT_APP_FIREBASE_API_KEY=your-actual-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
REACT_APP_FIREBASE_APP_ID=your-app-id

# Backend API URL
REACT_APP_BACKEND_API_URL=https://your-backend-api.com
```

### **Mobile App (.env)**

Create the file `mobile-app/.env` with your Firebase config:

```bash
# Firebase Configuration
FIREBASE_API_KEY=your-actual-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
FIREBASE_APP_ID=your-app-id

# Backend API URL
BACKEND_API_URL=https://your-backend-api.com
```

### **How to Get Your Firebase Config Values**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** (gear icon)
4. Scroll to **"Your apps"** section
5. Click on your web app
6. Copy the config values:

```javascript
const firebaseConfig = {
  apiKey: "your-api-key",                    // → REACT_APP_FIREBASE_API_KEY
  authDomain: "your-project.firebaseapp.com", // → REACT_APP_FIREBASE_AUTH_DOMAIN
  projectId: "your-project-id",               // → REACT_APP_FIREBASE_PROJECT_ID
  storageBucket: "your-project.appspot.com",  // → REACT_APP_FIREBASE_STORAGE_BUCKET
  messagingSenderId: "123456789",             // → REACT_APP_FIREBASE_MESSAGING_SENDER_ID
  appId: "1:123456789:web:abcdef123456"      // → REACT_APP_FIREBASE_APP_ID
};
```

### **Commands to Create Files**

```bash
# Web app
echo "# Firebase Configuration
REACT_APP_FIREBASE_API_KEY=your-actual-api-key
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
REACT_APP_FIREBASE_APP_ID=your-app-id
REACT_APP_BACKEND_API_URL=https://your-backend-api.com" > frontend/.env.local

# Mobile app
echo "# Firebase Configuration
FIREBASE_API_KEY=your-actual-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your-messaging-sender-id
FIREBASE_APP_ID=your-app-id
BACKEND_API_URL=https://your-backend-api.com" > mobile-app/.env
```

**Replace all the placeholder values with your actual Firebase config!** 