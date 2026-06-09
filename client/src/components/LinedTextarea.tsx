import { useRef, useCallback, useEffect } from 'react';

interface LinedTextareaProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  rows?: number;
  className?: string;
  placeholder?: string;
}

export default function LinedTextarea({ value, onChange, rows = 8, className = '', placeholder }: LinedTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const gutterRef = useRef<HTMLDivElement>(null);
  const lines = value.split('\n');
  const digits = String(lines.length || 1).length;

  const syncScroll = useCallback(() => {
    if (textareaRef.current && gutterRef.current) {
      gutterRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  }, []);

  useEffect(() => {
    syncScroll();
  }, [value, syncScroll]);

  return (
    <div className={`flex border border-gray-300 rounded-md overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent ${className}`}>
      <div
        ref={gutterRef}
        className="overflow-hidden bg-gray-100 border-r border-gray-200 text-right select-none pt-2 pb-2"
        style={{ minWidth: `${digits * 0.75 + 1.5}rem` }}
      >
        <div className="font-mono text-xs text-gray-400 leading-6 pr-3 pl-2">
          {lines.map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
      </div>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        onScroll={syncScroll}
        rows={rows}
        className="w-full px-3 py-2 text-sm font-mono focus:outline-none resize-none leading-6"
        placeholder={placeholder}
      />
    </div>
  );
}
