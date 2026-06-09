import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api, type SourceInfo, type ContentResponse } from '../api/client';
import Modal from '../components/Modal';

export default function DomainDetail() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const domain = name!;

  const [instructions, setInstructions] = useState('');
  const [instLoading, setInstLoading] = useState(true);
  const [instSaving, setInstSaving] = useState(false);
  const [instMsg, setInstMsg] = useState('');

  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [srcLoading, setSrcLoading] = useState(true);
  const [error, setError] = useState('');

  const [showCreateSource, setShowCreateSource] = useState(false);
  const [newSourceName, setNewSourceName] = useState('');
  const [newSourceFile, setNewSourceFile] = useState<File | null>(null);
  const [creatingSource, setCreatingSource] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const [editingSource, setEditingSource] = useState<string | null>(null);
  const [specExisting, setSpecExisting] = useState(false);
  const [specContent, setSpecContent] = useState('');
  const [specLoading, setSpecLoading] = useState(false);
  const [specSaving, setSpecSaving] = useState(false);
  const [specUploading, setSpecUploading] = useState(false);

  const [viewContent, setViewContent] = useState('');
  const [viewLabel, setViewLabel] = useState('');
  const [showViewModal, setShowViewModal] = useState(false);

  const fileInputRefs = useRef<Map<string, HTMLInputElement | null>>(new Map());
  const [selectedFiles, setSelectedFiles] = useState<Map<string, { file: File; name: string }>>(new Map());

  const loadInstructions = () => {
    setInstLoading(true);
    api.getInstructions(domain)
      .then((r: ContentResponse) => setInstructions(r.content))
      .catch((e: Error) => setError(e.message))
      .finally(() => setInstLoading(false));
  };

  const loadSources = () => {
    setSrcLoading(true);
    api.listSources(domain)
      .then(setSources)
      .catch((e: Error) => setError(e.message))
      .finally(() => setSrcLoading(false));
  };

  useEffect(() => {
    loadInstructions();
    loadSources();
  }, [domain]);

  const saveInstructions = async () => {
    setInstSaving(true);
    setInstMsg('');
    try {
      await api.saveInstructions(domain, instructions);
      setInstMsg('Saved.');
      setTimeout(() => setInstMsg(''), 2000);
    } catch (e: any) {
      setInstMsg(`Error: ${e.message}`);
    } finally {
      setInstSaving(false);
    }
  };

  const handleCreateSource = async () => {
    if (!newSourceName.trim()) return;
    setCreatingSource(true);
    try {
      await api.createSource(domain, newSourceName.trim());
      if (newSourceFile) {
        const content = await newSourceFile.text();
        await api.uploadSpec(domain, newSourceName.trim(), content);
      }
      setNewSourceName('');
      setNewSourceFile(null);
      setShowCreateSource(false);
      loadSources();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreatingSource(false);
    }
  };

  const handleDeleteSource = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteSource(domain, deleteTarget);
      setDeleteTarget(null);
      if (editingSource === deleteTarget) {
        setEditingSource(null);
        setSpecContent('');
        setSelectedFiles((prev) => {
          const next = new Map(prev);
          next.delete(deleteTarget);
          return next;
        });
      }
      loadSources();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const openSource = async (sourceName: string) => {
    if (editingSource === sourceName) {
      setEditingSource(null);
      return;
    }
    setEditingSource(sourceName);
    setSpecLoading(true);
    try {
      const r = await api.getSpec(domain, sourceName);
      const existing = r.content.trim().length > 0;
      setSpecExisting(existing);
      setSpecContent(r.content);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSpecLoading(false);
    }
  };

  const handleFileSelect = (sourceName: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFiles((prev) => {
      const next = new Map(prev);
      next.set(sourceName, { file, name: file.name });
      return next;
    });
  };

  const handleUpload = async (sourceName: string) => {
    const entry = selectedFiles.get(sourceName);
    if (!entry) return;
    setSpecUploading(true);
    try {
      const content = await entry.file.text();
      await api.uploadSpec(domain, sourceName, content);
      setSpecContent(content);
      setSelectedFiles((prev) => {
        const next = new Map(prev);
        next.delete(sourceName);
        return next;
      });
      const inputEl = fileInputRefs.current.get(sourceName);
      if (inputEl) inputEl.value = '';
      setSpecExisting(true);
      loadSources();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSpecUploading(false);
    }
  };

  const openViewer = async (sourceName: string) => {
    setViewLabel(`${sourceName} — source_specs.md`);
    setViewContent('');
    setShowViewModal(true);
    try {
      const r = await api.getSpec(domain, sourceName);
      setViewContent(r.content);
    } catch {
      setViewContent('(error loading content)');
    }
  };

  const handleNewSession = async (sourceName: string) => {
    try {
      const session = await api.createSession(domain, sourceName);
      navigate(`/sessions/${session.session_id}`, { state: session });
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <Link to="/domains" className="text-sm text-blue-600 hover:text-blue-800">Domains</Link>
        <span className="text-gray-400">/</span>
        <h2 className="text-2xl font-bold text-gray-900">{domain}</h2>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4">
          {error}
          <button onClick={() => setError('')} className="float-right font-bold">&times;</button>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Domain Instructions</h3>
          <div className="flex items-center gap-2">
            {instMsg && <span className="text-sm text-green-600">{instMsg}</span>}
            <button
              onClick={saveInstructions}
              disabled={instSaving}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {instSaving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
        {instLoading ? (
          <p className="text-gray-500 text-sm">Loading...</p>
        ) : (
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={8}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Enter domain-specific instructions in markdown..."
          />
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Sources</h3>
          <button
            onClick={() => setShowCreateSource(true)}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
          >
            + Create Source
          </button>
        </div>

        {srcLoading ? (
          <p className="text-gray-500 text-sm">Loading...</p>
        ) : sources.length === 0 ? (
          <p className="text-gray-500 text-sm py-4">No sources in this domain. Create one to upload a specification file.</p>
        ) : (
          <div className="space-y-2">
            {sources.map((s) => {
              const isOpen = editingSource === s.name;
              const sel = selectedFiles.get(s.name);
              return (
                <div
                  key={s.name}
                  className={`border border-gray-100 rounded-md ${s.has_spec ? 'cursor-pointer' : ''}`}
                  onDoubleClick={() => s.has_spec && handleNewSession(s.name)}
                >
                  <div className="flex items-center justify-between py-2 px-3 hover:bg-gray-50">
                    <button
                      onClick={() => openSource(s.name)}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium text-left"
                    >
                      {s.name}
                      <span className={`ml-2 text-xs text-gray-400 transition-transform inline-block ${isOpen ? 'rotate-90' : ''}`}>
                        &#9654;
                      </span>
                    </button>
                    <div className="flex items-center gap-3">
                      {s.has_spec ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Spec ready
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          No spec
                        </span>
                      )}
                      {s.has_spec && (
                        <button
                          onClick={() => handleNewSession(s.name)}
                          className="text-xs text-white bg-green-600 hover:bg-green-700 px-2 py-1 rounded font-medium"
                        >
                          New Session
                        </button>
                      )}
                      <button
                        onClick={() => setDeleteTarget(s.name)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="border-t border-gray-100 p-4 bg-gray-50 rounded-b-md">
                      {specLoading ? (
                        <p className="text-gray-500 text-sm">Loading...</p>
                      ) : (
                        <div className="space-y-3">
                          {specExisting && (
                            <div>
                              <button
                                onClick={() => openViewer(s.name)}
                                className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200 border border-gray-200"
                              >
                                View Existing Spec
                              </button>
                              <span className="ml-2 text-xs text-gray-400">source_specs.md</span>
                            </div>
                          )}

                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                              {specExisting ? 'Upload replacement file' : 'Upload specification file'}
                            </label>
                            <div className="flex items-center gap-2">
                              <input
                                ref={(el) => { fileInputRefs.current.set(s.name, el); }}
                                type="file"
                                accept=".md,.txt"
                                onChange={(e) => handleFileSelect(s.name, e)}
                                className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                              />
                              {sel && (
                                <button
                                  onClick={() => handleUpload(s.name)}
                                  disabled={specUploading}
                                  className="px-4 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex-shrink-0"
                                >
                                  {specUploading ? 'Uploading...' : 'Upload'}
                                </button>
                              )}
                            </div>
                            {sel && (
                              <p className="text-xs text-gray-500 mt-1">
                                Selected: <span className="font-medium">{sel.name}</span> — will be saved as <span className="font-mono">source_specs.md</span>
                              </p>
                            )}
                          </div>

                          {specExisting && sel && (
                            <div className="bg-amber-50 border border-amber-200 rounded-md px-3 py-2 text-sm text-amber-800 flex items-start gap-2">
                              <span className="text-amber-500 mt-0.5">&#9888;</span>
                              <span>
                                <strong>Warning:</strong> Uploading will overwrite the existing <span className="font-mono">source_specs.md</span> file.
                                {specExisting && ' Any prior extraction results for this source will remain in the output store unchanged.'}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <Modal open={showViewModal} onClose={() => setShowViewModal(false)} title={viewLabel} wide>
        <pre className="bg-gray-50 border border-gray-200 rounded-md p-4 text-xs text-gray-700 overflow-auto max-h-96 font-mono whitespace-pre-wrap">
          {viewContent || <span className="text-gray-400">(empty)</span>}
        </pre>
        <div className="flex justify-end mt-3">
          <button
            onClick={() => setShowViewModal(false)}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Close
          </button>
        </div>
      </Modal>

      <Modal open={showCreateSource} onClose={() => { setShowCreateSource(false); setNewSourceName(''); setNewSourceFile(null); }} title="Create Source">
        <label className="block text-sm font-medium text-gray-700 mb-1">Source name</label>
        <input
          type="text"
          value={newSourceName}
          onChange={(e) => setNewSourceName(e.target.value)}
          placeholder="e.g. monthly-export"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-4"
          autoFocus
          onKeyDown={(e) => e.key === 'Enter' && handleCreateSource()}
        />
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Specification file (optional)</label>
          <input
            type="file"
            accept=".md,.txt"
            onChange={(e) => setNewSourceFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {newSourceFile && (
            <p className="text-xs text-gray-500 mt-1">
              Selected: <span className="font-medium">{newSourceFile.name}</span> — will be saved as <span className="font-mono">source_specs.md</span>
            </p>
          )}
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={() => { setShowCreateSource(false); setNewSourceName(''); setNewSourceFile(null); }}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={handleCreateSource}
            disabled={creatingSource || !newSourceName.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creatingSource ? 'Creating...' : 'Create'}
          </button>
        </div>
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Source">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete <strong>{deleteTarget}</strong>? This will remove the source specification and all output files. This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button onClick={() => setDeleteTarget(null)} className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900">
            Cancel
          </button>
          <button
            onClick={handleDeleteSource}
            className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700"
          >
            Delete
          </button>
        </div>
      </Modal>
    </div>
  );
}
