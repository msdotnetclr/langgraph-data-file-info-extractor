import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, OutputTreeNode } from '../api/client';

export default function Outputs() {
  const [tree, setTree] = useState<OutputTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedDomain, setExpandedDomain] = useState<Set<string>>(new Set());
  const [expandedSource, setExpandedSource] = useState<Set<string>>(new Set());
  const [selectedOutput, setSelectedOutput] = useState<Record<string, unknown> | null>(null);
  const [selLabel, setSelLabel] = useState('');

  useEffect(() => {
    api.listOutputTree()
      .then(setTree)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const toggleDomain = (d: string) => {
    setExpandedDomain((prev) => {
      const next = new Set(prev);
      next.has(d) ? next.delete(d) : next.add(d);
      return next;
    });
  };

  const toggleSource = (s: string) => {
    setExpandedSource((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });
  };

  const viewOutput = async (domain: string, source: string, filename: string) => {
    try {
      const data = await api.getOutput(domain, source, filename);
      setSelectedOutput(data);
      setSelLabel(`${domain} / ${source} / ${filename}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Output Store</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4">
          {error}
          <button onClick={() => setError('')} className="float-right font-bold">&times;</button>
        </div>
      )}

      <div className="flex gap-6">
        <div className="w-80 flex-shrink-0">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Browse</h3>
            {loading ? (
              <p className="text-gray-500 text-sm">Loading...</p>
            ) : tree.length === 0 ? (
              <p className="text-gray-500 text-sm py-4">
                No approved outputs yet. Outputs are saved when a session is approved.
              </p>
            ) : (
              tree.map((d) => (
                <div key={d.domain}>
                  <button
                    onClick={() => toggleDomain(d.domain)}
                    className="flex items-center gap-1 py-1.5 text-sm font-medium text-gray-700 hover:text-gray-900 w-full text-left"
                  >
                    <span className={`text-xs transition-transform ${expandedDomain.has(d.domain) ? 'rotate-90' : ''}`}>
                      &#9654;
                    </span>
                    {d.domain}
                  </button>
                  {expandedDomain.has(d.domain) && (
                    <div className="ml-4">
                      {d.sources.map((s) => (
                        <div key={s.name}>
                          <button
                            onClick={() => toggleSource(`${d.domain}/${s.name}`)}
                            className="flex items-center gap-1 py-1 text-sm text-gray-600 hover:text-gray-900 w-full text-left"
                          >
                            <span className={`text-xs transition-transform ${expandedSource.has(`${d.domain}/${s.name}`) ? 'rotate-90' : ''}`}>
                              &#9654;
                            </span>
                            {s.name} ({s.outputs.length})
                          </button>
                          {expandedSource.has(`${d.domain}/${s.name}`) && (
                            <div className="ml-4">
                              {s.outputs.map((f) => (
                                <button
                                  key={f}
                                  onClick={() => viewOutput(d.domain, s.name, f)}
                                  className="block py-1 text-sm text-blue-600 hover:text-blue-800 w-full text-left truncate"
                                  title={f}
                                >
                                  {f.replace('.json', '')}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="flex-1">
          {selectedOutput ? (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">{selLabel}</h3>
                <button onClick={() => setSelectedOutput(null)} className="text-sm text-gray-400 hover:text-gray-600">&times;</button>
              </div>

              {selectedOutput.file_metadata && (
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {Object.entries(selectedOutput.file_metadata as Record<string, unknown>).map(([k, v]) => (
                    <div key={k} className="bg-gray-50 rounded-md p-2">
                      <p className="text-xs text-gray-500 uppercase">{k.replace(/_/g, ' ')}</p>
                      <p className="text-sm font-medium text-gray-900">{String(v ?? '—')}</p>
                    </div>
                  ))}
                </div>
              )}

              {selectedOutput.fields && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-100">
                        <th className="text-left px-2 py-1.5 text-gray-600 font-medium">#</th>
                        <th className="text-left px-2 py-1.5 text-gray-600 font-medium">Group</th>
                        <th className="text-left px-2 py-1.5 text-gray-600 font-medium">Name</th>
                        <th className="text-left px-2 py-1.5 text-gray-600 font-medium">Type</th>
                        <th className="text-left px-2 py-1.5 text-gray-600 font-medium">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedOutput.fields as Array<Record<string, unknown>>).map((f: any, i: number) => (
                        <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                          <td className="px-2 py-1.5 text-gray-500">{f.field_index ?? '—'}</td>
                          <td className="px-2 py-1.5">
                            <span className={`inline-flex items-center px-1 rounded text-xs font-medium ${
                              f.field_group === 'header' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                            }`}>
                              {f.field_group}
                            </span>
                          </td>
                          <td className="px-2 py-1.5 font-medium text-gray-800">{f.field_name}</td>
                          <td className="px-2 py-1.5 text-gray-600 font-mono">{f.data_type}</td>
                          <td className="px-2 py-1.5 text-gray-500 truncate max-w-xs" title={f.description}>{f.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <details className="mt-4">
                <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">Raw JSON</summary>
                <pre className="mt-2 bg-gray-50 rounded-md p-3 text-xs text-gray-700 overflow-auto max-h-64 font-mono">
                  {JSON.stringify(selectedOutput, null, 2)}
                </pre>
              </details>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
              <p>Select an output file to view its contents.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
