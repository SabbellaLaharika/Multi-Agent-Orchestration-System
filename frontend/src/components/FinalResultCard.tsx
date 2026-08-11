import React, { useState } from 'react';
import { Sparkles, Check, Copy } from 'lucide-react';

interface FinalResultCardProps {
  result: string;
}

export const FinalResultCard: React.FC<FinalResultCardProps> = ({ result }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="final-result-card">
      <div className="result-card-header">
        <div className="header-title">
          <Sparkles size={20} className="text-green" />
          <h2>Synthesized Final Result</h2>
        </div>
        <button type="button" className="copy-btn" onClick={handleCopy}>
          {copied ? <Check size={16} /> : <Copy size={16} />}
          <span>{copied ? 'Copied' : 'Copy Output'}</span>
        </button>
      </div>

      <div className="result-card-body">
        <pre className="markdown-content">{result}</pre>
      </div>
    </div>
  );
};
