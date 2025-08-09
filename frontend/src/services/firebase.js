// Firebase client initialization and helper APIs
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  onAuthStateChanged,
  signOut,
} from 'firebase/auth';
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
} from 'firebase/firestore';
import { getStorage } from 'firebase/storage';

// Validate required env vars
const REQUIRED_VARS = [
  'REACT_APP_FIREBASE_API_KEY',
  'REACT_APP_FIREBASE_AUTH_DOMAIN',
  'REACT_APP_FIREBASE_PROJECT_ID',
  'REACT_APP_FIREBASE_STORAGE_BUCKET',
  'REACT_APP_FIREBASE_MESSAGING_SENDER_ID',
  'REACT_APP_FIREBASE_APP_ID',
];

const missing = REQUIRED_VARS.filter((k) => !process.env[k]);
if (missing.length) {
  // Log a non-fatal warning in dev; production should have these set
  // eslint-disable-next-line no-console
  console.warn('Firebase configuration incomplete. Missing:', missing);
}

const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY || 'placeholder',
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN || 'placeholder',
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID || 'placeholder',
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET || 'placeholder',
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID || 'placeholder',
  appId: process.env.REACT_APP_FIREBASE_APP_ID || 'placeholder',
};

let app;
try {
  app = initializeApp(firebaseConfig);
  // eslint-disable-next-line no-console
  console.log('✅ Firebase initialized successfully');
} catch (e) {
  // eslint-disable-next-line no-console
  console.error('❌ Firebase init failed', e);
}

export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

export const onAuthStateChange = (cb) => onAuthStateChanged(auth, cb);

export const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(auth, provider);
    return { user: result.user, error: null };
  } catch (error) {
    return { user: null, error: error.message || 'Google sign-in failed' };
  }
};

export const signOutUser = async () => {
  try {
    await signOut(auth);
    return { error: null };
  } catch (error) {
    return { error: error.message };
  }
};

export const getUserRole = async (uid) => {
  try {
    const ref = doc(db, 'users', uid);
    const snap = await getDoc(ref);
    if (snap.exists()) {
      return { role: snap.data().role || null, error: null };
    }
    return { role: null, error: null };
  } catch (error) {
    return { role: null, error: error.message };
  }
};

export const setUserRole = async (uid, role) => {
  try {
    const ref = doc(db, 'users', uid);
    await setDoc(ref, { role }, { merge: true });
    return { error: null };
  } catch (error) {
    return { error: error.message };
  }
};

export default app;


