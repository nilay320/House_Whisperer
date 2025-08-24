import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { db } from '../services/firebase';
import { collection, onSnapshot, orderBy, query } from 'firebase/firestore';
import { apiDelete } from '../services/api';

export default function InspectionsList({ user }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    if (!user) return; // do not subscribe if not authed
    const qRef = query(collection(db, 'inspections'), orderBy('createdAt', 'desc'));
    const unsub = onSnapshot(qRef, (snap) => {
      const rows = [];
      snap.forEach((d) => {
        const data = d.data() || {};
        const counts = data.counts || {};
        rows.push({
          id: d.id,
          address: data.address || '',
          status: data.status || 'in_progress',
          createdAt: data.createdAt,
          counts: {
            total: counts.total || 0,
            done: counts.done || 0,
          },
        });
      });
      setItems(rows);
      setLoading(false);
    }, () => setLoading(false));
    return () => unsub && unsub();
  }, [user]);

  const handleDelete = async (inspection) => {
    const address = inspection.address || `Inspection ${inspection.id.slice(0, 8)}...`;
    const confirmed = window.confirm(
      `Are you sure you want to delete "${address}"?\n\nThis will permanently delete:\n• The inspection\n• All clips (${inspection.counts.total})\n• All reports\n\nThis action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setDeleting(inspection.id);
    try {
      await apiDelete(`/api/inspections/${inspection.id}`);
      // The onSnapshot will automatically update the list
    } catch (error) {
      console.error('Failed to delete inspection:', error);
      alert('Failed to delete inspection. Please try again.');
    } finally {
      setDeleting(null);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><p>Loading…</p></div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link 
              to="/inspector" 
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span className="text-sm">Back to Dashboard</span>
            </Link>
            <h2 className="text-2xl font-bold">My Inspections</h2>
          </div>
          <Link to="/inspection/new" className="text-sm text-emerald-500 hover:underline">Start Inspection</Link>
        </div>
        <div className="bg-white border rounded-lg shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="p-3">Property Address</th>
                <th className="p-3">Status</th>
                <th className="p-3">Clips</th>
                <th className="p-3">Created</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-b hover:bg-gradient-to-r hover:from-emerald-50 hover:to-purple-50 transition-all duration-200 cursor-pointer">
                  <td className="p-3">
                    <div className="font-medium text-gray-900">
                      {it.address || 'No address provided'}
                    </div>
                    <div className="text-xs text-gray-500 font-mono">
                      ID: {it.id.slice(0, 8)}...
                    </div>
                  </td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      it.status==='done'?'bg-green-100 text-green-700':
                      it.status==='in_progress'?'bg-yellow-100 text-yellow-700':
                      it.status==='published'?'bg-blue-100 text-blue-700':
                      it.status==='attention'?'bg-red-100 text-red-700':
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {it.status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="p-3 text-gray-700">{it.counts.done}/{it.counts.total}</td>
                  <td className="p-3 text-gray-500 text-xs">
                    {it.createdAt?.toDate ? 
                      it.createdAt.toDate().toLocaleDateString() : 
                      'N/A'
                    }
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <Link 
                        to={`/inspection/${it.id}`} 
                        className="text-emerald-600 hover:text-emerald-700 hover:underline font-medium focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none rounded"
                      >
                        Open
                      </Link>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(it);
                        }}
                        disabled={deleting === it.id}
                        className="p-1 text-red-600 hover:text-red-800 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete inspection"
                      >
                        {deleting === it.id ? (
                          <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                        ) : (
                          <Trash2 size={16} />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="p-3 text-gray-500" colSpan={5}>No inspections yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
