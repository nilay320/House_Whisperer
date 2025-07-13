import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged
} from 'firebase/auth';
import { getFirestore, collection, addDoc, getDocs, query, where, orderBy } from 'firebase/firestore';
import { getStorage, ref, uploadBytes, getDownloadURL, listAll, deleteObject } from 'firebase/storage';

// Validate Firebase configuration
const validateFirebaseConfig = () => {
  const requiredVars = [
    'REACT_APP_FIREBASE_API_KEY',
    'REACT_APP_FIREBASE_AUTH_DOMAIN',
    'REACT_APP_FIREBASE_PROJECT_ID',
    'REACT_APP_FIREBASE_STORAGE_BUCKET',
    'REACT_APP_FIREBASE_MESSAGING_SENDER_ID',
    'REACT_APP_FIREBASE_APP_ID'
  ];

  const missingVars = requiredVars.filter(varName => !process.env[varName]);
  
  if (missingVars.length > 0) {
    console.error('Missing Firebase environment variables:', missingVars);
    // Don't throw error during build, just log warning
    if (process.env.NODE_ENV === 'development') {
      console.warn('Firebase configuration incomplete. Some features may not work.');
    }
    return false;
  }
  return true;
};

// Firebase configuration from environment variables
const getFirebaseConfig = () => {
  const isValid = validateFirebaseConfig();
  
  if (!isValid) {
    // Return a default config to prevent build failures
    return {
      apiKey: "placeholder",
      authDomain: "placeholder",
      projectId: "placeholder",
      storageBucket: "placeholder",
      messagingSenderId: "placeholder",
      appId: "placeholder"
    };
  }
  
  return {
    apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
    authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
    storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.REACT_APP_FIREBASE_APP_ID
  };
};

// Initialize Firebase with error handling
let app;
try {
  const firebaseConfig = getFirebaseConfig();
  app = initializeApp(firebaseConfig);
  console.log('✅ Firebase initialized successfully');
} catch (error) {
  console.error('❌ Firebase initialization failed:', error.message);
  // In production, you might want to show a user-friendly error
  if (process.env.NODE_ENV === 'production') {
    console.error('Firebase configuration error in production');
  }
}

// Initialize Firebase services
export const auth = getAuth(app);
export const db = getFirestore(app);
export const storage = getStorage(app);

// Authentication functions
export const signInWithEmail = async (email, password) => {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    return { user: userCredential.user, error: null };
  } catch (error) {
    return { user: null, error: error.message };
  }
};

export const signUpWithEmail = async (email, password) => {
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    return { user: userCredential.user, error: null };
  } catch (error) {
    return { user: null, error: error.message };
  }
};

export const signInWithGoogle = async () => {
  try {
    const provider = new GoogleAuthProvider();
    const userCredential = await signInWithPopup(auth, provider);
    return { user: userCredential.user, error: null };
  } catch (error) {
    return { user: null, error: error.message };
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

export const onAuthStateChange = (callback) => {
  return onAuthStateChanged(auth, callback);
};

// Storage functions
export const uploadFile = async (file, path, metadata = {}) => {
  try {
    const storageRef = ref(storage, path);
    const snapshot = await uploadBytes(storageRef, file, metadata);
    const downloadURL = await getDownloadURL(snapshot.ref);
    return { url: downloadURL, error: null };
  } catch (error) {
    return { url: null, error: error.message };
  }
};

export const uploadInspectionReport = async (file, userId, inspectionId) => {
  const path = `inspections/${inspectionId}/reports/${file.name}`;
  const metadata = {
    contentType: file.type,
    customMetadata: {
      userId: userId,
      inspectionId: inspectionId,
      uploadedAt: new Date().toISOString()
    }
  };
  return await uploadFile(file, path, metadata);
};

export const uploadVoiceNote = async (audioBlob, userId, inspectionId, noteId) => {
  const path = `inspections/${inspectionId}/voice-notes/${noteId}.webm`;
  const metadata = {
    contentType: 'audio/webm',
    customMetadata: {
      userId: userId,
      inspectionId: inspectionId,
      noteId: noteId,
      uploadedAt: new Date().toISOString()
    }
  };
  return await uploadFile(audioBlob, path, metadata);
};

export const uploadPhoto = async (file, userId, inspectionId, photoId) => {
  const path = `inspections/${inspectionId}/photos/${photoId}_${file.name}`;
  const metadata = {
    contentType: file.type,
    customMetadata: {
      userId: userId,
      inspectionId: inspectionId,
      photoId: photoId,
      uploadedAt: new Date().toISOString()
    }
  };
  return await uploadFile(file, path, metadata);
};

export const getInspectionFiles = async (inspectionId) => {
  try {
    const inspectionRef = ref(storage, `inspections/${inspectionId}`);
    const result = await listAll(inspectionRef);
    
    const files = [];
    for (const itemRef of result.items) {
      const url = await getDownloadURL(itemRef);
      files.push({
        name: itemRef.name,
        url: url,
        path: itemRef.fullPath
      });
    }
    
    return { files, error: null };
  } catch (error) {
    return { files: [], error: error.message };
  }
};

export const deleteFile = async (filePath) => {
  try {
    const fileRef = ref(storage, filePath);
    await deleteObject(fileRef);
    return { error: null };
  } catch (error) {
    return { error: error.message };
  }
};

// Firestore functions for inspection data
export const createInspection = async (inspectionData) => {
  try {
    const docRef = await addDoc(collection(db, 'inspections'), {
      ...inspectionData,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
    return { id: docRef.id, error: null };
  } catch (error) {
    return { id: null, error: error.message };
  }
};

export const getUserInspections = async (userId) => {
  try {
    const q = query(
      collection(db, 'inspections'),
      where('userId', '==', userId),
      orderBy('createdAt', 'desc')
    );
    const querySnapshot = await getDocs(q);
    
    const inspections = [];
    querySnapshot.forEach((doc) => {
      inspections.push({
        id: doc.id,
        ...doc.data()
      });
    });
    
    return { inspections, error: null };
  } catch (error) {
    return { inspections: [], error: error.message };
  }
};

export default app; 