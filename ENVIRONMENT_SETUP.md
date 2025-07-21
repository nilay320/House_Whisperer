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

Great catch! This error means you are using the Firestore functions `setDoc` and `getDoc` in your `firebase.js` file, but you haven’t imported them from the Firebase SDK.

---

## 🛠️ **How to Fix**

Add these imports at the top of your `frontend/src/services/firebase.js` file:

```js
import { setDoc, getDoc, doc } from 'firebase/firestore';
```

- `setDoc` and `getDoc` are used for writing/reading documents.
- `doc` is used to create a reference to a specific document (which you also need for your code to work correctly).

---

## 📝 **Also Update the Code (if needed):**

Change:
```js
const userRef = collection(db, 'users').doc(userCredential.user.uid);
await setDoc(userRef, { role: role });
```
to:
```js
const userRef = doc(db, 'users', userCredential.user.uid);
await setDoc(userRef, { role: role });
```

And:
```js
const userRef = collection(db, 'users').doc(userId);
const docSnap = await getDoc(userRef);
```
to:
```js
const userRef = doc(db, 'users', userId);
const docSnap = await getDoc(userRef);
```

---

## ✅ **Summary of What to Do**
1. Add the import:
   ```js
   import { setDoc, getDoc, doc } from 'firebase/firestore';
   ```
2. Use `doc(db, 'users', userId)` instead of `collection(db, 'users').doc(userId)`

---

Would you like me to make these changes for you? 

---

## 🚀 **Step 1: Create a Firebase Project**

1. **Go to the [Firebase Console](https://console.firebase.google.com/).**
2. **Click “Add project”** (or “Create a project”).
3. **Enter a project name** (e.g., `house-whisperer-ai`).
4. **(Optional) Enable Google Analytics** (not required for your POC).
5. **Click “Create project”** and wait for setup to finish.

---

## 🛠️ **Step 2: Register a Web App**

1. In your Firebase project dashboard, click the **web (“</>”) icon** to add a web app.
2. **Give your app a nickname** (e.g., `house-whisperer-web`).
3. **(Optional) Set up Firebase Hosting** (not required for local dev).
4. **Click “Register app”**.

---

## 🔑 **Step 3: Get Your Firebase Config**

After registering your web app, you’ll see a code snippet like this:

```js
<code_block_to_apply_changes_from>
```

---

## 🧩 **Step 4: Enable Authentication Methods**

1. In the Firebase Console, go to **Build > Authentication**.
2. Click **“Get started”**.
3. Go to the **Sign-in method** tab.
4. **Enable “Email/Password”** (and “Google” if you want).
5. Save changes.

---

## 📝 **Step 5: Create `.env.local` in Your `frontend/` Directory**

1. In your project, go to the `frontend/` directory.
2. Create a file named `.env.local` (if it doesn’t exist).
3. Copy your Firebase config into it, like this:

```env
REACT_APP_FIREBASE_API_KEY=AIzaSyA...your-key...
REACT_APP_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your-project-id
REACT_APP_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456

# Backend API URL (for local development)
REACT_APP_BACKEND_API_URL=http://localhost:8000
```

**Note:**  
- The variable names must start with `REACT_APP_` for Create React App to use them.
- Do **not** commit `.env.local` to git (it’s in `.gitignore` by default).

---

## 🏁 **Step 6: Start Your App**

```bash
cd frontend
npm install
npm start
```

- Open [http://localhost:3000](http://localhost:3000) in your browser.
- You should now be able to sign up, log in, and use Firebase features!

---

## ✅ **You’re Ready!**

- You do **not** need to run Firebase locally—your app will connect to the cloud.
- If you want to use Firestore or Storage, you can enable those in the Firebase Console as well.

---

**Let me know if you want screenshots or run into any issues!** 