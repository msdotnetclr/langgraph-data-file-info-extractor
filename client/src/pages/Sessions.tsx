import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, type SessionInfo, type InputTreeNode } from '../api/client';
import Modal from '../components/Modal';
import TreeView from '../components/TreeView';

export default function Sessions() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('draft');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [inputTree, setInputTree] = useState<InputTreeNode[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    api.listSessions(statusFilter || undefined)
      .then(setSessions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleCreate = async () => {
    if (!selectedDomain || !selectedSource) return;
    setCreating(true);
    try {
      const session = await api.createSession(selectedDomain, selectedSource);
      setShowCreate(false);
      setSelectedDomain('');
      setSelectedSource('');
      navigate(`/sessions/${session.session_id}`, { state: session });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteSession(deleteTarget);
      setDeleteTarget(null);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const openCreate = () => {
    setShowCreate(true);
    setTreeLoading(true);
    api.getInputTree()
      .then(setInputTree)
      .catch((e) => setError(e.message))
      .finally(() => setTreeLoading(false));
  };

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      draft: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      in_progress: 'bg-blue-100 text-blue-800',
      created: 'bg-gray-100 text-gray-600',
      failed: 'bg-red-100 text-red-800',
    };
    return `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-600'}`;
  };

  const filters = [
    { label: 'Drafts', value: 'draft' },
    { label: 'Approved', value: 'approved' },
    { label: 'All', value: '' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Sessions</h2>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + New Session
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4">
          {error}
          <button onClick={() => setError('')} className="float-right font-bold">&times;</button>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setStatusFilter(f.value)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              statusFilter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No sessions found</p>
          <p>Create a new session to start extraction.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Domain</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Source</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Status</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-600">Modified</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-800">{s.domain}</td>
                  <td className="px-4 py-3 text-sm text-gray-800">{s.source}</td>
                  <td className="px-4 py-3">
                    <span className={statusBadge(s.status)}>{s.status.replace('_', ' ')}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(s.last_modified_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link
                      to={`/sessions/${s.session_id}`}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      View
                    </Link>
                    <button
                      onClick={() => setDeleteTarget(s.session_id)}
                      className="text-red-500 hover:text-red-700 text-sm font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={showCreate} onClose={() => { setShowCreate(false); setSelectedDomain(''); setSelectedSource(''); }} title="New Session">
        <p className="text-sm text-gray-600 mb-4">Select a domain and source to create a new extraction session:</p>
        {treeLoading ? (
          <p className="text-gray-500 text-sm">Loading...</p>
        ) : inputTree.length === 0 ? (
          <p className="text-gray-500 text-sm mb-4">
            No domains or sources found.{' '}
            <Link to="/domains" className="text-blue-600 hover:text-blue-800">Create them first</Link>.
          </p>
        ) : (
          <div className="border border-gray-200 rounded-md max-h-64 overflow-y-auto mb-4">
            <TreeView
              nodes={inputTree.map((d) => ({
                name: d.domain,
                children: d.sources,
              }))}
              onSelect={(leaf) => {
                setSelectedDomain(leaf.parent!);
                setSelectedSource(leaf.name);
              }}
            />
          </div>
        )}
        {selectedDomain && selectedSource && (
          <p className="text-sm text-gray-700 mb-4">
            Selected: <strong>{selectedDomain}</strong> / <strong>{selectedSource}</strong>
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={() => { setShowCreate(false); setSelectedDomain(''); setSelectedSource(''); }}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating || !selectedDomain || !selectedSource}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {creating ? 'Creating...' : 'Create Session'}
          </button>
        </div>
      </Modal>

      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title="Delete Session">
        <p className="text-sm text-gray-600 mb-4">
          Are you sure you want to delete this session? This action cannot be undone.
        </p>
        <div className="flex justify-end gap-2">
          <button onClick={() => setDeleteTarget(null)} className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900">
            Cancel
          </button>
          <button onClick={handleDelete} className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700">
            Delete
          </button>
        </div>
      </Modal>
    </div>
  );
}
