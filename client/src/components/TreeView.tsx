import { useState } from 'react';

interface TreeNode {
  name: string;
  children?: string[];
}

interface TreeViewProps {
  nodes: TreeNode[];
  onSelect: (leaf: { parent: string; name: string }) => void;
}

export default function TreeView({ nodes, onSelect }: TreeViewProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (name: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  return (
    <div>
      {nodes.map((node) => {
        const hasChildren = node.children && node.children.length > 0;
        const isExpanded = expanded.has(node.name);
        return (
          <div key={node.name}>
            <div
              className="flex items-center gap-1 py-1.5 px-2 rounded hover:bg-gray-100 cursor-pointer text-sm"
              onClick={() => toggle(node.name)}
            >
              <span className={`transition-transform text-xs text-gray-500 ${isExpanded ? 'rotate-90' : ''}`}>
                &#9654;
              </span>
              <span className="font-medium text-gray-700">{node.name}</span>
              <span className="text-gray-400 ml-1">({node.children?.length || 0})</span>
            </div>
            {hasChildren && isExpanded && (
              <div className="ml-4">
                {node.children!.map((child) => (
                  <div
                    key={child}
                    className="flex items-center gap-1 py-1 px-2 rounded hover:bg-blue-50 cursor-pointer text-sm"
                    onClick={(e) => { e.stopPropagation(); onSelect({ parent: node.name, name: child }); }}
                  >
                    <span className="w-3" />
                    <span className="text-gray-600">{child}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
