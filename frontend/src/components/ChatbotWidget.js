import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, X, MessageCircle, FileText, User, Bot, ChevronDown, ChevronUp, BookOpen, CheckCircle } from 'lucide-react';
import { useDropzone } from 'react-dropzone';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Custom markdown components for better formatting
const markdownComponents = {
  // Headers
  h1: ({ children }) => <h1 className="text-2xl font-bold mb-3 mt-4">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-semibold mb-2 mt-3">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 mt-2">{children}</h3>,
  h4: ({ children }) => <h4 className="text-base font-semibold mb-1 mt-2">{children}</h4>,
  
  // Paragraphs and text
  p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  
  // Lists
  ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="ml-2">{children}</li>,
  
  // Code
  code: ({ inline, children }) => {
    if (inline) {
      return <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>;
    }
    return (
      <pre className="bg-gray-100 p-3 rounded-lg overflow-x-auto mb-3">
        <code className="text-sm font-mono">{children}</code>
      </pre>
    );
  },
  
  // Blockquotes
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-blue-500 pl-4 my-3 italic text-gray-700">
      {children}
    </blockquote>
  ),
  
  // Tables
  table: ({ children }) => (
    <div className="overflow-x-auto mb-3">
      <table className="min-w-full border-collapse border border-gray-300">
        {children}
      </table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-gray-300 px-3 py-2 bg-gray-100 font-semibold text-left">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-gray-300 px-3 py-2">
      {children}
    </td>
  ),
};

// Component for displaying sources in a structured way
const SourcesDisplay = ({ sources }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!sources || sources.length === 0) return null;
  
  // Group sources by type
  const sourcesByType = sources.reduce((acc, source) => {
    const type = source.source?.includes('InterNACHI') ? 'InterNACHI Standards' :
                  source.source?.includes('NCHILB') || source.source?.includes('NC Home Inspector Licensure Board') ? 'NC Licensure Board' :
                  source.source?.includes('NC Building Codes') || source.source?.includes('Building Code') ? 'NC Building Codes' :
                  source.type === 'web_resource' ? 'Web Resources' :
                  'Other Sources';
    
    if (!acc[type]) acc[type] = [];
    acc[type].push(source);
    return acc;
  }, {});
  
  return (
    <div className="mt-4 border-t pt-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
      >
        <span className="flex items-center gap-2">
          <BookOpen size={16} />
          Sources ({sources.length})
        </span>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-3 space-y-3"
          >
            {Object.entries(sourcesByType).map(([type, typeSources]) => (
              <div key={type} className="bg-gray-50 rounded-lg p-3">
                <h5 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-600" />
                  {type}
                </h5>
                <div className="space-y-2">
                  {typeSources.map((source, idx) => (
                    <div key={idx} className="text-xs text-gray-600 ml-5">
                      <div className="flex items-start gap-2">
                        <span className="text-gray-400">•</span>
                        <div>
                          <span className="font-medium">{source.source}</span>
                          <span className="ml-2 text-gray-500">
                            (Relevance: {(source.score * 100).toFixed(0)}%)
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Component for rendering bot messages with markdown and sources
const BotMessage = ({ content, sources, timestamp }) => {
  // Separate timing info and sources from main content
  const contentParts = content.split('\n\n⏱️');
  const mainContent = contentParts[0];
  const timingInfo = contentParts[1] ? contentParts[1].split('\n\n📚')[0] : null;
  
  // Extract sources if they're in the content
  let extractedSources = sources;
  if (!extractedSources && content.includes('📚 Sources:')) {
    const sourcesMatch = content.match(/📚 Sources:([\s\S]*?)(?:\n\n|$)/);
    if (sourcesMatch) {
      extractedSources = [];
      const sourceLines = sourcesMatch[1].trim().split('\n');
      sourceLines.forEach(line => {
        const match = line.match(/• (.+?) \(relevance: (\d+\.?\d*)%\)/);
        if (match) {
          extractedSources.push({
            source: match[1],
            score: parseFloat(match[2]) / 100
          });
        }
      });
    }
  }
  
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl bg-gray-100 text-gray-800 px-4 py-3">
        <div className="flex items-start space-x-2">
          <Bot size={16} className="mt-1 text-blue-600 flex-shrink-0" />
          <div className="flex-1">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={markdownComponents}
              >
                {mainContent}
              </ReactMarkdown>
            </div>
            
            {timingInfo && (
              <div className="mt-3 text-xs text-gray-500 flex items-center gap-2">
                <span>⏱️</span>
                <span>{timingInfo.replace('**Response Time:', '').replace('**', '').trim()}</span>
              </div>
            )}
            
            {extractedSources && extractedSources.length > 0 && (
              <SourcesDisplay sources={extractedSources} />
            )}
            
            <p className="text-xs opacity-70 mt-2">
              {formatTime(timestamp)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

const formatTime = (timestamp) => {
  return timestamp.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
};

const ChatbotWidget = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: 'Hello! I\'m your **NC Home Inspector AI Assistant**. I can help you with:\n\n• InterNACHI standards and best practices\n• NCHILB regulations and requirements\n• NC building codes and amendments\n• Inspection procedures and compliance\n\nWhat would you like to know about North Carolina home inspection standards?',
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedPdf, setUploadedPdf] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const uploadPdfToBackend = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload_pdf', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('PDF upload error:', error);
      throw error;
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    onDrop: async (acceptedFiles) => {
      const file = acceptedFiles[0];
      if (file) {
        setUploadedPdf(file);
        addMessage('user', `Uploaded PDF: ${file.name}`);
        setIsLoading(true);
        
        try {
          // Upload and process the PDF
          const result = await uploadPdfToBackend(file);
          addMessage('bot', `✅ Successfully processed your inspection report "${file.name}". I can now answer specific questions about your property's findings, provide maintenance recommendations, and help you understand any issues that were identified. What would you like to know?`);
        } catch (error) {
          addMessage('bot', `❌ Sorry, I had trouble processing your PDF. Please make sure the backend API is running and try uploading again. Error: ${error.message}`);
          setUploadedPdf(null); // Clear the uploaded file on error
        } finally {
          setIsLoading(false);
        }
      }
    },
  });

  const addMessage = (type, content, sources = null) => {
    const newMessage = {
      id: Date.now(),
      type,
      content,
      sources,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSendMessage = async () => {
    console.log('handleSendMessage called');
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    console.log('User message:', userMessage);
    setInputValue('');
    addMessage('user', userMessage);
    console.log('User message added to chat');
    setIsLoading(true);

    try {
      if (uploadedPdf) {
        // Use PDF chat endpoint for document-specific questions
        const response = await fetch('/api/pdf_chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: userMessage,
            pdf_filename: uploadedPdf.name,
            model: 'gpt-4o-mini'
          }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // PDF chat returns JSON
        const data = await response.json();
        addMessage('bot', data.answer);
      } else {
        // Use RAG chat endpoint for inspector questions with SSE streaming
        console.log('Starting RAG chat request with SSE...');
        const apiUrl = process.env.REACT_APP_API_URL || '';
        console.log('API URL:', apiUrl);
        console.log('Sending message:', userMessage);
        
        const response = await fetch(`${apiUrl}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            message: userMessage,
            sessionId: `session-${Date.now()}`
          }),
        });
        
        console.log('Response status:', response.status);
        console.log('Response ok:', response.ok);
        
        if (!response.ok) {
          console.error('Response not ok:', response.status, response.statusText);
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Handle SSE streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentBotMessageId = null;
        const requestStartTime = Date.now();
        let accumulatedResponse = '';
        let responseSources = [];
        
        // Add initial bot message for streaming updates
        const botMessage = {
          id: Date.now(),
          type: 'bot',
          content: '🤖 Starting analysis...',
          timestamp: new Date(),
        };
        currentBotMessageId = botMessage.id;
        setMessages(prev => [...prev, botMessage]);
        
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const jsonStr = line.slice(6);
                  console.log('Parsing SSE line:', jsonStr.substring(0, 100) + (jsonStr.length > 100 ? '...' : ''));
                  const data = JSON.parse(jsonStr);
                  
                  if (data.status === 'progress') {
                    // Update the bot message with progress and timing
                    const elapsed = data.elapsed_seconds || ((Date.now() - requestStartTime) / 1000);
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: `🤖 ${data.message} (${elapsed.toFixed(1)}s)` }
                        : msg
                    ));
                  } else if (data.status === 'response_start') {
                    // Response is starting - show metadata
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: `🤖 Generating response... (${data.response_length} chars expected)` }
                        : msg
                    ));
                  } else if (data.status === 'response_chunk') {
                    // Accumulate response chunks and update UI in real-time
                    accumulatedResponse += data.chunk;
                    
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: accumulatedResponse }
                        : msg
                    ));
                  } else if (data.status === 'sources') {
                    // Store sources for final display
                    responseSources = data.sources;
                  } else if (data.status === 'complete') {
                    // Final completion - add timing and sources to accumulated response
                    const totalTime = data.total_time_seconds || ((Date.now() - requestStartTime) / 1000);
                    let finalResponse = accumulatedResponse;
                    
                    // Add timing info
                    finalResponse += `\n\n⏱️ **Response Time: ${totalTime.toFixed(1)} seconds**`;
                    
                    // Update the bot message with final response and sources separately
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: finalResponse, sources: responseSources }
                        : msg
                    ));
                    
                    console.log(`SSE streaming completed in ${totalTime.toFixed(1)} seconds`); // Debug log
                    break;
                  } else if (data.status === 'error') {
                    // Error response
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: `❌ Error: ${data.message}` }
                        : msg
                    ));
                    break;
                  }
                } catch (parseError) {
                  console.error('Failed to parse SSE data:', parseError);
                  console.error('Line causing error:', line);
                  console.error('Line length:', line.length);
                  
                  // If it's a complete status but parsing failed, try to display error
                  if (line.includes('"status":"complete"')) {
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentBotMessageId 
                        ? { ...msg, content: '❌ Response received but failed to parse. Check console for details.' }
                        : msg
                    ));
                  }
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }
      }
      
    } catch (error) {
      console.error('Chat error:', error);
      addMessage('bot', 'Sorry, I encountered an error processing your request. Please make sure the backend API is running and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const removePdf = () => {
    setUploadedPdf(null);
    addMessage('user', 'Removed uploaded PDF');
  };

  return (
    <>
      {/* Chat Toggle Button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-50 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-colors"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: 0 }}
              animate={{ rotate: 180 }}
              exit={{ rotate: 0 }}
            >
              <X size={24} />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ rotate: 180 }}
              animate={{ rotate: 0 }}
              exit={{ rotate: 180 }}
            >
              <MessageCircle size={24} />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Chat Widget - Increased size */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-6 z-40 w-[600px] h-[650px] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-t-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                  <Bot size={16} />
                </div>
                <div>
                  <h3 className="font-semibold">NC Home Inspector AI</h3>
                  <p className="text-xs text-blue-100">InterNACHI • NCHILB • NC Building Codes</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-blue-100 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {message.type === 'bot' ? (
                    <BotMessage 
                      content={message.content} 
                      sources={message.sources}
                      timestamp={message.timestamp}
                    />
                  ) : (
                    <div className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl bg-blue-600 text-white px-4 py-3">
                        <div className="flex items-start space-x-2">
                          <div className="flex-1">
                            <p className="text-sm leading-relaxed">{message.content}</p>
                            <p className="text-xs opacity-70 mt-2">
                              {formatTime(message.timestamp)}
                            </p>
                          </div>
                          <User size={16} className="mt-1 text-blue-100 flex-shrink-0" />
                        </div>
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-start"
                >
                  <div className="bg-gray-100 text-gray-800 rounded-2xl px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <Bot size={16} className="text-blue-600" />
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Info Section - Enhanced */}
            <div className="px-4 pb-2">
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <BookOpen size={16} className="text-blue-600 mt-0.5" />
                  <div className="text-sm text-blue-800 flex-1">
                    <p className="font-medium">NC Inspector Knowledge Base</p>
                    <p className="text-xs text-blue-600 mt-1">
                      Powered by InterNACHI SOP, NCHILB regulations, and 2024 NC Building Codes
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200">
              <div className="flex items-end space-x-2">
                <div className="flex-1">
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask about inspection standards, codes, or regulations..."
                    className="w-full resize-none border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={1}
                    style={{ minHeight: '40px', maxHeight: '120px' }}
                  />
                </div>
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatbotWidget;