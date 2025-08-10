import React, { useState } from 'react';
import { signInWithGoogle, getUserRole, setUserRole } from '../services/firebase';

const AuthScreen = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  // Inspector-only focus: auto-assign inspector on first login (no prompt)

  const handleGoogle = async () => {
    setLoading(true);
    setError('');
    const { user, error } = await signInWithGoogle();
    if (error) {
      setError(error);
      setLoading(false);
      return;
    }
    const { role } = await getUserRole(user.uid);
    if (!role) {
      // Auto-assign inspector for first login
      await setUserRole(user.uid, 'inspector');
    }
    setLoading(false);
    // App will route based on auth state
    window.location.reload();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white rounded-xl shadow p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-center">Sign in to NC Inspector AI</h1>
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

        <button
          onClick={handleGoogle}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Continue with Google'}
        </button>
      </div>
    </div>
  );
};

export default AuthScreen;


