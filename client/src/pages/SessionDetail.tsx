import { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation, Link } from 'react-router-dom';
import { api, type SessionInfo } from '../api/client';

export default function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = location.state as SessionInfo | null;

  const [session, setSession] = useState<SessionInfo | null>(routeState);
  const [loading, setLoading] = useState(!routeState);
  const [error, setError] = useState('');

  useEffect(() => {
    if (routeState) return;
    if (!id) return;
    api.getSession(id)
      .then(setSession)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, routeState]);

  if (loading) return <p className="text-gray-500 py-12 text-center">Loading session...</p>;

  if (error) return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">{error}</div>
    </div>
  );

  if (!session) return null;

  const statusColors: Record<string, string> = {
    created: 'bg-gray-100 text-gray-600',
    in_progress: 'bg-blue-100 text-blue-800',
    draft: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };

  return (
    <div className="max-w-4xl mx-auto py-6">
      <div className="flex items-center gap-2 mb-6">
        <Link to="/sessions" className="text-sm text-blue-600 hover:text-blue-800">Sessions</Link>
        <span className="text-gray-400">/</span>
        <h2 className="text-2xl font-bold text-gray-900">Session</h2>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-gray-500 uppercase">Domain</p>
            <p className="text-sm font-medium text-gray-900">{session.domain}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Source</p>
            <p className="text-sm font-medium text-gray-900">{session.source}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Status</p>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[session.status] || ''}`}>
              {(session.status || '').replace('_', ' ')}
            </span>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase">Created</p>
            <p className="text-sm text-gray-600">{new Date(session.created_at).toLocaleString()}</p>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-100">
          {(session.status === 'created' || session.status === 'draft') && (
            <button
              onClick={() => navigate(`/sessions/${session.session_id}/extract`, { state: session })}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
            >
              {session.status === 'draft' ? 'Re-run Extraction' : 'Start Extraction'}
            </button>
          )}
          {session.status === 'draft' && (
            <button
              onClick={() => navigate(`/sessions/${session.session_id}/review`)}
              className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700"
            >
              View & Review
            </button>
          )}
          {session.status === 'approved' && (
            <button
              onClick={() => navigate(`/sessions/${session.session_id}/review`)}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200"
            >
              View Results
            </button>
          )}
          <Link
            to="/sessions"
            className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            Back
          </Link>
        </div>
      </div>
    </div>
  );
}
