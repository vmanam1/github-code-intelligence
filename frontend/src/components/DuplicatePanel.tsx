import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Copy, ArrowRightLeft } from 'lucide-react';

interface FunctionObj {
  id: string;
  name: string;
  signature: string;
  start_line: number;
  end_line: number;
  body: string;
  file_path: string;
  class_name?: string;
}

interface DuplicatePair {
  function_a: FunctionObj;
  function_b: FunctionObj;
  similarity: number;
}

export const DuplicatePanel: React.FC<{
  repositoryId: string | null;
  onSelectFile: (path: string) => void;
}> = ({ repositoryId, onSelectFile }) => {
  const [pairs, setPairs] = useState<DuplicatePair[]>([]);
  const [loading, setLoading] = useState(false);
  const [activePair, setActivePair] = useState<DuplicatePair | null>(null);

  const fetchDuplicates = async () => {
    if (!repositoryId) return;
    setLoading(true);
    try {
      const res = await api.get(`/functions/duplicates/detect?repository_id=${repositoryId}`);
      setPairs(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDuplicates();
    setActivePair(null);
  }, [repositoryId]);

  if (!repositoryId) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-gray-500 bg-editor-bg">
        Select a repository to scan duplicates.
      </div>
    );
  }

  return (
    <div className="flex-1 flex bg-editor-bg text-editor-fg h-full select-text overflow-hidden">
      {/* Sidebar List */}
      <div className="w-80 bg-editor-sidebar border-r border-editor-border flex flex-col h-full shrink-0">
        <div className="p-3 border-b border-editor-border flex items-center gap-2 shrink-0">
          <Copy size={16} className="text-editor-accent" />
          <h2 className="text-xs uppercase font-bold text-gray-300 tracking-wider">Duplicate Code Detector</h2>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-xs text-gray-400 gap-1.5 p-4 text-center">
            <div className="w-3 h-3 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
            Comparing embeddings...
          </div>
        ) : pairs.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-xs text-gray-500 p-4 text-center italic">
            No duplicated functions found. Excellent codebase structure!
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto divide-y divide-editor-border">
            {pairs.map((pair, idx) => {
              const simPercent = Math.round(pair.similarity * 100);
              const isSelected = activePair === pair;

              return (
                <div
                  key={idx}
                  onClick={() => setActivePair(pair)}
                  className={`p-3 cursor-pointer flex flex-col gap-1 hover:bg-editor-hover transition-colors ${
                    isSelected ? 'bg-editor-active' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-white truncate max-w-[180px]">
                      {pair.function_a.name}
                    </span>
                    <span className="text-[10px] bg-editor-accent/20 text-editor-accent px-1.5 py-0.5 rounded font-mono font-bold">
                      {simPercent}% Match
                    </span>
                  </div>
                  
                  <div className="text-[10px] text-gray-500 flex flex-col gap-0.5 truncate">
                    <div className="truncate">File A: {pair.function_a.file_path.split('/').pop()}</div>
                    <div className="truncate">File B: {pair.function_b.file_path.split('/').pop()}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail Comparison Panel */}
      <div className="flex-1 flex flex-col h-full bg-editor-bg overflow-hidden">
        {activePair ? (
          <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Toolbar title */}
            <div className="p-3 bg-editor-sidebar border-b border-editor-border flex items-center justify-between shrink-0">
              <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                <ArrowRightLeft size={14} className="text-editor-accent" />
                Side-by-Side Comparison (Cosine Similarity: {(activePair.similarity).toFixed(4)})
              </span>
            </div>

            {/* Split comparison panels */}
            <div className="flex-1 grid grid-cols-2 divide-x divide-editor-border overflow-hidden">
              {/* Function A */}
              <div className="flex flex-col h-full overflow-hidden">
                <div className="p-2.5 bg-editor-inactive border-b border-editor-border flex justify-between items-center text-[10px] text-gray-400 shrink-0">
                  <span className="truncate font-semibold text-white" title={activePair.function_a.file_path}>
                    {activePair.function_a.file_path}
                  </span>
                  <button
                    onClick={() => onSelectFile(activePair.function_a.file_path)}
                    className="hover:text-white px-2 py-0.5 border border-editor-border rounded bg-editor-bg"
                  >
                    Open
                  </button>
                </div>
                <div className="flex-1 overflow-auto p-4 bg-editor-bg text-xs">
                  <div className="font-mono text-gray-500 text-[10px] mb-2">
                    Lines: {activePair.function_a.start_line} - {activePair.function_a.end_line}
                  </div>
                  <pre className="font-mono text-gray-300 leading-relaxed overflow-x-auto text-[11px] whitespace-pre bg-editor-sidebar border border-editor-border p-3 rounded">
                    <code>{activePair.function_a.body}</code>
                  </pre>
                </div>
              </div>

              {/* Function B */}
              <div className="flex flex-col h-full overflow-hidden">
                <div className="p-2.5 bg-editor-inactive border-b border-editor-border flex justify-between items-center text-[10px] text-gray-400 shrink-0">
                  <span className="truncate font-semibold text-white" title={activePair.function_b.file_path}>
                    {activePair.function_b.file_path}
                  </span>
                  <button
                    onClick={() => onSelectFile(activePair.function_b.file_path)}
                    className="hover:text-white px-2 py-0.5 border border-editor-border rounded bg-editor-bg"
                  >
                    Open
                  </button>
                </div>
                <div className="flex-1 overflow-auto p-4 bg-editor-bg text-xs">
                  <div className="font-mono text-gray-500 text-[10px] mb-2">
                    Lines: {activePair.function_b.start_line} - {activePair.function_b.end_line}
                  </div>
                  <pre className="font-mono text-gray-300 leading-relaxed overflow-x-auto text-[11px] whitespace-pre bg-editor-sidebar border border-editor-border p-3 rounded">
                    <code>{activePair.function_b.body}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-xs text-gray-500 italic p-8 text-center bg-editor-bg">
            <Copy size={32} className="text-gray-600 mb-2" />
            <p>Select a duplicate pair from the left panel to compare code fragments.</p>
          </div>
        )}
      </div>
    </div>
  );
};
