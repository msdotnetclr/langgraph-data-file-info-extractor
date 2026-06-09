import { useEffect, useState } from 'react';
import {
  api,
  type OutputTreeNode,
  type VersionEntry,
  type OutputWithVersion,
  type VersionDiff,
  type VersionChainItem,
} from '../api/client';

type DetailView = 'versions' | 'diff';

export default function Outputs() {
  const [tree, setTree] = useState<OutputTreeNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [expandedDomain, setExpandedDomain] = useState<Set<string>>(new Set());
  const [expandedSource, setExpandedSource] = useState<Set<string>>(new Set());
  const [selectedDomain, setSelectedDomain] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [versions, setVersions] = useState<VersionEntry[]>([]);
  const [latestVersion, setLatestVersion] = useState(0);
  const [loadingVersions, setLoadingVersions] = useState(false);

  const [view, setView] = useState<DetailView>('versions');
  const [selV1, setSelV1] = useState(0);
  const [selV2, setSelV2] = useState(0);

  const [output, setOutput] = useState<OutputWithVersion | null>(null);
  const [chain, setChain] = useState<VersionChainItem[]>([]);
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

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

  const toggleSource = async (domain: string, source: string) => {
    const key = `${domain}/${source}`;
    const wasExpanded = expandedSource.has(key);

    setExpandedSource((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

    if (!wasExpanded) {
      setSelectedDomain(domain);
      setSelectedSource(source);
      setLoadingVersions(true);
      try {
        const data = await api.listOutputVersions(domain, source);
        setVersions(data.versions);
        setLatestVersion(data.latest_version);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoadingVersions(false);
      }
    }
  };

  const viewVersion = async (version: number) => {
    setView('versions');
    setDiff(null);
    setLoadingDetail(true);
    try {
      const [out, chainData] = await Promise.all([
        api.getOutputByVersion(selectedDomain, selectedSource, version),
        api.getVersionChain(selectedDomain, selectedSource, version),
      ]);
      setOutput(out);
      setChain(chainData.chain);
      setSelV1(version);
      setSelV2(0);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const viewLatest = async () => {
    if (!latestVersion) return;
    setView('versions');
    setDiff(null);
    setLoadingDetail(true);
    try {
      const [out, chainData] = await Promise.all([
        api.getLatestOutput(selectedDomain, selectedSource),
        api.getVersionChain(selectedDomain, selectedSource),
      ]);
      setOutput(out);
      setChain(chainData.chain);
      setSelV1(latestVersion);
      setSelV2(0);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const compareVersions = async () => {
    if (!selV1 || !selV2 || selV1 === selV2) return;
    setView('diff');
    setOutput(null);
    setLoadingDetail(true);
    try {
      const d = await api.diffOutputs(selectedDomain, selectedSource, selV1, selV2);
      setDiff(d);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingDetail(false);
    }
  };

  const swapDiff = () => {
    setSelV1(selV2);
    setSelV2(selV1);
    compareVersions();
  };

  // Reset diff when comparing changes trigger re-fetch
  useEffect(() => {
    if (view === 'diff' && selV1 && selV2 && selV1 !== selV2) {
      compareVersions();
    }
  }, [view]);

  const renderFileMetadata = (metadata: Record<string, unknown>) => (
    <div className="grid grid-cols-2 gap-3 mb-4">
      {Object.entries(metadata).map(([k, v]) => (
        <div key={k} className="bg-gray-50 rounded-md p-2">
          <p className="text-xs text-gray-500 uppercase">{k.replace(/_/g, ' ')}</p>
          <p className="text-sm font-medium text-gray-900">{String(v ?? '\u2014')}</p>
        </div>
      ))}
    </div>
  );

  const renderFieldsTable = (fields: Array<Record<string, unknown>>) => (
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
          {(fields as Array<Record<string, unknown>>).map((f: any, i: number) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="px-2 py-1.5 text-gray-500">{f.field_index ?? '\u2014'}</td>
              <td className="px-2 py-1.5">
                <span
                  className={`inline-flex items-center px-1 rounded text-xs font-medium ${
                    f.field_group === 'header'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  {f.field_group}
                </span>
              </td>
              <td className="px-2 py-1.5 font-medium text-gray-800">{f.field_name}</td>
              <td className="px-2 py-1.5 text-gray-600 font-mono">{f.data_type}</td>
              <td className="px-2 py-1.5 text-gray-500 truncate max-w-xs" title={f.description}>
                {f.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const hasMetadataDiff = (d: VersionDiff) => {
    const { added, removed, changed } = d.file_metadata;
    return Object.keys(added).length + Object.keys(removed).length + Object.keys(changed).length > 0;
  };

  const hasFieldsDiff = (d: VersionDiff) => {
    return d.fields.added.length + d.fields.removed.length + d.fields.changed.length > 0;
  };

  const hasWarningsDiff = (d: VersionDiff) => {
    return d.warnings.added.length + d.warnings.removed.length > 0;
  };

  const renderDiff = () => {
    if (!diff) return null;

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">
            Comparing v{diff.v1} <span className="text-gray-400">vs</span> v{diff.v2}
          </span>
          <button
            onClick={swapDiff}
            className="text-xs text-blue-600 hover:text-blue-800"
            title="Swap comparison direction"
          >
            &#8644; Swap
          </button>
          <span className="text-xs text-gray-400">
            v{diff.v1}: {diff.v1_session_id.slice(0, 8)}... &middot; v{diff.v2}: {diff.v2_session_id.slice(0, 8)}...
          </span>
        </div>

        {/* Metadata diff */}
        {hasMetadataDiff(diff) && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">File Metadata Changes</h4>
            <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-3 py-1.5 text-gray-600">Attribute</th>
                    <th className="text-left px-3 py-1.5 text-gray-600">v{diff.v1}</th>
                    <th className="text-left px-3 py-1.5 text-gray-600">v{diff.v2}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(diff.file_metadata.changed).map(([key, { old, new: nv }]) => (
                    <tr key={key} className="border-b border-gray-100">
                      <td className="px-3 py-1.5 font-medium text-gray-700">{key}</td>
                      <td className="px-3 py-1.5 text-red-600 bg-red-50 line-through">
                        {String(old ?? '\u2014')}
                      </td>
                      <td className="px-3 py-1.5 text-green-700 bg-green-50">
                        {String(nv ?? '\u2014')}
                      </td>
                    </tr>
                  ))}
                  {Object.entries(diff.file_metadata.added).map(([key, val]) => (
                    <tr key={`add-${key}`} className="border-b border-gray-100">
                      <td className="px-3 py-1.5 font-medium text-gray-700">{key}</td>
                      <td className="px-3 py-1.5 text-gray-400">\u2014</td>
                      <td className="px-3 py-1.5 text-green-700 bg-green-50">
                        + {String(val)}
                      </td>
                    </tr>
                  ))}
                  {Object.entries(diff.file_metadata.removed).map(([key, val]) => (
                    <tr key={`del-${key}`} className="border-b border-gray-100">
                      <td className="px-3 py-1.5 font-medium text-gray-700">{key}</td>
                      <td className="px-3 py-1.5 text-red-600 bg-red-50 line-through">
                        - {String(val)}
                      </td>
                      <td className="px-3 py-1.5 text-gray-400">\u2014</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Fields diff */}
        {hasFieldsDiff(diff) && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Field Changes
              <span className="ml-2 text-xs font-normal text-gray-400">
                +{diff.fields.added.length} added &middot; -{diff.fields.removed.length} removed
                &middot; ~{diff.fields.changed.length} modified
              </span>
            </h4>
            <div className="space-y-2">
              {diff.fields.added.map((f: any, i) => (
                <div key={`add-${i}`} className="bg-green-50 border border-green-200 rounded-md px-3 py-2">
                  <span className="text-xs font-semibold text-green-700">+ ADDED</span>
                  <span className="ml-2 text-xs text-gray-700">
                    [{f.field_group}] {f.field_name} ({f.data_type})
                  </span>
                </div>
              ))}
              {diff.fields.removed.map((f: any, i) => (
                <div key={`del-${i}`} className="bg-red-50 border border-red-200 rounded-md px-3 py-2">
                  <span className="text-xs font-semibold text-red-600">- REMOVED</span>
                  <span className="ml-2 text-xs text-gray-700 line-through">
                    [{f.field_group}] {f.field_name} ({f.data_type})
                  </span>
                </div>
              ))}
              {diff.fields.changed.map((item, i) => (
                <div key={`chg-${i}`} className="bg-yellow-50 border border-yellow-200 rounded-md px-3 py-2">
                  <span className="text-xs font-semibold text-yellow-700">~ MODIFIED</span>
                  <span className="ml-2 text-xs text-gray-700">
                    [{item.key.field_group}] {item.key.field_name}
                  </span>
                  <div className="mt-1 ml-4 text-xs space-y-0.5">
                    {Object.entries(item.changes).map(([attr, { old, new: nv }]) => (
                      <div key={attr} className="flex gap-2">
                        <span className="text-gray-500 w-24 shrink-0">{attr}:</span>
                        <span className="text-red-600 bg-red-50 px-1 rounded line-through">
                          {String(old ?? '\u2014')}
                        </span>
                        <span className="text-gray-400">&rarr;</span>
                        <span className="text-green-700 bg-green-50 px-1 rounded">
                          {String(nv ?? '\u2014')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Warnings diff */}
        {hasWarningsDiff(diff) && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Warning Changes
              <span className="ml-2 text-xs font-normal text-gray-400">
                +{diff.warnings.added.length} added &middot; -{diff.warnings.removed.length} removed
              </span>
            </h4>
            <div className="space-y-1">
              {diff.warnings.added.map((w, i) => (
                <div key={`aw-${i}`} className="bg-green-50 border border-green-200 rounded-md px-3 py-1.5 text-xs">
                  <span className="text-green-700 font-semibold">+ </span>
                  <span className="text-gray-700">{w}</span>
                </div>
              ))}
              {diff.warnings.removed.map((w, i) => (
                <div key={`rw-${i}`} className="bg-red-50 border border-red-200 rounded-md px-3 py-1.5 text-xs">
                  <span className="text-red-600 font-semibold">- </span>
                  <span className="text-gray-700 line-through">{w}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!hasMetadataDiff(diff) && !hasFieldsDiff(diff) && !hasWarningsDiff(diff) && (
          <div className="bg-gray-50 border border-gray-200 rounded-md p-6 text-center text-gray-500 text-sm">
            No differences found between v{diff.v1} and v{diff.v2}
          </div>
        )}
      </div>
    );
  };

  const renderVersionChain = () => {
    if (!chain.length) return null;

    return (
      <div className="flex items-center gap-1 mb-3 flex-wrap">
        <span className="text-xs text-gray-400 mr-1">Chain:</span>
        {chain.map((item, i) => {
          const isLatest = item.version === latestVersion;
          const isCurrent = item.version === output?.version;
          return (
            <span key={item.version} className="flex items-center gap-1">
              {i > 0 && <span className="text-gray-300 text-xs">&rarr;</span>}
              <button
                onClick={() => viewVersion(item.version)}
                className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium transition-colors ${
                  isCurrent
                    ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
                title={`Session: ${item.session_id.slice(0, 8)}...`}
              >
                v{item.version}
                {item.is_based_on_feedback && (
                  <span className="text-orange-500" title={`${item.feedback_rounds} feedback round(s)`}>
                    &#9998;
                  </span>
                )}
                {isLatest && (
                  <span className="text-green-600 text-[10px] font-bold">LATEST</span>
                )}
              </button>
            </span>
          );
        })}
      </div>
    );
  };

  const renderVersionSelector = () => {
    if (versions.length < 2) return null;
    return (
      <div className="flex items-center gap-2 mb-3 text-xs">
        <select
          value={selV1}
          onChange={(e) => setSelV1(Number(e.target.value))}
          className="border border-gray-300 rounded px-2 py-1 text-gray-700"
        >
          <option value={0}>Select version...</option>
          {versions.map((v) => (
            <option key={v.version} value={v.version}>
              v{v.version} {v.version === latestVersion ? '(latest)' : ''}
            </option>
          ))}
        </select>
        <span className="text-gray-400">vs</span>
        <select
          value={selV2}
          onChange={(e) => setSelV2(Number(e.target.value))}
          className="border border-gray-300 rounded px-2 py-1 text-gray-700"
        >
          <option value={0}>Select version...</option>
          {versions.map((v) => (
            <option key={v.version} value={v.version}>
              v{v.version} {v.version === latestVersion ? '(latest)' : ''}
            </option>
          ))}
        </select>
        <button
          onClick={compareVersions}
          disabled={!selV1 || !selV2 || selV1 === selV2}
          className="bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          Compare
        </button>
      </div>
    );
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Output Store</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4">
          {error}
          <button onClick={() => setError('')} className="float-right font-bold">
            &times;
          </button>
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
                    <span
                      className={`text-xs transition-transform ${
                        expandedDomain.has(d.domain) ? 'rotate-90' : ''
                      }`}
                    >
                      &#9654;
                    </span>
                    {d.domain}
                  </button>
                  {expandedDomain.has(d.domain) && (
                    <div className="ml-4">
                      {d.sources.map((s) => (
                        <div key={s.name}>
                          <button
                            onClick={() => toggleSource(d.domain, s.name)}
                            className="flex items-center gap-1 py-1 text-sm text-gray-600 hover:text-gray-900 w-full text-left"
                          >
                            <span
                              className={`text-xs transition-transform ${
                                expandedSource.has(`${d.domain}/${s.name}`) ? 'rotate-90' : ''
                              }`}
                            >
                              &#9654;
                            </span>
                            {s.name}
                            <span className="text-xs text-gray-400 ml-1">
                              v{s.latest_version}
                              {s.total_versions > 1 && (
                                <span title={`${s.total_versions} total versions`}>
                                  {' '}({s.total_versions} versions)
                                </span>
                              )}
                            </span>
                          </button>
                          {expandedSource.has(`${d.domain}/${s.name}`) && (
                            <div className="ml-4">
                              {loadingVersions &&
                              selectedDomain === d.domain &&
                              selectedSource === s.name ? (
                                <p className="text-gray-400 text-xs py-1">Loading versions...</p>
                              ) : (
                                versions.map((v) => (
                                  <button
                                    key={v.version}
                                    onClick={() => viewVersion(v.version)}
                                    className={`flex items-center gap-1.5 py-1 text-sm w-full text-left ${
                                      output?.version === v.version
                                        ? 'text-blue-700 font-medium'
                                        : 'text-blue-600 hover:text-blue-800'
                                    }`}
                                  >
                                    <span className="text-xs">v{v.version}</span>
                                    {v.version === latestVersion && (
                                      <span className="text-[10px] px-1 bg-green-100 text-green-700 rounded font-medium">
                                        LATEST
                                      </span>
                                    )}
                                    {v.feedback_rounds > 0 && (
                                      <span
                                        className="text-[10px] text-orange-500"
                                        title={`${v.feedback_rounds} feedback round(s)`}
                                      >
                                        &#9998;{v.feedback_rounds}
                                      </span>
                                    )}
                                  </button>
                                ))
                              )}
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
          {view === 'diff' && diff ? (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">
                  Diff: {selectedDomain}/{selectedSource}
                </h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setView('versions'); }}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    &larr; Back to versions
                  </button>
                </div>
              </div>
              {renderDiff()}
            </div>
          ) : output ? (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">
                    {selectedDomain}/{selectedSource} &mdash; v{output.version}
                    {output.version === latestVersion && (
                      <span className="ml-2 text-[10px] px-1.5 bg-green-100 text-green-700 rounded font-bold">
                        LATEST
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Session: {output.session_id.slice(0, 8)}... &middot;{' '}
                    {new Date(output.created_at).toLocaleString()}
                    {output.based_on_version && (
                      <span> &middot; Based on v{output.based_on_version}</span>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => setOutput(null)}
                  className="text-sm text-gray-400 hover:text-gray-600"
                >
                  &times;
                </button>
              </div>

              {renderVersionChain()}
              {renderVersionSelector()}

              {loadingDetail ? (
                <p className="text-gray-500 text-sm py-4">Loading...</p>
              ) : (
                <>
                  {output.data.file_metadata &&
                    Object.keys(output.data.file_metadata as Record<string, unknown>).length > 0 &&
                    renderFileMetadata(output.data.file_metadata as Record<string, unknown>)}

                  {output.data.fields &&
                    (output.data.fields as Array<Record<string, unknown>>).length > 0 &&
                    renderFieldsTable(output.data.fields as Array<Record<string, unknown>>)}

                  {output.data.warnings &&
                    (output.data.warnings as string[]).length > 0 && (
                      <div className="mt-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-1">Warnings</h4>
                        <ul className="list-disc list-inside text-xs text-amber-700 space-y-0.5">
                          {(output.data.warnings as string[]).map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                  <details className="mt-4">
                    <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
                      Raw JSON
                    </summary>
                    <pre className="mt-2 bg-gray-50 rounded-md p-3 text-xs text-gray-700 overflow-auto max-h-64 font-mono">
                      {JSON.stringify(output.data, null, 2)}
                    </pre>
                  </details>
                </>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-400">
              {selectedDomain ? (
                <div className="space-y-2">
                  <p>
                    {selectedDomain}/{selectedSource} &mdash; {versions.length} version(s)
                  </p>
                  {latestVersion > 0 && (
                    <button
                      onClick={viewLatest}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      View latest version (v{latestVersion})
                    </button>
                  )}
                </div>
              ) : (
                <p>Select a version to view its contents, or compare two versions.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
