interface LinedContentProps {
  content: string;
  emptyLabel?: string;
  className?: string;
  maxH?: string;
}

export default function LinedContent({ content, emptyLabel, className = '', maxH = 'max-h-96' }: LinedContentProps) {
  if (!content) {
    return <span className="text-gray-400">{emptyLabel || '(empty)'}</span>;
  }
  const lines = content.split('\n');
  const digits = String(lines.length).length;

  return (
    <div className={`bg-gray-50 border border-gray-200 rounded-md overflow-auto ${maxH} ${className}`}>
      <table className="w-full border-collapse">
        <tbody className="font-mono text-xs text-gray-700">
          {lines.map((line, i) => (
            <tr key={i} className="hover:bg-gray-100">
              <td className="text-right text-gray-400 select-none pr-3 pl-3 py-0 align-top whitespace-nowrap border-r border-gray-200 bg-gray-100 w-1"
                style={{ minWidth: `${digits * 0.75 + 2}rem` }}>
                {i + 1}
              </td>
              <td className="pl-3 pr-3 py-0 align-top whitespace-pre-wrap break-all">
                {line}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
