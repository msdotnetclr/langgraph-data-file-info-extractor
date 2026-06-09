import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, type DomainInfo, type SessionInfo } from '../api/client';

export default function Dashboard() {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.listDomains(),
      api.listSessions(),
    ])
      .then(([d, s]) => {
        setDomains(d);
        setSessions(s);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalSources = domains.reduce((s, d) => s + d.source_count, 0);
  const draftCount = sessions.filter((s) => s.status === 'draft').length;
  const approvedCount = sessions.filter((s) => s.status === 'approved').length;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-sm text-gray-500 mb-1">Domains</p>
            <p className="text-3xl font-bold text-gray-900">{domains.length}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-sm text-gray-500 mb-1">Sources</p>
            <p className="text-3xl font-bold text-gray-900">{totalSources}</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <p className="text-sm text-gray-500 mb-1">Sessions</p>
            <p className="text-3xl font-bold text-gray-900">{sessions.length}</p>
            <div className="flex gap-3 mt-2">
              <span className="text-xs text-yellow-700 bg-yellow-100 px-2 py-0.5 rounded-full">
                {draftCount} drafts
              </span>
              <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                {approvedCount} approved
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Link
          to="/domains"
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Manage Domains & Sources
        </Link>
      </div>
    </div>
  );
}
