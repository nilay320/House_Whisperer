import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { onAuthStateChange } from './services/firebase';
import AuthScreen from './screens/AuthScreen';
import ChatbotWidget from './components/ChatbotWidget';
import InspectorCapture from './components/InspectorCapture';
import { Home, Camera, MessageCircle, LogOut } from 'lucide-react';
import { signOutUser } from './services/firebase';
import toast from 'react-hot-toast';

// Navigation Component
const Navigation = ({ user }) => {
  const location = useLocation();
  
  const handleSignOut = async () => {
    const { error } = await signOutUser();
    if (error) {
      toast.error('Failed to sign out');
    } else {
      toast.success('Signed out successfully');
    }
  };

  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Dashboard' },
    { path: '/inspector', icon: Camera, label: 'Inspector' },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <h1 className="text-xl font-bold text-blue-600">Inspector AI</h1>
          <div className="hidden md:flex space-x-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors
                  ${location.pathname === item.path
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }
                `}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button
            onClick={handleSignOut}
            className="flex items-center space-x-1 px-3 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden md:inline">Sign Out</span>
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden mt-3 pt-3 border-t border-gray-200">
        <div className="flex space-x-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors flex-1 justify-center
                ${location.pathname === item.path
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }
              `}
            >
              <item.icon className="w-4 h-4" />
              <span className="text-sm">{item.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};

// Dashboard Component
const Dashboard = () => (
  <div className="min-h-screen bg-gray-50 p-8">
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Welcome to Inspector AI</h2>
          <p className="text-gray-600 mb-4">
            Your AI-powered home inspection assistant. Capture voice notes and photos 
            to generate professional inspection reports automatically.
          </p>
          <Link
            to="/inspector"
            className="inline-flex items-center space-x-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Camera className="w-4 h-4" />
            <span>Start Inspection</span>
          </Link>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
          <p className="text-gray-600 mb-4">
            Your recent inspections and reports will appear here.
          </p>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-700">No recent inspections</span>
              <span className="text-sm text-gray-500">Get started!</span>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Camera className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-semibold mb-2">1. Capture</h3>
            <p className="text-gray-600 text-sm">Take photos and record voice notes during your inspection</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <MessageCircle className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-semibold mb-2">2. Process</h3>
            <p className="text-gray-600 text-sm">AI analyzes your inputs and generates structured reports</p>
          </div>
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <Home className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="font-semibold mb-2">3. Deliver</h3>
            <p className="text-gray-600 text-sm">Export professional reports in multiple formats</p>
          </div>
        </div>
      </div>
    </div>
  </div>
);

// Report Generation Component
const ReportGenerator = ({ reportData, onClose }) => {
  const [isGenerating, setIsGenerating] = useState(true);
  const [reportContent, setReportContent] = useState('');

  useEffect(() => {
    // Simulate AI report generation
    const generateReport = async () => {
      setIsGenerating(true);
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Mock report content
      const mockReport = `
# Home Inspection Report

## Executive Summary
Based on the captured voice notes and photos, this property shows the following findings:

## Voice Notes Summary
${reportData.recordings.length} voice notes were analyzed and transcribed.

## Photo Analysis
${reportData.photos.length} photos were processed and analyzed for potential issues.

## Recommendations
1. Further inspection recommended for any identified issues
2. Professional consultation advised for major concerns
3. Regular maintenance schedule should be established

*This report was generated using AI analysis and should be reviewed by a qualified inspector.*
      `;
      
      setReportContent(mockReport);
      setIsGenerating(false);
      toast.success('Report generated successfully!');
    };

    generateReport();
  }, [reportData]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">AI Generated Report</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>
        </div>
        
        <div className="p-6 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 120px)' }}>
          {isGenerating ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Generating your inspection report...</p>
              <p className="text-sm text-gray-500 mt-2">Processing {reportData.recordings.length} voice notes and {reportData.photos.length} photos</p>
            </div>
          ) : (
            <div className="prose max-w-none">
              <pre className="whitespace-pre-wrap text-gray-800">{reportContent}</pre>
            </div>
          )}
        </div>
        
        {!isGenerating && (
          <div className="p-6 border-t border-gray-200 bg-gray-50">
            <div className="flex space-x-4">
              <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                Export PDF
              </button>
              <button className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                Email Report
              </button>
              <button
                onClick={onClose}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Inspector Page Component
const InspectorPage = () => {
  const [showReportGenerator, setShowReportGenerator] = useState(false);
  const [currentReportData, setCurrentReportData] = useState(null);

  const handleGenerateReport = (reportData) => {
    setCurrentReportData(reportData);
    setShowReportGenerator(true);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <InspectorCapture onGenerateReport={handleGenerateReport} />
      
      {showReportGenerator && currentReportData && (
        <ReportGenerator
          reportData={currentReportData}
          onClose={() => setShowReportGenerator(false)}
        />
      )}
    </div>
  );
};

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChange((user) => {
      setUser(user);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
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
        
        {user && <Navigation user={user} />}
        
        <Routes>
          <Route
            path="/"
            element={user ? <Navigate to="/dashboard" /> : <AuthScreen />}
          />
          <Route
            path="/dashboard"
            element={user ? <Dashboard /> : <Navigate to="/" />}
          />
          <Route
            path="/inspector"
            element={user ? <InspectorPage /> : <Navigate to="/" />}
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>

        {/* Chatbot Widget - Always available for testing */}
        {user && <ChatbotWidget />}
      </div>
    </Router>
  );
}

export default App; 