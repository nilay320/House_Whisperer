import React, { useEffect, useRef, useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkSlug from 'remark-slug';
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
  const [requiredSections, setRequiredSections] = useState([]);
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
        const res = await fetchReportSections();
        setSectionOptions(res.sections || []);
        setRequiredSections(res.requiredSections || []);
        const last = window.sessionStorage.getItem('hw_last_section_key');
        if (last && (res.sections || []).find(o => o.key === last)) {
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
    // Hooks must not be conditional
    const containerRef = React.useRef(null);
    const [headings, setHeadings] = React.useState([]);
    React.useEffect(() => {
      const sc = containerRef.current;
      if (!sc) return;
      // Only include top-level section headings (h2) to keep TOC concise
      const els = Array.from(sc.querySelectorAll('h2'));
      setHeadings(els.map((el) => ({ level: 2, text: el.textContent || '', id: el.id })));
    }, [markdown]);
    const renderSeenRef = React.useRef(new Map()); // counts during render
    const scrollToId = (id) => {
      const sc = containerRef.current;
      if (!sc) return;
      const el = sc.querySelector(`#${id}`);
      if (!el) return;
      // Measure sticky header (TOC) and container padding to align the heading precisely
      const toc = sc.querySelector('[data-toc="1"]');
      const stickyH = toc ? toc.offsetHeight : 0;
      const cs = window.getComputedStyle(sc);
      const padTop = parseFloat(cs.paddingTop || '0') || 0;
      const offset = stickyH + padTop;
      // Compute delta within the scroll container for robust positioning
      const scRect = sc.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      const delta = elRect.top - scRect.top;
      const top = Math.max(sc.scrollTop + delta - offset, 0);
      sc.scrollTo({ top, behavior: 'smooth' });
    };
    const slug = (txt) => (txt || '').toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim().replace(/\s+/g, '-');
    if (!markdown) return null;
    return (
      <div ref={containerRef} className="max-h-96 overflow-auto rounded-lg border bg-white markdown-preview">
        {headings.length > 0 && (
          <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b px-3 py-2" data-toc="1">
            <div className="text-xs text-gray-700 font-medium mb-2">Table of Contents</div>
            <div className="flex flex-wrap gap-2">
              {headings.map(h => (
                <button key={h.id} onClick={() => scrollToId(h.id)} className={`text-xs px-3 py-1.5 rounded-md border font-medium ${h.level===2 ? 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' : 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200'} transition-colors`} title={h.text}>{h.text}</button>
              ))}
            </div>
          </div>
        )}
        <div className="p-4">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkSlug]}
            linkTarget="_blank"
            components={{
              h1: ({ node, ...props }) => <h1 className="text-xl font-bold mt-4 mb-2" {...props} />,
              h2: ({ node, ...props }) => {
                const text = String(props.children || '').trim();
                const base = slug(text);
                const map = renderSeenRef.current;
                const k = (map.get(base) || 0) + 1;
                map.set(base, k);
                const id = k > 1 ? `${base}-${k}` : base;
                return <h2 id={id} className="scroll-mt-16 text-lg font-semibold mt-4 mb-2" {...props} />;
              },
              h3: ({ node, ...props }) => {
                const text = String(props.children || '').trim();
                const base = slug(text);
                const map = renderSeenRef.current;
                const k = (map.get(base) || 0) + 1;
                map.set(base, k);
                const id = k > 1 ? `${base}-${k}` : base;
                return <h3 id={id} className="scroll-mt-16 font-semibold mt-3 mb-1" {...props} />;
              },
              p: ({ node, ...props }) => <p className="text-sm leading-6 mb-2" {...props} />,
              ul: ({ node, ...props }) => <ul className="list-disc ml-5 my-2 text-sm" {...props} />,
              ol: ({ node, ...props }) => <ol className="list-decimal ml-5 my-2 text-sm" {...props} />,
              li: ({ node, ...props }) => <li className="mb-1" {...props} />,
              a: ({ node, ...props }) => <a className="text-blue-600 underline" {...props} />,
              img: ({ node, ...props }) => <img className="w-full max-w-md max-h-64 object-contain rounded border my-2" {...props} />,
            }}
          >
            {markdown}
          </ReactMarkdown>
        </div>
      </div>
    );
  };

  // Soft completeness indicator for demo
  const REQUIRED_SECTIONS = requiredSections.length ? requiredSections : ['roof','exterior','electrical','plumbing','hvac','insulation_ventilation','interior','site_drainage'];
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
                <div className="mt-2 flex gap-3">
                  <button 
                    className="flex items-center gap-2 px-4 py-2 bg-orange-100 text-orange-700 border border-orange-200 rounded-lg hover:bg-orange-200 hover:border-orange-300 transition-colors font-medium text-sm"
                    onClick={() => {
                      if (window.confirm('Clear recording and photos? This cannot be undone.')) {
                        setChunks([]); 
                        setPhotos([]);
                      }
                    }}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Clear
                  </button>
                  {canSave ? (
                    <button 
                      className="flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-green-600 hover:bg-green-700 transition-colors font-medium text-sm"
                      onClick={saveClip}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Save Clip
                    </button>
                  ) : (
                    <span title="Select a section to enable Save">
                      <button 
                        className="flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gray-400 cursor-not-allowed font-medium text-sm opacity-60" 
                        disabled
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Save Clip
                      </button>
                    </span>
                  )}
                </div>
              </div>
            )}
            <div className="mt-4">
              <h4 className="font-medium mb-1">Photos</h4>
              <div className="relative">
                <input 
                  type="file" 
                  accept="image/*" 
                  capture="environment" 
                  multiple 
                  onChange={(e)=>handlePhotoFiles(e.target.files)}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="photo-upload"
                />
                <label 
                  htmlFor="photo-upload"
                  className="flex items-center justify-center w-full h-12 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 hover:border-gray-400 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <span>Add Photos</span>
                  </div>
                </label>
              </div>
              <div className="mt-2 space-y-2">
                {photos.map((p,i)=>(
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-sm text-gray-600">{p.file?.name}</span>
                    <input 
                      className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1 bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                      placeholder="Add caption..." 
                      value={p.caption} 
                      onChange={(e)=>updateCaption(i,e.target.value)} 
                    />
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <h4 className="font-medium mb-1">Section <span className="text-red-600">*</span></h4>
                <select className={`w-full border rounded-lg px-3 py-2 text-sm bg-white text-gray-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${needsSection ? 'border-red-500' : 'border-gray-300'}`} value={sectionKey} onChange={(e)=>setSectionKey(e.target.value)} aria-invalid={needsSection}>
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
                {requiredSections.length > 0 && (!isComplete || clips.length < 3) && (
                  <div className="mt-2 text-xs text-gray-600">
                    <span className="mr-1">Required:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {requiredSections.map((rk) => {
                        const present = completedSectionKeys.includes(rk);
                        return (
                          <span key={rk} className={`px-2 py-0.5 rounded border ${present ? 'bg-green-50 text-green-700 border-green-200 font-medium' : 'bg-gray-50 text-gray-700 border-gray-200'}`}>
                            {labelFor(rk)}
                          </span>
                        );
                      })}
                      <span className={`ml-2 ${isComplete ? 'text-green-700' : 'text-amber-700'}`}>{REQUIRED_SECTIONS.length - missingRequired.length}/{REQUIRED_SECTIONS.length} complete</span>
                    </div>
                  </div>
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
                    <div className="text-sm text-gray-700">ID: <span className="font-mono">{c.id}</span><span title={c.section || 'uncategorized'} className="ml-2 text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{c.section ? labelFor(c.section) : 'Uncategorized'}</span></div>
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
        <div className="mt-8 bg-white border rounded-lg p-5 shadow-sm report-draft-panel">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-bold text-gray-900">Report Draft</h3>
            <div className="flex items-center gap-2">
              <button className={`px-3 py-2 rounded text-white ${generating?'bg-gray-400':'bg-blue-600 hover:bg-blue-700'}`} onClick={generateDraft} disabled={generating}>
                {generating ? 'Generating…' : 'Generate Draft'}
              </button>
              <button className={`px-3 py-2 rounded text-white ${publishing || !draft?'bg-gray-400':'bg-green-600 hover:bg-green-700'}`} onClick={publishDraft} disabled={publishing || !draft}>
                {publishing ? 'Publishing…' : 'Publish Final Draft'}
              </button>
              <button className={`px-3 py-2 rounded text-white ${!draft?'bg-gray-400':'bg-blue-600 hover:bg-blue-700'} transition-colors`} onClick={downloadMarkdown} disabled={!draft}>Download .md</button>
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
          {draft?.sectionMetadata && (
            <div className="mb-3">
              <div className="text-xs text-gray-700 font-medium mb-2">Generation coverage</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(draft.sectionMetadata).map(([key, meta]) => {
                  const m = meta || {};
                  const nCount = m.narrativeCount || 0;
                  const topScore = typeof m.topScore === 'number' ? m.topScore : 0;
                  const minScore = parseFloat(process.env.REACT_APP_NARRATIVE_MIN_SCORE || '0.55');
                  const mode = nCount > 0 ? (topScore < minScore ? 'low' : 'narrative') : 'summary';
                  const style = mode === 'narrative'
                    ? 'bg-green-100 text-green-800 border border-green-300 font-medium'
                    : mode === 'low'
                      ? 'bg-gray-100 text-gray-700 border border-gray-300 font-medium'
                      : 'bg-amber-100 text-amber-800 border border-amber-300 font-medium';
                  const label = sectionOptions.find(s => s.key === key)?.label || key;
                  const text = mode === 'narrative' ? `Narrative (n=${nCount})`
                    : mode === 'low' ? `Narrative (low confidence n=${nCount})` : 'Summary';
                  return (
                    <span key={key} className={`text-xs px-3 py-1.5 rounded-md ${style}`} title={`${label}: ${text}`}>
                      {label}: {text}
                    </span>
                  );
                })}
              </div>
            </div>
          )}
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


