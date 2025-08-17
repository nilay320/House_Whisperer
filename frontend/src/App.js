import React, { useEffect, useRef, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import ChatbotWidget from './components/ChatbotWidget';
import AuthScreen from './screens/AuthScreen';
import { onAuthStateChange, getUserRole, signOutUser } from './services/firebase';
import { Home, MessageCircle, BookOpen } from 'lucide-react';
import StartInspection from './screens/StartInspection';
import InspectionDetail from './screens/InspectionDetail';
import InspectionsList from './screens/InspectionsList';

const InspectorShell = () => (
  <div className="min-h-screen bg-gray-50 p-6">
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Inspector Workspace</h2>
        <div className="text-sm text-gray-600">Capture clips, ask questions, and generate reports.</div>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-2">Standards Q&A</h3>
          <p className="text-sm text-gray-600 mb-3">Ask about InterNACHI, NCHILB, and NC codes.</p>
          {/* Floating widget is global; we embed guidance here for now */}
          <p className="text-xs text-gray-500">Use the chat widget (bottom-right) to ask questions.</p>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-2">Inspections</h3>
          <p className="text-sm text-gray-600">Start a new inspection or open an existing one.</p>
          <div className="flex gap-4 text-sm">
            <Link to="/inspection/new" className="text-blue-600 hover:underline">Start Inspection</Link>
            <Link to="/inspections" className="text-blue-600 hover:underline">View Inspections</Link>
          </div>
        </div>
        
      </div>
    </div>
  </div>
);

const RoleRedirect = ({ user, role, loading }) => {
  const hasRedirected = useRef(false);
  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><p>Loading…</p></div>;
  if (!user) return <AuthScreen />;
  // One-shot redirect to avoid flicker during role resolution
  if (!hasRedirected.current) {
    hasRedirected.current = true;
    if (role === 'inspector') return <Navigate to="/inspector" replace />;
    return <Navigate to="/inspector" replace />; // default role path
  }
  return null;
};

function App() {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [roleLoading, setRoleLoading] = useState(false);

  useEffect(() => {
    const unsub = onAuthStateChange(async (u) => {
      setUser(u);
      if (u) {
        setRoleLoading(true);
        const { role } = await getUserRole(u.uid);
        setRole(role);
        setRoleLoading(false);
      } else {
        setRole(null);
      }
      setLoading(false);
    });
    return () => unsub();
  }, []);

  if (loading || (user && role === null && roleLoading)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50"><p>Loading…</p></div>
    );
  }

  return (
    <Router>
      <div className="App">
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
        }}
      />

      {/* Chatbot Widget - visible to all for now */}
      <ChatbotWidget />
      <Routes>
        <Route path="/" element={<RoleRedirect user={user} role={role} loading={loading || roleLoading} />} />
        <Route path="/inspector" element={user && role === 'inspector' ? <InspectorShell /> : <Navigate to="/" replace />} />
        <Route path="/inspections" element={<InspectionsList />} />
        <Route path="/inspection/new" element={<StartInspection />} />
        <Route path="/inspection/:id" element={<InspectionDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
    </Router>
  );
}

export default App;