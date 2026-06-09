import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api, type ReviewData, type FeedbackRound } from '../api/client';
import WorkflowVisualizer from '../components/WorkflowVisualizer';
import LinedContent from '../components/LinedContent';

export default function Review() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'summary' | 'fields' | 'warnings' | 'raw'>('summary');
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [expandedFeedback, setExpandedFeedback] = useState<Set<number>>(new Set());
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);

  const load = () => {
    if (!id) return;
    setLoading(true);
    api.getReviewData(id)
      .then((d) => {
        setData(d);
        if (d.status === 'approved') {
          setCompletedNodes(['split_specification', 'extract_next_chunk', 'reduce_results', 'review_results', 'store_approved_result']);
          setActiveNode(null);
        } else {
          setCompletedNodes(['split_specification', 'extract_next_chunk', 'reduce_results']);
          setActiveNode('review_results');
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleSubmit = async (decision: 'approved' | 'rejected') => {
    if (!id) return;
    setSubmitting(true);
    try {
      await api.submitReview(
        id,
        decision === 'approved' ? 'approved' : 'rejected',
        decision === 'rejected' ? feedback : ''
      );
      if (decision === 'approved') {
        setCompletedNodes((prev) => {
          const next = [...prev, 'review_results'];
          return next.includes('store_approved_result') ? next : [...next, 'store_approved_result'];
        });
        setActiveNode('store_approved_result');
        setData((prev) => prev ? { ...prev, status: 'approved' } : prev);
        setTimeout(() => {
          setActiveNode(null);
          setCompletedNodes((prev) => prev.includes('store_approved_result') ? prev : [...prev, 'store_approved_result']);
          navigate('/sessions');
        }, 1500);
      } else {
        setCompletedNodes((prev) => {
          const next = [...prev, 'review_results'];
          return next.includes('incorporate_feedback') ? next : next;
        });
        setActiveNode('incorporate_feedback');
        setFeedback('');
        setShowFeedback(false);
        setData(null);
        setLoading(true);
        setSubmitting(false);
        setTimeout(() => load(), 500);
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="text-gray-500 py-12 text-center">Loading review data...</p>;

  if (error) return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">{error}</div>
    </div>
  );

  if (!data) return null;

  const { result, feedback_rounds, domain, source, status } = data;
  const tabs = [
    { key: 'summary' as const, label: 'Summary' },
    { key: 'fields' as const, label: `Fields (${result.fields?.length || 0})` },
    { key: 'warnings' as const, label: `Warnings (${result.warnings?.length || 0})` },
    { key: 'raw' as const, label: 'Raw JSON' },
  ];

  return (
    <div className="max-w-6xl mx-auto py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Review Results</h2>
          <p className="text-sm text-gray-500 mt-1">
            <Link to="/sessions" className="text-blue-600 hover:text-blue-800">Sessions</Link>
            {' / '}
            <strong>{domain}</strong> / <strong>{source}</strong>
          </p>
        </div>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
        }`}>
          {status === 'approved' ? 'Approved' : 'Draft - Awaiting Review'}
        </span>
      </div>

      {feedback_rounds.length > 0 && (
        <div className="mb-6 bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Feedback History</h3>
          {feedback_rounds.map((fr: FeedbackRound) => (
            <div key={fr.round} className="mb-2 last:mb-0">
              <button
                onClick={() => {
                  setExpandedFeedback((prev) => {
                    const next = new Set(prev);
                    next.has(fr.round) ? next.delete(fr.round) : next.add(fr.round);
                    return next;
                  });
                }}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
              >
                <span className={expandedFeedback.has(fr.round) ? 'rotate-90' : ''}>&#9654;</span>
                Round {fr.round} — {new Date(fr.timestamp).toLocaleString()}
              </button>
              {expandedFeedback.has(fr.round) && (
                <pre className="mt-1 ml-6 p-2 bg-gray-50 rounded text-xs text-gray-700 whitespace-pre-wrap font-mono">
                  {fr.feedback_text}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      <WorkflowVisualizer
        activeNode={activeNode}
        completedNodes={completedNodes}
      />

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-6">
        <div className="flex border-b border-gray-200">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === 'summary' && (
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(result.file_metadata || {}).map(([k, v]) => (
                <div key={k} className="bg-gray-50 rounded-md p-3">
                  <p className="text-xs text-gray-500 uppercase mb-1">{k.replace(/_/g, ' ')}</p>
                  <p className="text-sm font-medium text-gray-900">{v || <span className="text-gray-400">—</span>}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'fields' && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left px-3 py-2 text-gray-600 font-medium">#</th>
                    <th className="text-left px-3 py-2 text-gray-600 font-medium">Group</th>
                    <th className="text-left px-3 py-2 text-gray-600 font-medium">Name</th>
                    <th className="text-left px-3 py-2 text-gray-600 font-medium">Type</th>
                    <th className="text-left px-3 py-2 text-gray-600 font-medium">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.fields || []).map((f: any, i: number) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-500">{f.field_index ?? '—'}</td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                          f.field_group === 'header' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                        }`}>
                          {f.field_group}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-medium text-gray-800">{f.field_name}</td>
                      <td className="px-3 py-2 text-gray-600 font-mono text-xs">{f.data_type}</td>
                      <td className="px-3 py-2 text-gray-600 max-w-md truncate" title={f.description}>
                        {f.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'warnings' && (
            <div>
              {(result.warnings || []).length === 0 ? (
                <p className="text-gray-500 text-sm py-4">No warnings.</p>
              ) : (
                <ul className="space-y-1">
                  {result.warnings.map((w: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 rounded-md px-3 py-2">
                      <span className="text-amber-500 mt-0.5">&#9888;</span>
                      {w}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {activeTab === 'raw' && (
            <LinedContent content={JSON.stringify(result, null, 2)} />
          )}
        </div>
      </div>

      {status === 'draft' && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          {showFeedback ? (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Provide Feedback for Re-run</h3>
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={6}
                placeholder="Describe what needs to be improved in the extraction. This feedback will be added as domain-specific instructions for the next run."
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent mb-3"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleSubmit('rejected')}
                  disabled={submitting || !feedback.trim()}
                  className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? 'Submitting...' : 'Submit Feedback & Re-run'}
                </button>
                <button
                  onClick={() => { setShowFeedback(false); setFeedback(''); }}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleSubmit('approved')}
                disabled={submitting}
                className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
              >
                {submitting ? 'Approving...' : 'Approve'}
              </button>
              <button
                onClick={() => setShowFeedback(true)}
                className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700"
              >
                Re-run with Feedback
              </button>
              <Link
                to={`/sessions`}
                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
              >
                Back to Sessions
              </Link>
            </div>
          )}
        </div>
      )}

      {status === 'approved' && (
        <div className="bg-green-50 border border-green-200 rounded-md px-4 py-3 text-green-800 text-sm flex items-center gap-2">
          <span className="text-lg">&#10003;</span>
          This session has been approved. Result saved to output store.
          <Link to="/sessions" className="ml-auto text-blue-600 hover:text-blue-800 font-medium">Back to Sessions</Link>
        </div>
      )}
    </div>
  );
}
