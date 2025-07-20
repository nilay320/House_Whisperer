import React, { useState, useRef, useEffect } from 'react';
import { Camera, Mic, MicOff, Upload, FileText, Trash2, Play, Pause } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';

const InspectorCapture = ({ onGenerateReport }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [currentRecording, setCurrentRecording] = useState(null);
  const [playingRecording, setPlayingRecording] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  // Check if device supports media recording
  const [hasMediaSupport, setHasMediaSupport] = useState(false);

  useEffect(() => {
    setHasMediaSupport(
      navigator.mediaDevices && 
      navigator.mediaDevices.getUserMedia && 
      window.MediaRecorder
    );
  }, []);

  // Voice Recording Functions
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });

      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        const newRecording = {
          id: Date.now(),
          blob: audioBlob,
          url: audioUrl,
          duration: Date.now() - currentRecording?.startTime || 0,
          timestamp: new Date().toLocaleTimeString()
        };

        setRecordings(prev => [...prev, newRecording]);
        stream.getTracks().forEach(track => track.stop());
        toast.success('Voice note recorded!');
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setCurrentRecording({ startTime: Date.now() });
      toast.success('Recording started');
    } catch (error) {
      console.error('Error starting recording:', error);
      toast.error('Could not access microphone');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setCurrentRecording(null);
    }
  };

  const playRecording = (recording) => {
    if (playingRecording === recording.id) {
      setPlayingRecording(null);
      return;
    }

    const audio = new Audio(recording.url);
    audio.onended = () => setPlayingRecording(null);
    audio.play();
    setPlayingRecording(recording.id);
  };

  const deleteRecording = (id) => {
    setRecordings(prev => prev.filter(r => r.id !== id));
    toast.success('Recording deleted');
  };

  // Photo Capture Functions
  const capturePhoto = () => {
    cameraInputRef.current?.click();
  };

  const handlePhotoCapture = (event) => {
    const files = Array.from(event.target.files);
    const newPhotos = files.map(file => ({
      id: Date.now() + Math.random(),
      file,
      url: URL.createObjectURL(file),
      name: file.name,
      timestamp: new Date().toLocaleTimeString()
    }));

    setPhotos(prev => [...prev, ...newPhotos]);
    toast.success(`${files.length} photo(s) added`);
  };

  const deletePhoto = (id) => {
    setPhotos(prev => prev.filter(p => p.id !== id));
    toast.success('Photo deleted');
  };

  // File Upload via Dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
      'audio/*': ['.mp3', '.wav', '.m4a']
    },
    onDrop: (acceptedFiles) => {
      const newFiles = acceptedFiles.map(file => {
        const isImage = file.type.startsWith('image/');
        return {
          id: Date.now() + Math.random(),
          file,
          url: URL.createObjectURL(file),
          name: file.name,
          type: isImage ? 'photo' : 'audio',
          timestamp: new Date().toLocaleTimeString()
        };
      });

      newFiles.forEach(file => {
        if (file.type === 'photo') {
          setPhotos(prev => [...prev, file]);
        } else {
          setRecordings(prev => [...prev, { ...file, blob: file.file }]);
        }
      });

      toast.success(`${acceptedFiles.length} file(s) added`);
    }
  });

  const generateReport = () => {
    if (recordings.length === 0 && photos.length === 0) {
      toast.error('Please add at least one voice note or photo');
      return;
    }

    const reportData = {
      recordings: recordings.map(r => ({
        id: r.id,
        timestamp: r.timestamp,
        blob: r.blob,
        duration: r.duration
      })),
      photos: photos.map(p => ({
        id: p.id,
        timestamp: p.timestamp,
        file: p.file,
        name: p.name
      }))
    };

    onGenerateReport?.(reportData);
    toast.success('Generating AI report...');
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Inspector Capture</h1>
        <p className="text-gray-600">Record voice notes and capture photos for AI report generation</p>
      </div>

      {/* Media Support Warning */}
      {!hasMediaSupport && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">
            ⚠️ Your browser doesn't support media recording. You can still upload files manually.
          </p>
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        {/* Voice Recording */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={!hasMediaSupport}
          className={`
            p-6 rounded-xl border-2 transition-all duration-200
            ${isRecording 
              ? 'bg-red-50 border-red-300 text-red-700' 
              : 'bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100'
            }
            ${!hasMediaSupport ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          <div className="flex flex-col items-center space-y-2">
            {isRecording ? (
              <MicOff className="w-8 h-8" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
            <span className="font-medium">
              {isRecording ? 'Stop Recording' : 'Record Voice Note'}
            </span>
            {isRecording && (
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            )}
          </div>
        </motion.button>

        {/* Photo Capture */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={capturePhoto}
          className="p-6 rounded-xl border-2 bg-green-50 border-green-300 text-green-700 hover:bg-green-100 transition-all duration-200 cursor-pointer"
        >
          <div className="flex flex-col items-center space-y-2">
            <Camera className="w-8 h-8" />
            <span className="font-medium">Take Photo</span>
          </div>
        </motion.button>
      </div>

      {/* File Upload Area */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        {isDragActive ? (
          <p className="text-blue-600">Drop files here...</p>
        ) : (
          <div>
            <p className="text-gray-600">Drag & drop photos or audio files here</p>
            <p className="text-sm text-gray-400 mt-1">or click to browse</p>
          </div>
        )}
      </div>

      {/* Recordings List */}
      {recordings.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Voice Notes ({recordings.length})</h3>
          <div className="space-y-2">
            {recordings.map((recording) => (
              <motion.div
                key={recording.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between p-4 bg-white border rounded-lg shadow-sm"
              >
                <div className="flex items-center space-x-3">
                  <button
                    onClick={() => playRecording(recording)}
                    className="p-2 bg-blue-100 text-blue-600 rounded-full hover:bg-blue-200 transition-colors"
                  >
                    {playingRecording === recording.id ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </button>
                  <div>
                    <p className="font-medium text-gray-900">Voice Note</p>
                    <p className="text-sm text-gray-500">{recording.timestamp}</p>
                  </div>
                </div>
                <button
                  onClick={() => deleteRecording(recording.id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-full transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Photos Grid */}
      {photos.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Photos ({photos.length})</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {photos.map((photo) => (
              <motion.div
                key={photo.id}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative group"
              >
                <img
                  src={photo.url}
                  alt={photo.name}
                  className="w-full h-32 object-cover rounded-lg border"
                />
                <button
                  onClick={() => deletePhoto(photo.id)}
                  className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 rounded-b-lg">
                  {photo.timestamp}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Generate Report Button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={generateReport}
        disabled={recordings.length === 0 && photos.length === 0}
        className={`
          w-full p-4 rounded-xl font-semibold text-white transition-all duration-200
          ${recordings.length > 0 || photos.length > 0
            ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
            : 'bg-gray-400 cursor-not-allowed'
          }
        `}
      >
        <div className="flex items-center justify-center space-x-2">
          <FileText className="w-5 h-5" />
          <span>Generate AI Report</span>
        </div>
      </motion.button>

      {/* Hidden Inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        onChange={handlePhotoCapture}
        className="hidden"
      />
    </div>
  );
};

export default InspectorCapture; 