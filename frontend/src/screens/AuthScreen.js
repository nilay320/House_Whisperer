import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Building2 } from 'lucide-react';
import { signInWithGoogle, getUserRole, onAuthStateChange } from '../services/firebase';
import { setDoc, doc } from 'firebase/firestore';
import { db } from '../services/firebase';
import toast from 'react-hot-toast';

function AuthScreen() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showRoleSelector, setShowRoleSelector] = useState(false);
  const [selectedRole, setSelectedRole] = useState('');
  const [googleUser, setGoogleUser] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  // Check if user is already signed in but needs role selection
  useEffect(() => {
    const unsubscribe = onAuthStateChange(async (user) => {
      setCurrentUser(user);
      if (user) {
        // User is signed in, check if they have a role
        const { role } = await getUserRole(user.uid);
        if (!role) {
          // No role found, show role selector immediately
          setGoogleUser(user);
          setShowRoleSelector(true);
        }
        // If role exists, App.js will handle navigation
      }
    });
    return () => unsubscribe();
  }, []);

  // Only Google sign-in
  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await signInWithGoogle();
      if (result.error) {
        setError(result.error);
        setLoading(false);
        return;
      }
      const user = result.user;
      // Check Firestore for role
      const { role } = await getUserRole(user.uid);
      if (role) {
        // Role exists, proceed to app (let parent handle auth state)
        setLoading(false);
      } else {
        // No role, prompt for role selection
        setGoogleUser(user);
        setShowRoleSelector(true);
        setLoading(false);
      }
    } catch (err) {
      setError('Google sign-in failed');
      setLoading(false);
    }
  };

  // Handle role selection for new Google users
  const handleRoleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedRole || !googleUser) return;
    setLoading(true);
    setError('');
    try {
      const userRef = doc(db, 'users', googleUser.uid);
      await setDoc(userRef, { role: selectedRole }, { merge: true });
      setShowRoleSelector(false);
      setGoogleUser(null);
      setLoading(false);
      // Optionally, trigger a reload or update parent state
      window.location.reload();
    } catch (err) {
      setError('Failed to save role. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6 text-center">Sign in to Home Inspector AI</h2>
        {error && <div className="text-red-500 mb-4 text-center">{error}</div>}
        {showRoleSelector ? (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Welcome! Choose your role</h3>
              <p className="text-sm text-gray-600">This helps us customize your experience</p>
            </div>
            
            <form onSubmit={handleRoleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">Select your role</label>
                <div className="space-y-3">
                  <label className="flex items-center p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
                    <input
                      type="radio"
                      name="role"
                      value="inspector"
                      checked={selectedRole === 'inspector'}
                      onChange={e => setSelectedRole(e.target.value)}
                      className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                    />
                    <div className="ml-3 flex items-center">
                      <Building2 className="w-5 h-5 text-blue-600 mr-2" />
                      <div>
                        <div className="font-medium text-gray-900">Inspector</div>
                        <div className="text-sm text-gray-500">Capture photos and generate reports</div>
                      </div>
                    </div>
                  </label>
                  
                  <label className="flex items-center p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors">
                    <input
                      type="radio"
                      name="role"
                      value="buyer"
                      checked={selectedRole === 'buyer'}
                      onChange={e => setSelectedRole(e.target.value)}
                      className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                    />
                    <div className="ml-3 flex items-center">
                      <User className="w-5 h-5 text-green-600 mr-2" />
                      <div>
                        <div className="font-medium text-gray-900">Buyer</div>
                        <div className="text-sm text-gray-500">Review reports and ask questions</div>
                      </div>
                    </div>
                  </label>
                </div>
              </div>
              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50"
                disabled={loading || !selectedRole}
              >
                {loading ? 'Setting up your account...' : 'Continue'}
              </button>
            </form>
          </div>
        ) : (
          <button
            onClick={handleGoogleSignIn}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center"
            disabled={loading}
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 48 48">
              <g>
                <path fill="#4285F4" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.23l6.85-6.85C36.45 2.36 30.68 0 24 0 14.82 0 6.71 5.1 2.69 12.44l7.98 6.2C12.13 13.13 17.62 9.5 24 9.5z"/>
                <path fill="#34A853" d="M46.1 24.55c0-1.64-.15-3.22-.43-4.74H24v9.01h12.42c-.54 2.9-2.18 5.36-4.65 7.04l7.18 5.59C43.98 37.13 46.1 31.36 46.1 24.55z"/>
                <path fill="#FBBC05" d="M9.67 28.64c-1.13-3.36-1.13-6.97 0-10.33l-7.98-6.2C-1.13 17.1-1.13 30.9 9.67 39.36l7.98-6.2z"/>
                <path fill="#EA4335" d="M24 48c6.48 0 11.92-2.15 15.9-5.86l-7.18-5.59c-2.01 1.35-4.59 2.15-8.72 2.15-6.38 0-11.87-3.63-14.33-8.94l-7.98 6.2C6.71 42.9 14.82 48 24 48z"/>
                <path fill="none" d="M0 0h48v48H0z"/>
              </g>
            </svg>
            {loading ? 'Signing in...' : 'Sign in with Google'}
          </button>
        )}
      </div>
    </div>
  );
}

export default AuthScreen; 