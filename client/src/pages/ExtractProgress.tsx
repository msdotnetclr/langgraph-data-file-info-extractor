import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api, type SSEEvent, type SessionInfo } from '../api/client';
import WorkflowVisualizer from '../components/WorkflowVisualizer';

export default function ExtractProgress() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const routeState = location.state as SessionInfo | null;

  const [phase, setPhase] = useState('Starting...');
  const [progress, setProgress] = useState('');
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [chunkCurrent, setChunkCurrent] = useState(0);
  const [chunkTotal, setChunkTotal] = useState(0);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  useEffect(() => {
    if (!id) return;

    const run = async () => {
      try {
        const res = await api.startExtraction(
          id,
          routeState?.domain,
          routeState?.source,
        );
        if (!res.ok) {
          const detail = (await res.json().catch(() => ({}))) as { detail?: string };
          setError(detail.detail || 'Failed to start extraction');
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) {
          setError('No response body');
          return;
        }
        readerRef.current = reader;

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: SSEEvent = JSON.parse(line.slice(6));
                switch (event.type) {
                  case 'status':
                    if (event.phase === 'starting') {
                      setPhase('Initializing...');
                    } else if (event.phase === 'chunking') {
                      setPhase('Chunking specification file...');
                      setProgress(`Found ${event.chunks} chunks`);
                      setChunkTotal(event.chunks || 0);
                      setActiveNode('split_specification');
                    } else if (event.phase === 'reducing') {
                      setPhase('Reducing results...');
                      setProgress('');
                      setCompletedNodes((prev) => prev.includes('extract_next_chunk') ? prev : [...prev, 'extract_next_chunk']);
                      setActiveNode('reduce_results');
                    }
                    break;
                  case 'progress':
                    setPhase('Extracting fields');
                    setProgress(`Processing chunk ${event.chunk} of ${event.total}`);
                    setChunkCurrent(event.chunk || 0);
                    setCompletedNodes((prev) => prev.includes('split_specification') ? prev : [...prev, 'split_specification']);
                    setActiveNode('extract_next_chunk');
                    break;
                  case 'complete':
                    setPhase('Extraction complete');
                    setProgress('Ready for review');
                    setDone(true);
                    setChunkCurrent(chunkTotal);
                    setCompletedNodes((prev) => {
                      const base = ['split_specification', 'extract_next_chunk', 'reduce_results'];
                      const merged = new Set([...prev, ...base]);
                      return [...merged];
                    });
                    setActiveNode('review_results');
                    setTimeout(() => navigate(`/sessions/${id}/review`), 1500);
                    break;
                  case 'error':
                    setError(event.message || 'Unknown error');
                    reader.cancel();
                    break;
                }
              } catch {
                // Skip unparseable lines
              }
            }
          }
        }
      } catch (e: any) {
        setError(e.message);
      }
    };

    run();

    return () => {
      readerRef.current?.cancel().catch(() => {});
    };
  }, [id, navigate]);

  return (
    <div className="max-w-2xl mx-auto py-12">
      <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">Extraction Progress</h2>

      <WorkflowVisualizer
        activeNode={activeNode}
        completedNodes={completedNodes}
        chunkCurrent={chunkCurrent}
        chunkTotal={chunkTotal}
        defaultVisible
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
        {!error && (
          <>
            <div className="mb-4">
              {done ? (
                <span className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-100 text-green-600 text-2xl">&#10003;</span>
              ) : (
                <div className="inline-block w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              )}
            </div>
            <p className="text-lg font-medium text-gray-800 mb-2">{phase}</p>
            {progress && <p className="text-sm text-gray-500">{progress}</p>}
          </>
        )}
      </div>

      {!done && !error && (
        <div className="mt-4 w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
          <div className="bg-blue-600 h-full rounded-full animate-pulse" style={{ width: '60%' }} />
        </div>
      )}
    </div>
  );
}
