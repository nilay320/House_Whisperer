import React, { useEffect, useRef, useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiPost, fetchReportSections } from '../services/api';
import { auth, db, storage } from '../services/firebase';
import { collection, doc, onSnapshot, orderBy, query, serverTimestamp, setDoc } from 'firebase/firestore';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';

const randomId = () => Math.random().toString(36).slice(2);

export default function InspectionDetail() {
  const { id } = useParams();
  const [inspection, setInspection] = useState(null);
  const [clips, setClips] = useState([]);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [audioUrl, setAudioUrl] = useState('');
  const [mimeUsed, setMimeUsed] = useState('');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [durationSec, setDurationSec] = useState(null);
  const [sizeBytes, setSizeBytes] = useState(null);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [sectionKey, setSectionKey] = useState('');
  const [sectionOptions, setSectionOptions] = useState([]);
  const [draft, setDraft] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const selectedSection = useMemo(() => sectionOptions.find(o => o.key === sectionKey), [sectionKey, sectionOptions]);

  useEffect(() => {
    // Load section options from backend YAML
    (async () => {
      try {
        const opts = await fetchReportSections();
        setSectionOptions(opts);
        const last = window.sessionStorage.getItem('hw_last_section_key');
        if (last && opts.find(o => o.key === last)) {
          setSectionKey(last);
        }
      } catch (e) {
        setSectionOptions([]);
      }
    })();
  }, []);

  useEffect(() => {
    const clipsRef = collection(db, 'inspections', id, 'clips');
    const q = query(clipsRef, orderBy('createdAt', 'asc'));
    const unsub = onSnapshot(q, (snap) => {
      const rows = [];
      snap.forEach((d) => rows.push({ id: d.id, ...d.data() }));
      setClips(rows);
      setInspection({ id });
    });
    return () => unsub();
  }, [id]);

  // Subscribe to report draft
  useEffect(() => {
    const dref = doc(db, 'inspections', id, 'reports', 'draft');
    const unsub = onSnapshot(dref, (snap) => {
      setDraft(snap.exists() ? ({ id: snap.id, ...snap.data() }) : null);
    });
    return () => unsub();
  }, [id]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    const preferred = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    const mime = preferred.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) || '';
    const mr = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    setMimeUsed(mime || mr.mimeType || 'audio/webm');
    const next = [];
    mr.ondataavailable = (e) => { if (e.data && e.data.size) next.push(e.data); };
    mr.onstop = async () => {
      setChunks(next);
      const blob = new Blob(next, { type: mime || 'audio/webm' });
      setRecordedBlob(blob);
      setSizeBytes(blob.size);
      try {
        const arrayBuf = await blob.arrayBuffer();
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) {
          const ctx = new AC();
          const audioBuf = await ctx.decodeAudioData(arrayBuf.slice(0));
          setDurationSec(audioBuf.duration);
          ctx.close && ctx.close();
        }
      } catch (e) {
        // ignore duration decode errors
      }
    };
    mr.start(1000);
    setMediaRecorder(mr);
    setRecording(true);
    setElapsedMs(0);
    timerRef.current = setInterval(() => setElapsedMs((v) => v + 1000), 1000);
  };
  const stopRecording = () => {
    try { mediaRecorder?.requestData(); } catch (e) {}
    mediaRecorder?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    setRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const handlePhotoFiles = (files) => {
    const arr = Array.from(files).map((f) => ({ file: f, caption: '' }));
    setPhotos(prev => [...prev, ...arr]);
  };
  const updateCaption = (idx, caption) => setPhotos(prev => prev.map((p,i)=> i===idx?{...p, caption}:p));

  const uploadToStorage = async (blobOrFile, path, contentType) => {
    const r = ref(storage, path);
    await uploadBytes(r, blobOrFile, contentType ? { contentType } : undefined);
    return getDownloadURL(r);
  };

  const transcriptPreview = useMemo(() => '', [chunks, recordedBlob]);

  const canSave = !!sectionKey && (recordedBlob || chunks.length);
  const needsSection = !sectionKey && (recordedBlob || chunks.length);

  const saveClip = async () => {
    if (!sectionKey) return;
    const blob = recordedBlob || (chunks.length ? new Blob(chunks, { type: mimeUsed || 'audio/webm' }) : null);
    if (!blob) return;
    const idLocal = randomId();
    const ct = mimeUsed || blob.type || 'audio/webm';
    const ext = ct.includes('mp4') ? 'm4a' : (ct.includes('ogg') ? 'ogg' : 'webm');
    const aPath = `inspections/${id}/clips/${idLocal}.${ext}`;
    const aUrl = await uploadToStorage(blob, aPath, ct);

    const photoPayload = [];
    for (let i = 0; i < photos.length; i += 1) {
      const p = photos[i];
      const pPath = `inspections/${id}/clips/${idLocal}/photo_${i}.jpg`;
      const url = await uploadToStorage(p.file, pPath, p.file?.type || 'image/jpeg');
      photoPayload.push({ id: `p${i}`, url, user_caption: p.caption || '' });
    }

    const clipDoc = doc(db, 'inspections', id, 'clips', idLocal);
    await setDoc(clipDoc, {
      audioUrl: aUrl,
      photos: photoPayload,
      section: sectionKey || null,
      status: 'queued',
      createdAt: serverTimestamp(),
      ownerUid: null,
    }, { merge: true });

    await apiPost(`/api/inspections/${id}/clips`, { clip_id: idLocal, audio_url: aUrl, photos: photoPayload });

    window.sessionStorage.setItem('hw_last_section_key', sectionKey);

    setChunks([]);
    setPhotos([]);
    setSectionKey(sectionKey);
    setRecordedBlob(null);
    setDurationSec(null);
    setSizeBytes(null);
  };

  const generateDraft = async () => {
    try {
      setGenerating(true);
      await apiPost('/api/generate_report', { inspectionId: id });
    } catch (e) {
      // no-op; surface errors minimally
      console.error('generate_report failed', e);
    } finally {
      setGenerating(false);
    }
  };

  const publishDraft = async () => {
    try {
      setPublishing(true);
      await apiPost('/api/publish_report', { inspectionId: id });
    } catch (e) {
      console.error('publish_report failed', e);
    } finally {
      setPublishing(false);
    }
  };

  const downloadMarkdown = () => {
    if (!draft || !draft.markdown) return;
    const blob = new Blob([draft.markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inspection_${id}_draft.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const MarkdownPreview = ({ markdown }) => {
    if (!markdown) return null;
    const lines = markdown.split('\n');
    return (
      <div className="max-h-96 overflow-auto rounded border bg-gray-50 p-3">
        {lines.map((ln, i) => {
          const img = ln.match(/^\s*-\s*!\[(.*?)\]\((.*?)\)/);
          if (img) {
            const alt = img[1] || '';
            const url = img[2];
            return (
              <div key={i} className="my-2">
                <img src={url} alt={alt} className="w-full max-w-md max-h-64 object-contain rounded border" />
                {alt ? <div className="text-xs text-gray-500 mt-1">{alt}</div> : null}
              </div>
            );
          }
          return <p key={i} className="text-sm whitespace-pre-wrap">{ln}</p>;
        })}
      </div>
    );
  };

  // Soft completeness indicator for demo
  const REQUIRED_SECTIONS = ['roof','exterior','electrical','plumbing','hvac','insulation_ventilation','interior','site_drainage'];
  const completedSectionKeys = useMemo(() => {
    const set = new Set();
    clips.forEach(c => { if (c.section && (c.status === 'done' || c.transcript)) set.add(c.section); });
    return Array.from(set);
  }, [clips]);
  const missingRequired = useMemo(() => REQUIRED_SECTIONS.filter(k => !completedSectionKeys.includes(k)), [REQUIRED_SECTIONS, completedSectionKeys]);
  const labelFor = (key) => (sectionOptions.find(s => s.key === key)?.label || key);
  const isComplete = missingRequired.length === 0;
  const badgeClass = isComplete
    ? 'inline-block px-2 py-1 rounded text-xs bg-green-100 text-green-700 font-medium'
    : 'inline-block px-2 py-1 rounded text-xs bg-amber-100 text-amber-700 font-medium';

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-2">
          <Link to="/inspections" className="inline-flex items-center text-sm text-blue-600 hover:underline">
            <span className="mr-1">←</span> Back to Inspections
          </Link>
        </div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Inspection #{id}</h2>
          <span className="text-sm text-gray-500">Clips: {clips.length}</span>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white border rounded-lg p-5 shadow-sm">
            <h3 className="font-semibold mb-2">Add Clip</h3>
            <div className="flex items-center gap-3">
              {!recording ? (
                <button className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700" onClick={startRecording}>Start</button>
              ) : (
                <button className="px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700" onClick={stopRecording}>Stop</button>
              )}
              <span className="text-sm text-gray-600">{recording ? `Recording… ${Math.floor(elapsedMs/1000)}s` : recordedBlob ? 'Recorded' : 'Idle'}</span>
            </div>
            {chunks.length > 0 && (
              <div className="mt-3">
                <audio controls src={URL.createObjectURL(recordedBlob || new Blob(chunks, { type: mimeUsed || 'audio/webm' }))} />
                <div className="text-xs text-gray-600 mt-1">
                  {durationSec != null && <span>Recorded: {Math.round(durationSec)}s</span>}
                  {sizeBytes != null && <span> • Size: {(sizeBytes/1024).toFixed(1)} KB</span>}
                  {mimeUsed && <span> • {mimeUsed}</span>}
                </div>
                <div className="mt-2 flex gap-2">
                  <button className="px-3 py-2 bg-gray-200 rounded hover:bg-gray-300" onClick={() => { setChunks([]); setPhotos([]); }}>Delete</button>
                  {canSave ? (
                    <button className={`px-3 py-2 rounded text-white bg-green-600 hover:bg-green-700`} onClick={saveClip}>Save Clip</button>
                  ) : (
                    <span title="Select a section to enable Save">
                      <button className={`px-3 py-2 rounded text-white bg-gray-400 cursor-not-allowed`} disabled>Save Clip</button>
                    </span>
                  )}
                </div>
              </div>
            )}
            <div className="mt-4">
              <h4 className="font-medium mb-1">Photos</h4>
              <input type="file" accept="image/*" capture="environment" multiple onChange={(e)=>handlePhotoFiles(e.target.files)} />
              <div className="mt-2 space-y-2">
                {photos.map((p,i)=>(
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">{p.file?.name}</span>
                    <input className="border rounded px-2 py-1 text-sm flex-1" placeholder="Caption" value={p.caption} onChange={(e)=>updateCaption(i,e.target.value)} />
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <h4 className="font-medium mb-1">Section <span className="text-red-600">*</span></h4>
                <select className={`border rounded px-2 py-1 text-sm ${needsSection ? 'border-red-500' : ''}`} value={sectionKey} onChange={(e)=>setSectionKey(e.target.value)} aria-invalid={needsSection}>
                  <option value="">Select section…</option>
                  {sectionOptions.map(opt => (
                    <option key={opt.key} value={opt.key}>{opt.label}</option>
                  ))}
                </select>
                {needsSection && (
                  <div className="mt-1 text-xs text-red-600">Select a section to enable Save.</div>
                )}
                {selectedSection && selectedSection.includes && selectedSection.includes.length > 0 && (
                  <div className="mt-1 text-xs text-gray-500">Includes: {selectedSection.includes.join(', ')}</div>
                )}
              </div>
            </div>
          </div>

          <div className="bg-white border rounded-lg p-5 shadow-sm">
            <h3 className="font-semibold mb-2">Clips</h3>
            <div className="space-y-3">
              {clips.map(c => (
                <div key={c.id} className="border rounded p-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-700">ID: <span className="font-mono">{c.id}</span>{c.section && <span className="ml-2 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{c.section}</span>}</div>
                    <span className={`text-xs px-2 py-1 rounded-full ${c.status==='done'?'bg-green-100 text-green-700':c.status==='processing'?'bg-yellow-100 text-yellow-700':'bg-gray-100 text-gray-700'}`}>{c.status}</span>
                  </div>
                  {c.transcript && <pre className="mt-2 text-sm bg-gray-50 p-2 rounded whitespace-pre-wrap">{c.transcript}</pre>}
                  {Array.isArray(c.photos) && c.photos.length > 0 && (
                    <div className="mt-3">
                      <div className="grid grid-cols-3 gap-2">
                        {c.photos.map((ph) => (
                          <a key={ph.id} href={ph.url} target="_blank" rel="noreferrer" className="block">
                            <img src={ph.url} alt={ph.user_caption || 'photo'} className="w-full h-20 object-cover rounded border" />
                          </a>
                        ))}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {c.photos.map((ph) => ph.user_caption).filter(Boolean).join(' • ')}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {clips.length === 0 && <p className="text-sm text-gray-500">No clips yet.</p>}
            </div>
          </div>
        </div>

        {/* Report Draft Panel */}
        <div className="mt-8 bg-white border rounded-lg p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">Report Draft</h3>
            <div className="flex items-center gap-2">
              <button className={`px-3 py-2 rounded text-white ${generating?'bg-gray-400':'bg-blue-600 hover:bg-blue-700'}`} onClick={generateDraft} disabled={generating}>
                {generating ? 'Generating…' : 'Generate Draft'}
              </button>
              <button className={`px-3 py-2 rounded text-white ${publishing || !draft?'bg-gray-400':'bg-green-600 hover:bg-green-700'}`} onClick={publishDraft} disabled={publishing || !draft}>
                {publishing ? 'Publishing…' : 'Publish Final Draft'}
              </button>
              <button className={`px-3 py-2 rounded ${!draft?'bg-gray-200 text-gray-500':'bg-gray-100 hover:bg-gray-200'}`} onClick={downloadMarkdown} disabled={!draft}>Download .md</button>
            </div>
          </div>
          <div className="text-xs text-gray-700 mb-2 flex items-center gap-2">
            <span>Required sections completed:</span>
            <span className={badgeClass}>{REQUIRED_SECTIONS.length - missingRequired.length}/{REQUIRED_SECTIONS.length}</span>
            {missingRequired.length > 0 && (
              <>
                <span className="ml-2 text-amber-700">Missing:</span>
                <span className="ml-1 text-amber-700">{missingRequired.map(labelFor).join(', ')}</span>
              </>
            )}
          </div>
          {draft?.markdown ? (
            <MarkdownPreview markdown={draft.markdown} />
          ) : (
            <p className="text-sm text-gray-500">No draft yet. Click "Generate Draft" to build a report from current clips.</p>
          )}
        </div>
      </div>
    </div>
  );
}


