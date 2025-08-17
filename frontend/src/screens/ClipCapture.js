import React, { useEffect, useRef, useState } from 'react';
import { storage } from '../services/firebase';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import { apiPost, apiGet } from '../services/api';

const randomId = () => Math.random().toString(36).slice(2);

export default function ClipCapture() {
  const [inspection, setInspection] = useState(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [photos, setPhotos] = useState([]); // {file, caption}
  const [clip, setClip] = useState(null);
  const streamRef = useRef(null);

  useEffect(() => {
    // Create an inspection on mount for demo
    (async () => {
      const insp = await apiPost('/api/inspections', {});
      setInspection(insp);
    })();
  }, []);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    const mr = new MediaRecorder(stream);
    const nextChunks = [];
    mr.ondataavailable = (e) => { if (e.data && e.data.size > 0) nextChunks.push(e.data); };
    mr.onstop = async () => {
      setChunks(nextChunks);
    };
    mr.start();
    setMediaRecorder(mr);
    setRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorder) mediaRecorder.stop();
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
    setRecording(false);
  };

  const handlePhotoFiles = (files) => {
    const arr = Array.from(files).map((f) => ({ file: f, caption: '' }));
    setPhotos((prev) => [...prev, ...arr]);
  };

  const updateCaption = (idx, caption) => {
    setPhotos((prev) => prev.map((p, i) => (i === idx ? { ...p, caption } : p)));
  };

  const uploadToStorage = async (blobOrFile, path) => {
    const r = ref(storage, path);
    await uploadBytes(r, blobOrFile);
    return getDownloadURL(r);
  };

  const submitClip = async () => {
    if (!inspection) return;
    if (!chunks.length) return;
    const audioBlob = new Blob(chunks, { type: 'audio/webm' });
    const clipId = randomId();
    const audioPath = `inspections/${inspection.id}/clips/${clipId}.webm`;
    const audioUrl = await uploadToStorage(audioBlob, audioPath);

    // Upload photos
    const photoPayload = [];
    for (let i = 0; i < photos.length; i += 1) {
      const p = photos[i];
      const photoPath = `inspections/${inspection.id}/clips/${clipId}/photo_${i}.jpg`;
      const url = await uploadToStorage(p.file, photoPath);
      photoPayload.push({ id: `p${i}`, url, user_caption: p.caption || '' });
    }

    const created = await apiPost(`/api/inspections/${inspection.id}/clips`, {
      audio_url: audioUrl,
      photos: photoPayload,
    });
    setClip(created);

    // Poll transcript status
    const id = created.id;
    const poll = async () => {
      const c = await apiGet(`/api/clips/${id}`);
      setClip(c);
      if (c.status === 'queued' || c.status === 'processing') setTimeout(poll, 2000);
    };
    setTimeout(poll, 1500);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-4">Add Clip</h2>
        {!inspection ? (
          <p>Creating inspection…</p>
        ) : (
          <div className="space-y-6">
            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-2">Audio</h3>
              <div className="flex items-center gap-3">
                {!recording ? (
                  <button className="px-3 py-2 bg-blue-600 text-white rounded" onClick={startRecording}>Start</button>
                ) : (
                  <button className="px-3 py-2 bg-red-600 text-white rounded" onClick={stopRecording}>Stop</button>
                )}
                <span className="text-sm text-gray-600">{recording ? 'Recording…' : chunks.length ? 'Recorded' : 'Idle'}</span>
              </div>
            </div>

            <div className="bg-white border rounded p-4">
              <h3 className="font-semibold mb-2">Photos</h3>
              <input type="file" accept="image/*" multiple onChange={(e) => handlePhotoFiles(e.target.files)} />
              <div className="mt-3 space-y-2">
                {photos.map((p, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">{p.file?.name}</span>
                    <input className="border rounded px-2 py-1 text-sm flex-1" placeholder="Caption" value={p.caption} onChange={(e) => updateCaption(i, e.target.value)} />
                  </div>
                ))}
              </div>
            </div>

            <div>
              <button className="px-4 py-2 bg-green-600 text-white rounded" onClick={submitClip} disabled={!chunks.length}>Submit Clip</button>
            </div>

            {clip && (
              <div className="bg-white border rounded p-4">
                <h3 className="font-semibold mb-2">Clip Status</h3>
                <p className="text-sm">Status: <span className="font-mono">{clip.status}</span></p>
                {clip.transcript && (
                  <pre className="whitespace-pre-wrap text-sm mt-2 bg-gray-50 p-2 rounded">{clip.transcript}</pre>
                )}
                {clip.error && (
                  <p className="text-sm text-red-600 mt-2">Error: {clip.error}</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


