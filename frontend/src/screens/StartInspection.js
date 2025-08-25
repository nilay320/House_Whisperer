import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../services/api';
import { auth, db } from '../services/firebase';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';

export default function StartInspection() {
  const navigate = useNavigate();
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);

  const start = async () => {
    if (!address.trim()) {
      alert('Please enter a property address');
      return;
    }

    // Ensure user is authenticated
    if (!auth.currentUser) {
      alert('You must be logged in to create an inspection');
      navigate('/');
      return;
    }

    setLoading(true);
    try {
      const insp = await apiPost('/api/inspections', { 
        address: address.trim(),
        ownerUid: auth.currentUser.uid  // Send ownerUid to backend
      });
      
      // Also update in Firestore to ensure consistency
      try {
        await setDoc(doc(db, 'inspections', insp.id), {
          ownerUid: auth.currentUser.uid,
          address: address.trim(),
          createdAt: serverTimestamp(),
          status: 'in_progress',
        }, { merge: true });
      } catch (e) {
        // If Firestore update fails, it's critical since we need ownerUid
        console.error('Failed to set ownerUid in Firestore:', e);
        // Continue anyway since backend might have set it
      }
      navigate(`/inspection/${insp.id}`);
    } catch (error) {
      console.error('Failed to create inspection:', error);
      alert('Failed to create inspection. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white border rounded-lg p-8 shadow-sm max-w-md w-full">
        <h2 className="text-2xl font-bold mb-6 text-gray-900">Start New Inspection</h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-2">
              Property Address *
            </label>
            <input
              id="address"
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="123 Main St, Raleigh, NC 27605"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              disabled={loading}
            />
            <p className="text-xs text-gray-500 mt-1">
              Include street address, city, state, and ZIP code
            </p>
          </div>
          
          <button 
            onClick={start} 
            disabled={loading || !address.trim()}
            className="w-full px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
          >
            {loading ? 'Creating...' : 'Start Inspection'}
          </button>
        </div>
      </div>
    </div>
  );
}


