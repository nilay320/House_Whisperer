import React from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../services/api';
import { auth, db } from '../services/firebase';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';

export default function StartInspection() {
  const navigate = useNavigate();

  const start = async () => {
    const insp = await apiPost('/api/inspections', {});
    try {
      await setDoc(doc(db, 'inspections', insp.id), {
        ownerUid: auth.currentUser?.uid || null,
        createdAt: serverTimestamp(),
        status: 'in_progress',
      }, { merge: true });
    } catch (e) {
      // non-fatal in dev
      // eslint-disable-next-line no-console
      console.warn('Firestore write failed (non-fatal):', e);
    }
    navigate(`/inspection/${insp.id}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white border rounded p-8 shadow-sm">
        <h2 className="text-2xl font-bold mb-4">Start New Inspection</h2>
        <button onClick={start} className="px-4 py-2 bg-blue-600 text-white rounded">Start Inspection</button>
      </div>
    </div>
  );
}


