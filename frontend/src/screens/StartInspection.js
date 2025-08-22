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

    setLoading(true);
    try {
      const insp = await apiPost('/api/inspections', { address: address.trim() });
      try {
        await setDoc(doc(db, 'inspections', insp.id), {
          ownerUid: auth.currentUser?.uid || null,
          address: address.trim(),
          createdAt: serverTimestamp(),
          status: 'in_progress',
        }, { merge: true });
      } catch (e) {
        // non-fatal in dev
        // eslint-disable-next-line no-console
        console.warn('Firestore write failed (non-fatal):', e);
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
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={loading}
            />
            <p className="text-xs text-gray-500 mt-1">
              Include street address, city, state, and ZIP code
            </p>
          </div>
          
          <button 
            onClick={start} 
            disabled={loading || !address.trim()}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {loading ? 'Creating...' : 'Start Inspection'}
          </button>
        </div>
      </div>
    </div>
  );
}


