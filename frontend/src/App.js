import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { motion } from 'framer-motion';
import { onAuthStateChange } from './services/firebase';
import AuthScreen from './screens/AuthScreen';
import ChatbotWidget from './components/ChatbotWidget';
import InspectorCapture from './components/InspectorCapture';
import { Home, Camera, MessageCircle, LogOut, FileText } from 'lucide-react';
import { signOutUser } from './services/firebase';
import toast from 'react-hot-toast';
import { getUserRole } from './services/firebase';

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
  const [role, setRole] = useState(null);
  const [roleLoading, setRoleLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChange(async (user) => {
      setUser(user);
      setLoading(false);
      if (user) {
        setRoleLoading(true);
        const { role: userRole } = await getUserRole(user.uid);
        setRole(userRole);
        setRoleLoading(false);
      } else {
        setRole(null);
      }
    });
    return () => unsubscribe();
  }, []);

  if (loading || roleLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // If user is logged in but has no role, show AuthScreen (role selector)
  if (user && !role) {
    return <AuthScreen />;
  }

  // Enhanced Buyer Dashboard
  const BuyerDashboard = () => {
    const [recentReports] = useState([
      { id: 1, property: '123 Main St', date: '2024-01-15', status: 'Reviewed', issues: 3 },
      { id: 2, property: '456 Oak Ave', date: '2024-01-10', status: 'New', issues: 7 },
    ]);

    const [suggestedQuestions] = useState([
      "What are the most critical issues I should address first?",
      "How much might these repairs cost?",
      "Are there any safety concerns I should know about?",
      "What maintenance should I prioritize in the first year?",
      "Are there any deal-breakers in this report?"
    ]);

    // Handler functions for quick actions
    const handleUploadReport = () => {
      toast('Upload feature coming soon! For now, use the chat widget to upload PDFs.', {
        icon: '📁'
      });
      // TODO: Could open a file picker or modal
    };

    const handleAskQuestions = () => {
      toast('💬 Use the chat widget in the bottom-right corner to ask questions!', {
        icon: '💡'
      });
      // Could scroll to chat widget or highlight it
    };

    const handlePropertyTimeline = () => {
      toast('Property timeline feature coming soon!', {
        icon: '🏠'
      });
      // TODO: Navigate to timeline view
    };

    const handleQuestionClick = (question) => {
      toast(`Great question! Use the chat widget to ask: "${question}"`, {
        icon: '❓'
      });
      // TODO: Could auto-populate the chat input
    };

    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-6xl mx-auto px-6 py-8">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Welcome Back!</h1>
                <p className="text-gray-600 mt-2">Review your inspection reports and get AI-powered insights</p>
              </div>
              <div className="hidden md:flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm text-gray-500">Need help?</p>
                  <p className="text-sm font-medium text-blue-600">Use the chat widget →</p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-blue-600" />
                </div>
                <button
                  onClick={async () => {
                    const { error } = await signOutUser();
                    if (error) {
                      toast.error('Failed to sign out');
                    } else {
                      toast.success('Signed out successfully');
                    }
                  }}
                  className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="text-sm">Sign Out</span>
                </button>
              </div>
            </div>
            
            {/* Mobile logout */}
            <div className="md:hidden mt-4 pt-4 border-t border-gray-200">
              <button
                onClick={async () => {
                  const { error } = await signOutUser();
                  if (error) {
                    toast.error('Failed to sign out');
                  } else {
                    toast.success('Signed out successfully');
                  }
                }}
                className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors w-full justify-center"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Sign Out</span>
              </button>
            </div>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
          {/* Quick Actions */}
          <div className="grid md:grid-cols-3 gap-6">
            <motion.div
              whileHover={{ scale: 1.02 }}
              onClick={handleUploadReport}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-all"
            >
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Upload New Report</h3>
                  <p className="text-sm text-gray-600">Get AI analysis of your inspection</p>
                </div>
              </div>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.02 }}
              onClick={handleAskQuestions}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-all"
            >
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Ask Questions</h3>
                  <p className="text-sm text-gray-600">Get instant answers about your property</p>
                </div>
              </div>
            </motion.div>

            <motion.div
              whileHover={{ scale: 1.02 }}
              onClick={handlePropertyTimeline}
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-all"
            >
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Home className="w-6 h-6 text-purple-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Property Timeline</h3>
                  <p className="text-sm text-gray-600">Track inspection history</p>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Recent Reports */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">Recent Inspection Reports</h2>
              <p className="text-gray-600 mt-1">Your latest property inspections and their status</p>
            </div>
            <div className="p-6">
              {recentReports.length > 0 ? (
                <div className="space-y-4">
                  {recentReports.map((report) => (
                    <motion.div
                      key={report.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                          <FileText className="w-5 h-5 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">{report.property}</h3>
                          <p className="text-sm text-gray-600">Inspected on {report.date}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            report.status === 'New' 
                              ? 'bg-green-100 text-green-800' 
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {report.status}
                          </span>
                          <p className="text-sm text-gray-600 mt-1">{report.issues} items noted</p>
                        </div>
                        <button className="text-blue-600 hover:text-blue-800">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No reports yet</h3>
                  <p className="text-gray-600 mb-4">Upload your first inspection report to get started with AI analysis</p>
                  <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Upload Report
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* AI Assistant Section */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* Suggested Questions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">Popular Questions</h2>
                <p className="text-gray-600 mt-1">Quick start with these common queries</p>
              </div>
              <div className="p-6">
                <div className="space-y-3">
                  {suggestedQuestions.map((question, index) => (
                    <motion.button
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => handleQuestionClick(question)}
                      className="w-full text-left p-3 bg-gray-50 rounded-lg hover:bg-blue-50 hover:border-blue-200 border border-gray-200 transition-all"
                    >
                      <div className="flex items-center space-x-3">
                        <MessageCircle className="w-4 h-4 text-blue-600 flex-shrink-0" />
                        <span className="text-sm text-gray-700">{question}</span>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>

            {/* Getting Started Guide */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-lg font-bold text-gray-900">How to Get Started</h2>
                <p className="text-gray-600 mt-1">Make the most of your inspection reports</p>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div className="flex items-start space-x-3">
                    <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-blue-600">1</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">Upload Your Report</h3>
                      <p className="text-sm text-gray-600">Drag and drop your PDF inspection report using the chat widget</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-green-600">2</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">Ask Questions</h3>
                      <p className="text-sm text-gray-600">Get plain-English explanations of technical terms and findings</p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-6 h-6 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-purple-600">3</span>
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">Make Informed Decisions</h3>
                      <p className="text-sm text-gray-600">Understand repair priorities, costs, and safety concerns</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

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
        
        {user && role === 'inspector' && <Navigation user={user} />}
        
        <Routes>
          <Route
            path="/"
            element={user
              ? (role === 'inspector'
                  ? <Navigate to="/dashboard" />
                  : role === 'buyer'
                    ? <Navigate to="/buyer" />
                    : null // Don't navigate if role is missing!
                )
              : <AuthScreen />}
          />
          <Route
            path="/dashboard"
            element={user && role === 'inspector' ? <Dashboard /> : <Navigate to="/" />}
          />
          <Route
            path="/inspector"
            element={user && role === 'inspector' ? <InspectorPage /> : <Navigate to="/" />}
          />
          <Route
            path="/buyer"
            element={user && role === 'buyer' ? <BuyerDashboard /> : <Navigate to="/" />}
          />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>

        {/* Chatbot Widget - Only for buyers */}
        {user && role === 'buyer' && <ChatbotWidget />}
        {/* Inspector features only for inspectors */}
      </div>
    </Router>
  );
}

export default App; 