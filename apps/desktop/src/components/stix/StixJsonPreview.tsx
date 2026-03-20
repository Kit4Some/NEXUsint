import { useState } from 'react';

interface StixJsonPreviewProps {
  data: unknown;
  maxHeight?: number;
}

function syntaxHighlight(json: string): string {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = 'text-nexus-amber'; // number
      if (/^"/.test(match)) {
        if (/:$/.test(match)) {
          cls = 'text-nexus-cyan'; // key
          match = match.slice(0, -1); // remove colon for re-adding
          return `<span class="${cls}">${match}</span>:`;
        } else {
          cls = 'text-nexus-green'; // string
        }
      } else if (/true|false/.test(match)) {
        cls = 'text-purple-400'; // boolean
      } else if (/null/.test(match)) {
        cls = 'text-nexus-text-secondary'; // null
      }
      return `<span class="${cls}">${match}</span>`;
    },
  );
}

export function StixJsonPreview({ data, maxHeight = 300 }: StixJsonPreviewProps) {
  const [copied, setCopied] = useState(false);
  const jsonStr = JSON.stringify(data, null, 2);
  const lines = jsonStr.split('\n');
  const highlighted = syntaxHighlight(jsonStr);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative">
      <div className="absolute top-2 right-2 z-10">
        <button
          onClick={handleCopy}
          className="text-[10px] font-mono px-2 py-1 bg-nexus-card border border-nexus-border rounded text-nexus-text-secondary hover:text-nexus-cyan transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <div
        className="bg-nexus-bg border border-nexus-border rounded-lg overflow-auto font-mono text-xs p-3"
        style={{ maxHeight }}
      >
        <div className="flex">
          {/* Line numbers */}
          <div className="pr-3 mr-3 border-r border-nexus-border/50 select-none text-nexus-text-secondary text-right">
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>
          {/* Highlighted JSON */}
          <pre
            className="flex-1 whitespace-pre text-nexus-text"
            dangerouslySetInnerHTML={{ __html: highlighted }}
          />
        </div>
      </div>
    </div>
  );
}
