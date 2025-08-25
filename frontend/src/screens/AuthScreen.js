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
    
    // Always ensure user has inspector role
    const { role, error: roleError } = await getUserRole(user.uid);
    if (!role || role !== 'inspector') {
      // Auto-assign inspector role (for new users or users without proper role)
      const { error: setRoleError } = await setUserRole(user.uid, 'inspector');
      if (setRoleError) {
        console.error('Failed to set role:', setRoleError);
        // Continue anyway - user can still use the app
      } else {
        console.log('Inspector role assigned successfully');
      }
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
          className="w-full bg-emerald-600 text-white py-3 rounded-lg font-semibold hover:bg-emerald-700 disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
        >
          {loading ? 'Signing in…' : 'Continue with Google'}
        </button>
      </div>
    </div>
  );
};

export default AuthScreen;


