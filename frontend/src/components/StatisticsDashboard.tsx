import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { BarChart3, FileText, Code, AlignLeft, Layers } from 'lucide-react';

interface Stats {
  total_files: number;
  total_lines_of_code: number;
  total_functions: number;
  total_classes: number;
  language_distribution: Record<string, number>;
  avg_function_size: number;
  largest_files: Array<{
    path: string;
    size: number;
    lines: number;
  }>;
}

export const StatisticsDashboard: React.FC<{ repositoryId: string | null }> = ({ repositoryId }) => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    if (!repositoryId) return;
    setLoading(true);
    try {
      const res = await api.get(`/statistics/?repository_id=${repositoryId}`);
      setStats(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [repositoryId]);

  if (!repositoryId) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-gray-500 bg-editor-bg">
        Select a repository to view statistics.
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-gray-400 gap-1.5 bg-editor-bg">
        <div className="w-4 h-4 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
        Calculating repository statistics...
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-gray-500 bg-editor-bg italic">
        No statistics found. Ensure indexing has completed.
      </div>
    );
  }

  // Format bytes helper
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get total language count to calculate percentage
  const totalLangCount = Object.values(stats.language_distribution).reduce((a, b) => a + b, 0);

  return (
    <div className="flex-1 overflow-y-auto bg-editor-bg text-editor-fg p-6 flex flex-col gap-6 select-text">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-editor-border pb-3 shrink-0">
        <BarChart3 size={20} className="text-editor-accent" />
        <h1 className="text-sm font-bold uppercase tracking-wider text-white">Repository Statistics</h1>
      </div>

      {/* Grid Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Total Files</span>
          <div className="text-xl font-semibold text-white flex items-center gap-1.5">
            <FileText size={18} className="text-blue-400" />
            {stats.total_files}
          </div>
        </div>

        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Lines of Code</span>
          <div className="text-xl font-semibold text-white flex items-center gap-1.5">
            <AlignLeft size={18} className="text-green-400" />
            {stats.total_lines_of_code.toLocaleString()}
          </div>
        </div>

        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Functions / Methods</span>
          <div className="text-xl font-semibold text-white flex items-center gap-1.5">
            <Code size={18} className="text-yellow-600" />
            {stats.total_functions}
          </div>
        </div>

        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold">Classes Defined</span>
          <div className="text-xl font-semibold text-white flex items-center gap-1.5">
            <Layers size={18} className="text-purple-400" />
            {stats.total_classes}
          </div>
        </div>
      </div>

      {/* Language distribution & Largest files section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Language Breakdown */}
        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-3">
          <h3 className="text-xs uppercase font-bold text-gray-400 tracking-wider">Language Breakdown</h3>
          <div className="flex flex-col gap-2.5">
            {Object.entries(stats.language_distribution).map(([lang, count], idx) => {
              const pct = totalLangCount > 0 ? Math.round((count / totalLangCount) * 100) : 0;
              // Choose color based on language
              const colorClass = 
                lang === 'python' ? 'bg-blue-500' :
                lang === 'javascript' || lang === 'typescript' ? 'bg-yellow-500' :
                lang === 'go' ? 'bg-cyan-500' :
                lang === 'cpp' ? 'bg-orange-500' : 'bg-gray-500';

              return (
                <div key={idx} className="flex flex-col gap-1 text-xs">
                  <div className="flex items-center justify-between text-[11px] text-gray-300">
                    <span className="capitalize">{lang}</span>
                    <span className="font-mono text-gray-400">{count} files ({pct}%)</span>
                  </div>
                  <div className="w-full bg-editor-inactive h-2 rounded overflow-hidden">
                    <div className={`h-full ${colorClass}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Top 10 Largest Files */}
        <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-3">
          <h3 className="text-xs uppercase font-bold text-gray-400 tracking-wider">Top Largest Files</h3>
          <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
            {stats.largest_files.map((file, idx) => (
              <div key={idx} className="flex items-center justify-between p-1.5 bg-editor-bg border border-editor-border rounded text-[11px] text-gray-300">
                <div className="flex flex-col min-w-0 pr-2">
                  <span className="font-semibold truncate text-white" title={file.path}>
                    {file.path.split('/').pop()}
                  </span>
                  <span className="text-[9px] text-gray-500 truncate" title={file.path}>
                    {file.path}
                  </span>
                </div>
                <div className="shrink-0 text-right font-mono text-[10px] text-gray-400">
                  <div>{file.lines} lines</div>
                  <div>{formatBytes(file.size)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Code Characteristics */}
      <div className="bg-editor-sidebar border border-editor-border p-4 rounded flex flex-col gap-3">
        <h3 className="text-xs uppercase font-bold text-gray-400 tracking-wider">Code Characteristics</h3>
        <div className="flex items-center justify-between text-xs p-2 bg-editor-bg border border-editor-border rounded text-gray-300">
          <span>Average Function / Method Size:</span>
          <span className="font-mono font-semibold text-white">
            {stats.avg_function_size.toFixed(1)} lines of code
          </span>
        </div>
      </div>
    </div>
  );
};
