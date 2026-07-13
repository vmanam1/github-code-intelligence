import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Brain, ShieldAlert, Bug, RefreshCw, Zap, Clock, Info } from 'lucide-react';

interface AIPanelProps {
  selectedFunctionId: string | null;
  selectedFunctionName: string | null;
}

interface AIExplanation {
  purpose: string;
  summary: string;
  complexity: {
    time: string;
    space: string;
  };
  improvements: string[];
  potential_bugs: string[];
  security_concerns: string[];
  refactoring_suggestions: string[];
  raw_response: string;
}

export const AIPanel: React.FC<AIPanelProps> = ({ selectedFunctionId, selectedFunctionName }) => {
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState<AIExplanation | null>(null);

  useEffect(() => {
    // Reset explanation if function changes
    setExplanation(null);
  }, [selectedFunctionId]);

  const handleExplain = async () => {
    if (!selectedFunctionId) return;
    setLoading(true);
    try {
      const res = await api.post(`/functions/${selectedFunctionId}/explain`);
      setExplanation(res.data);
    } catch (err) {
      console.error(err);
      alert('AI Explanation request failed. Check that Ollama is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-editor-sidebar text-editor-fg border-l border-editor-border select-text">
      {/* Title */}
      <div className="p-3 bg-editor-sidebar border-b border-editor-border flex items-center gap-2 shrink-0">
        <Brain size={16} className="text-editor-accent" />
        <h2 className="text-xs uppercase font-bold text-gray-300 tracking-wider">Local AI Assistant</h2>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {!selectedFunctionId ? (
          <div className="text-xs text-gray-500 text-center flex flex-col items-center justify-center h-48 gap-2">
            <Info size={24} className="text-gray-600" />
            <p>Select a function in the code editor or search results to trigger AI analysis.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Call to action */}
            <div className="bg-editor-bg border border-editor-border p-3 rounded flex flex-col gap-2.5">
              <div className="text-xs">
                Selected: <span className="font-mono text-editor-accent font-semibold">{selectedFunctionName}</span>
              </div>
              <button
                onClick={handleExplain}
                disabled={loading}
                className="w-full bg-editor-accent hover:bg-editor-accentHover text-white text-xs py-1.5 px-3 rounded flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <Brain size={14} />
                {loading ? 'Analyzing Code...' : 'Analyze Function'}
              </button>
            </div>

            {loading && (
              <div className="text-xs text-gray-400 flex items-center justify-center gap-2 py-8">
                <div className="w-4 h-4 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
                Invoking Ollama local LLM...
              </div>
            )}

            {/* Explanation Results */}
            {explanation && !loading && (
              <div className="flex flex-col gap-4">
                {/* Purpose */}
                <div className="flex flex-col gap-1">
                  <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                    <Info size={12} className="text-blue-400" /> Purpose
                  </div>
                  <p className="text-xs text-gray-200 bg-editor-bg p-2 rounded border border-editor-border leading-relaxed">
                    {explanation.purpose}
                  </p>
                </div>

                {/* Summary */}
                <div className="flex flex-col gap-1">
                  <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Summary</div>
                  <p className="text-xs text-gray-300 leading-relaxed bg-editor-bg p-2 rounded border border-editor-border">
                    {explanation.summary}
                  </p>
                </div>

                {/* Complexity */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-editor-bg border border-editor-border p-2 rounded">
                    <div className="text-[9px] font-bold text-gray-400 uppercase flex items-center gap-1">
                      <Clock size={10} className="text-yellow-500" /> Time
                    </div>
                    <div className="text-[11px] font-mono text-white mt-0.5">{explanation.complexity.time}</div>
                  </div>
                  <div className="bg-editor-bg border border-editor-border p-2 rounded">
                    <div className="text-[9px] font-bold text-gray-400 uppercase flex items-center gap-1">
                      <Zap size={10} className="text-orange-400" /> Space
                    </div>
                    <div className="text-[11px] font-mono text-white mt-0.5">{explanation.complexity.space}</div>
                  </div>
                </div>

                {/* Potential Bugs */}
                {explanation.potential_bugs.length > 0 && (
                  <div className="flex flex-col gap-1">
                    <div className="text-[11px] font-bold text-red-400 uppercase tracking-wider flex items-center gap-1">
                      <Bug size={12} /> Potential Bugs
                    </div>
                    <ul className="text-xs text-gray-300 list-disc list-inside bg-red-950/10 border border-red-900/30 p-2.5 rounded flex flex-col gap-1">
                      {explanation.potential_bugs.map((bug, idx) => (
                        <li key={idx} className="leading-relaxed">{bug}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Security Concerns */}
                {explanation.security_concerns.length > 0 && (
                  <div className="flex flex-col gap-1">
                    <div className="text-[11px] font-bold text-orange-400 uppercase tracking-wider flex items-center gap-1">
                      <ShieldAlert size={12} /> Security Concerns
                    </div>
                    <ul className="text-xs text-gray-300 list-disc list-inside bg-orange-950/10 border border-orange-900/30 p-2.5 rounded flex flex-col gap-1">
                      {explanation.security_concerns.map((sec, idx) => (
                        <li key={idx} className="leading-relaxed">{sec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Improvements & Refactoring */}
                {explanation.improvements.length > 0 && (
                  <div className="flex flex-col gap-1">
                    <div className="text-[11px] font-bold text-green-400 uppercase tracking-wider flex items-center gap-1">
                      <RefreshCw size={11} /> Improvements & Refactoring
                    </div>
                    <ul className="text-xs text-gray-300 list-disc list-inside bg-green-950/10 border border-green-900/30 p-2.5 rounded flex flex-col gap-1">
                      {explanation.improvements.concat(explanation.refactoring_suggestions).map((imp, idx) => (
                        <li key={idx} className="leading-relaxed">{imp}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
