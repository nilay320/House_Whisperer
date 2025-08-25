import React, { useEffect, useRef, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import ChatbotWidget from './components/ChatbotWidget';
import CyberThemeInit from './components/ThemeToggle';
import AuthScreen from './screens/AuthScreen';
import { onAuthStateChange, getUserRole, setUserRole, signOutUser } from './services/firebase';
import { Home, MessageCircle, BookOpen } from 'lucide-react';
import StartInspection from './screens/StartInspection';
import InspectionDetail from './screens/InspectionDetail';
import InspectionsList from './screens/InspectionsList';

const InspectorShell = ({ onOpenChat }) => (
  <div className="min-h-screen bg-gray-50 p-6">
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Inspector Workspace</h2>
        <div className="text-sm text-gray-600">Capture clips, ask questions, and generate reports.</div>
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <button 
          onClick={onOpenChat}
          className="bg-white rounded-lg border p-4 hover:bg-gray-50 transition-colors text-left w-full group"
        >
          <h3 className="font-semibold mb-2 group-hover:text-emerald-500 transition-colors">Standards Q&A</h3>
          <p className="text-sm text-gray-600 mb-3">Ask about InterNACHI, NCHILB, and NC codes.</p>
          <p className="text-xs text-emerald-500 group-hover:text-emerald-600">Click to open chat assistant →</p>
        </button>
        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-semibold mb-2">Inspections</h3>
          <p className="text-sm text-gray-600">Start a new inspection or open an existing one.</p>
          <div className="flex gap-4 text-sm">
            <Link to="/inspection/new" className="text-emerald-500 hover:underline focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none rounded">Start Inspection</Link>
            <Link to="/inspections" className="text-emerald-500 hover:underline focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none rounded">View Inspections</Link>
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

// RequireAuth: blocks route content until auth resolved and user exists
const RequireAuth = ({ user, loading, children }) => {
  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><p>Loading…</p></div>;
  }
  if (!user) return <Navigate to="/" replace />;
  return children;
};

function App() {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);
  const [roleLoading, setRoleLoading] = useState(false);
  const chatWidgetRef = useRef(null);

  useEffect(() => {
    const unsub = onAuthStateChange(async (u) => {
      setUser(u);
      if (u) {
        setRoleLoading(true);
        const { role } = await getUserRole(u.uid);
        
        // If user doesn't have a role, automatically assign inspector
        if (!role || role !== 'inspector') {
          const { error } = await setUserRole(u.uid, 'inspector');
          if (!error) {
            setRole('inspector');
          } else {
            console.error('Failed to auto-assign inspector role:', error);
            // Set inspector role anyway for UI purposes
            setRole('inspector');
          }
        } else {
          setRole(role);
        }
        
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

      <CyberThemeInit />
      {/* Chatbot Widget - visible to all for now */}
      <ChatbotWidget ref={chatWidgetRef} />
      {process.env.NODE_ENV === 'development' && (
        <div className="cy-gradient border-b border-white/10">
          <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
            <div className="text-sm text-gray-600">House Whisperer</div>
            <div className="flex items-center gap-3">
              <span className="text-xs px-2 py-1 rounded-full bg-gray-100">Dev</span>
            </div>
          </div>
        </div>
      )}
      <Routes>
        <Route path="/" element={<RoleRedirect user={user} role={role} loading={loading || roleLoading} />} />
        <Route path="/inspector" element={user && role === 'inspector' ? <InspectorShell onOpenChat={() => chatWidgetRef.current?.openChat()} /> : <Navigate to="/" replace />} />
        <Route path="/inspections" element={<RequireAuth user={user} loading={loading || roleLoading}><InspectionsList user={user} /></RequireAuth>} />
        <Route path="/inspection/new" element={<RequireAuth user={user} loading={loading || roleLoading}><StartInspection /></RequireAuth>} />
        <Route path="/inspection/:id" element={<RequireAuth user={user} loading={loading || roleLoading}><InspectionDetail /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
    </Router>
  );
}

export default App;