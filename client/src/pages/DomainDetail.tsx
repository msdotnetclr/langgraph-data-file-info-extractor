import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, SourceInfo, ContentResponse } from '../api/client';
import Modal from '../components/Modal';

export default function DomainDetail() {
  const { name } = useParams<{ name: string }>();
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
  const [creatingSource, setCreatingSource] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const [editingSource, setEditingSource] = useState<string | null>(null);
  const [specContent, setSpecContent] = useState('');
  const [specLoading, setSpecLoading] = useState(false);
  const [specSaving, setSpecSaving] = useState(false);

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
      setNewSourceName('');
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
      loadSources();
      if (editingSource === deleteTarget) {
        setEditingSource(null);
        setSpecContent('');
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const loadSpec = async (sourceName: string) => {
    setEditingSource(sourceName);
    setSpecLoading(true);
    try {
      const r = await api.getSpec(domain, sourceName);
      setSpecContent(r.content);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSpecLoading(false);
    }
  };

  const saveSpec = async () => {
    if (!editingSource) return;
    setSpecSaving(true);
    try {
      await api.uploadSpec(domain, editingSource, specContent);
      loadSources();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSpecSaving(false);
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
            {sources.map((s) => (
              <div key={s.name}>
                <div className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-gray-50 border border-gray-100">
                  <button
                    onClick={() => loadSpec(s.name)}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    {s.name}
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
                    <button
                      onClick={() => setDeleteTarget(s.name)}
                      className="text-red-500 hover:text-red-700 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {editingSource === s.name && (
                  <div className="ml-4 mt-2 p-3 border border-gray-200 rounded-md bg-gray-50">
                    {specLoading ? (
                      <p className="text-gray-500 text-sm">Loading specification...</p>
                    ) : (
                      <>
                        <textarea
                          value={specContent}
                          onChange={(e) => setSpecContent(e.target.value)}
                          rows={12}
                          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-2"
                          placeholder="Enter source specification in markdown..."
                        />
                        <button
                          onClick={saveSpec}
                          disabled={specSaving}
                          className="px-3 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {specSaving ? 'Saving...' : 'Upload / Save Spec'}
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Modal open={showCreateSource} onClose={() => { setShowCreateSource(false); setNewSourceName(''); }} title="Create Source">
        <input
          type="text"
          value={newSourceName}
          onChange={(e) => setNewSourceName(e.target.value)}
          placeholder="Source name..."
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-4"
          autoFocus
          onKeyDown={(e) => e.key === 'Enter' && handleCreateSource()}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={() => { setShowCreateSource(false); setNewSourceName(''); }}
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
