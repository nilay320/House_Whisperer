import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { db } from '../services/firebase';
import { collection, onSnapshot, orderBy, query } from 'firebase/firestore';

export default function InspectionsList({ user }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

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
          status: data.status || 'in_progress',
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
          <Link to="/inspection/new" className="text-sm text-blue-600 hover:underline">Start Inspection</Link>
        </div>
        <div className="bg-white border rounded-lg shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="p-3">ID</th>
                <th className="p-3">Status</th>
                <th className="p-3">Clips</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-b">
                  <td className="p-3 font-mono text-gray-700">{it.id}</td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${it.status==='done'?'bg-green-100 text-green-700':it.status==='in_progress'?'bg-yellow-100 text-yellow-700':it.status==='attention'?'bg-red-100 text-red-700':'bg-gray-100 text-gray-700'}`}>{it.status}</span>
                  </td>
                  <td className="p-3 text-gray-700">{it.counts.done}/{it.counts.total}</td>
                  <td className="p-3"><Link to={`/inspection/${it.id}`} className="text-blue-600 hover:underline">Open</Link></td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="p-3 text-gray-500" colSpan={4}>No inspections yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
