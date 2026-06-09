import { useState } from 'react';

interface WorkflowVisualizerProps {
  activeNode: string | null;
  completedNodes: string[];
  defaultVisible?: boolean;
  chunkCurrent?: number;
  chunkTotal?: number;
}

function getNodeState(nodeId: string, activeNode: string | null, completedNodes: string[]): 'active' | 'completed' | 'pending' {
  if (nodeId === activeNode) return 'active';
  if (completedNodes.includes(nodeId)) return 'completed';
  return 'pending';
}

function Connector({ state, height }: { state: 'active' | 'completed' | 'pending'; height?: string }) {
  const color = state === 'completed' ? 'bg-green-400' : state === 'active' ? 'bg-yellow-400' : 'bg-gray-300';
  return <div className={`w-0.5 ${height || 'h-4'} ${color} mx-auto transition-colors duration-500`} />;
}

function NodeBox({ label, state, compact, subtitle }: { label: string; state: 'active' | 'completed' | 'pending'; compact?: boolean; subtitle?: string }) {
  const base = compact ? 'px-2.5 py-1.5 text-xs min-w-[130px]' : 'px-4 py-2 text-sm min-w-[180px]';

  const colors = state === 'completed'
    ? 'bg-green-100 border-green-400 text-green-800'
    : state === 'active'
      ? 'bg-yellow-100 border-yellow-400 text-yellow-800 shadow-[0_0_8px_rgba(250,204,21,0.5)]'
      : 'bg-gray-100 border-gray-300 text-gray-500';

  return (
    <div className={`${base} rounded-lg border-2 text-center ${colors} transition-all duration-500`}>
      <span className="font-semibold">
        {label}
      </span>
      {state === 'completed' && <span className="ml-1.5 text-green-600">&#10003;</span>}
      {state === 'active' && <span className="inline-block ml-1.5 w-1.5 h-1.5 rounded-full bg-yellow-500 animate-ping align-middle" />}
      {subtitle && (
        <div className={`text-[10px] mt-0.5 ${state === 'completed' ? 'text-green-600' : state === 'active' ? 'text-yellow-700' : 'text-gray-400'}`}>
          {subtitle}
        </div>
      )}
    </div>
  );
}

function BranchConnector({ leftState, rightState }: { leftState: 'active' | 'completed' | 'pending'; rightState: 'active' | 'completed' | 'pending' }) {
  const hColor = leftState === 'completed' && rightState === 'completed' ? 'bg-green-400' : 'bg-gray-300';
  const lColor = leftState === 'completed' ? 'bg-green-400' : leftState === 'active' ? 'bg-yellow-400' : 'bg-gray-300';
  const rColor = rightState === 'completed' ? 'bg-green-400' : rightState === 'active' ? 'bg-yellow-400' : 'bg-gray-300';

  return (
    <div className="relative w-full" style={{ height: '32px' }}>
      <div className={`absolute left-1/2 w-0.5 h-3 ${hColor} transition-colors duration-500`} style={{ top: 0, marginLeft: '-1px' }} />
      <div className={`absolute h-0.5 ${hColor} transition-colors duration-500`} style={{ top: 12, left: '22%', right: '22%' }} />
      <div className={`absolute w-0.5 h-5 ${lColor} transition-colors duration-500`} style={{ top: 12, left: '22%' }} />
      <div className={`absolute w-0.5 h-5 ${rColor} transition-colors duration-500`} style={{ top: 12, right: '22%' }} />
      <span className="absolute text-[10px] text-gray-400" style={{ top: 14, left: '23%', transform: 'translateY(-100%)' }}>approved</span>
      <span className="absolute text-[10px] text-gray-400" style={{ top: 14, right: '23%', transform: 'translateY(-100%)' }}>rejected</span>
    </div>
  );
}

function LoopArrow({ label, right, top, visible }: { label: string; right: number; top: number; visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="absolute" style={{ right: `${right}px`, top: `${top}px` }}>
      <svg width="100" height="44" className="text-gray-400">
        <path
          d="M 90,5 L 10,5 Q 0,5 0,15 L 0,22 Q 0,32 10,32 L 30,32"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          markerEnd="url(#arrowGray)"
        />
        <text x="45" y="18" className="text-[10px] fill-gray-400" textAnchor="middle">{label}</text>
        <defs>
          <marker id="arrowGray" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0,0 L 10,5 L 0,10 z" fill="currentColor" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

function FeedbackLoopArrow({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="flex justify-center">
      <svg width="200" height="60" className="text-gray-400">
        <path
          d="M 190,5 L 50,5 Q 20,5 20,25 L 20,45 Q 20,55 50,55 L 170,55"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeDasharray="5,3"
          markerEnd="url(#arrowGray2)"
        />
        <text x="100" y="2" className="text-[10px] fill-gray-400" textAnchor="middle">back to start (re-run)</text>
        <defs>
          <marker id="arrowGray2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0,0 L 10,5 L 0,10 z" fill="currentColor" />
          </marker>
        </defs>
      </svg>
    </div>
  );
}

export default function WorkflowVisualizer({ activeNode, completedNodes, defaultVisible, chunkCurrent, chunkTotal }: WorkflowVisualizerProps) {
  const [visible, setVisible] = useState(defaultVisible ?? false);

  const splitState = getNodeState('split_specification', activeNode, completedNodes);
  const extractState = getNodeState('extract_next_chunk', activeNode, completedNodes);
  const reduceState = getNodeState('reduce_results', activeNode, completedNodes);
  const reviewState = getNodeState('review_results', activeNode, completedNodes);
  const storeState = getNodeState('store_approved_result', activeNode, completedNodes);
  const feedbackState = getNodeState('incorporate_feedback', activeNode, completedNodes);

  const showChunkLoop = extractState === 'active' || (extractState === 'completed' && splitState === 'completed');
  const showFeedbackLoop = feedbackState === 'active' || feedbackState === 'completed';

  let chunkSubtitle: string | undefined;
  if (chunkCurrent && chunkTotal) {
    if (extractState === 'completed') {
      chunkSubtitle = `All ${chunkTotal} chunks processed`;
    } else if (extractState === 'active') {
      chunkSubtitle = `Processing chunk ${chunkCurrent} of ${chunkTotal}`;
    }
  }

  if (!visible) {
    return (
      <button
        onClick={() => setVisible(true)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
        Show Workflow
      </button>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-700">Workflow</h3>
          <div className="flex items-center gap-2 text-[10px]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-yellow-400" /> Active
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-400" /> Done
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-300" /> Pending
            </span>
          </div>
        </div>
        <button
          onClick={() => setVisible(false)}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Hide
        </button>
      </div>

      <div className="flex flex-col items-center">
        {/* START */}
        <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center text-[10px] font-bold bg-gray-50 border-gray-300 text-gray-500 transition-colors duration-500 ${completedNodes.length > 0 ? 'bg-green-100 border-green-400 text-green-700' : ''}`}>
          START
        </div>
        <Connector state={splitState} height="h-5" />

        {/* split_specification */}
        <NodeBox label="split_specification" state={splitState} />
        <Connector state={extractState} height="h-5" />

        {/* extract_next_chunk */}
        <div className="relative">
          <NodeBox label="extract_next_chunk" state={extractState} subtitle={chunkSubtitle} />
          <LoopArrow
            label="while more chunks"
            right={-95}
            top={0}
            visible={showChunkLoop}
          />
        </div>
        <Connector state={reduceState} height="h-5" />

        {/* reduce_results */}
        <NodeBox label="reduce_results" state={reduceState} />
        <Connector state={reviewState} height="h-5" />

        {/* review_results */}
        <NodeBox label="review_results" state={reviewState} />
        <BranchConnector leftState={storeState} rightState={feedbackState} />

        {/* Branch: store_approved_result and incorporate_feedback */}
        <div className="flex w-full">
          <div className="flex-1 flex flex-col items-center">
            <NodeBox label="store_approved_result" state={storeState} compact />
            {storeState === 'completed' && (
              <div className="flex flex-col items-center">
                <Connector state="completed" />
                <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center text-[10px] font-bold bg-green-100 border-green-400 text-green-700 transition-colors duration-500`}>
                  END
                </div>
              </div>
            )}
          </div>
          <div className="flex-1 flex flex-col items-center">
            <NodeBox label="incorporate_feedback" state={feedbackState} compact />
          </div>
        </div>

        <FeedbackLoopArrow visible={showFeedbackLoop} />
      </div>
    </div>
  );
}
