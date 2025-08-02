import React from 'react';
import { Toaster } from 'react-hot-toast';
import ChatbotWidget from './components/ChatbotWidget';
import { Home, MessageCircle, BookOpen } from 'lucide-react';

function App() {
  return (
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
      
      {/* Main Landing Page */}
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-6xl mx-auto px-6 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Home className="w-8 h-8 text-blue-600" />
                <h1 className="text-2xl font-bold text-gray-900">NC Inspector AI</h1>
              </div>
              <div className="text-sm text-gray-600">
                North Carolina Home Inspector Standards Assistant
              </div>
            </div>
          </div>
        </div>

        {/* Hero Section */}
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              North Carolina Home Inspector Standards Assistant
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Get instant answers about NCHILB regulations, InterNACHI standards, and NC building codes. 
              Designed specifically for North Carolina licensed home inspectors and those pursuing licensure.
            </p>
          </div>

          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <BookOpen className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">NCHILB Compliance</h3>
              <p className="text-gray-600">
                Access NC Home Inspector Licensure Board regulations and requirements instantly.
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <MessageCircle className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Instant Q&A</h3>
              <p className="text-gray-600">
                Ask natural language questions and get immediate, accurate answers with source references.
              </p>
            </div>

            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <Home className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">NC Building Codes</h3>
              <p className="text-gray-600">
                Navigate North Carolina building codes and amendments relevant to home inspections.
              </p>
            </div>
          </div>

          {/* Sample Questions */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            <h3 className="text-xl font-semibold mb-6 text-center">Try These Sample Questions</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700">
                  <span className="font-medium">Q:</span> What is the required clearance for electrical panels?
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700">
                  <span className="font-medium">Q:</span> How do I properly inspect a crawl space?
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700">
                  <span className="font-medium">Q:</span> What are the NCHILB continuing education requirements?
                </p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-700">
                  <span className="font-medium">Q:</span> How should I inspect roof flashings?
                </p>
              </div>
            </div>
            <p className="text-center mt-6 text-gray-600">
              Click the chat widget in the bottom right to start asking questions →
            </p>
          </div>
        </div>
      </div>

      {/* Chatbot Widget - Always visible */}
      <ChatbotWidget />
    </div>
  );
}

export default App;