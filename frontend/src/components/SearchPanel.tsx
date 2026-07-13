import React, { useState } from 'react';
import api from '../services/api';
import { Search, BrainCircuit, Code, FileText, Layout } from 'lucide-react';

export const SearchPanel: React.FC<{
  repositoryId: string | null;
  onSelectFile: (path: string, highlightLine?: number) => void;
}> = ({ repositoryId, onSelectFile }) => {
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic'>('keyword');
  const [filterType, setFilterType] = useState<string>(''); // empty means 'all'
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repositoryId || !query.trim()) return;

    setLoading(true);
    setResults([]);
    try {
      if (searchMode === 'keyword') {
        const typeParam = filterType ? `&type=${filterType}` : '';
        const res = await api.get(`/search/text?repository_id=${repositoryId}&q=${encodeURIComponent(query)}${typeParam}`);
        setResults(res.data);
      } else {
        const res = await api.get(`/search/semantic?repository_id=${repositoryId}&q=${encodeURIComponent(query)}`);
        setResults(res.data);
      }
    } catch (err) {
      console.error(err);
      alert('Search failed. Please ensure the repository is fully indexed.');
    } finally {
      setLoading(false);
    }
  };

  const getResultIcon = (type: string) => {
    switch (type) {
      case 'file':
        return <FileText size={14} className="text-blue-400 shrink-0" />;
      case 'class':
        return <Layout size={14} className="text-yellow-600 shrink-0" />;
      case 'function':
        return <Code size={14} className="text-green-400 shrink-0" />;
      default:
        return <Code size={14} className="text-gray-400 shrink-0" />;
    }
  };

  // Helper to extract a potential line number or jump to code
  const handleItemClick = (item: any) => {
    // If it's a function or class, it might have body line info in backend.
    // For now, let's open the file.
    onSelectFile(item.path);
  };

  return (
    <div className="flex flex-col h-full bg-editor-sidebar text-editor-fg border-r border-editor-border">
      {/* Search Header */}
      <div className="p-3 border-b border-editor-border">
        <h2 className="text-xs uppercase font-bold text-gray-400 tracking-wider mb-2">Search Workspace</h2>
        
        {/* Toggle Mode */}
        <div className="flex border border-editor-border rounded overflow-hidden mb-2 bg-editor-inactive">
          <button
            type="button"
            className={`flex-1 py-1 text-[11px] flex items-center justify-center gap-1 ${
              searchMode === 'keyword' ? 'bg-editor-active text-white font-medium' : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setSearchMode('keyword')}
          >
            <Search size={12} />
            Keyword
          </button>
          <button
            type="button"
            className={`flex-1 py-1 text-[11px] flex items-center justify-center gap-1 ${
              searchMode === 'semantic' ? 'bg-editor-active text-white font-medium' : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setSearchMode('semantic')}
          >
            <BrainCircuit size={12} />
            Semantic AI
          </button>
        </div>

        {/* Input */}
        <form onSubmit={handleSearch} className="flex flex-col gap-2">
          <div className="relative">
            <input
              type="text"
              placeholder={searchMode === 'keyword' ? 'Search terms, regex...' : 'Explain in plain english what you want...'}
              className="w-full bg-editor-inactive border border-editor-border text-xs pl-2 pr-8 py-1.5 focus:outline-none focus:border-editor-accent text-white"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              type="submit"
              className="absolute right-2 top-1.5 text-gray-400 hover:text-white"
              disabled={loading || !repositoryId}
            >
              <Search size={14} />
            </button>
          </div>

          {/* Filters (only for keyword) */}
          {searchMode === 'keyword' && (
            <div className="flex gap-1.5">
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full bg-editor-inactive border border-editor-border text-[10px] px-1 py-0.5 text-gray-300 focus:outline-none"
              >
                <option value="">All Types</option>
                <option value="file">Files</option>
                <option value="class">Classes</option>
                <option value="function">Functions</option>
              </select>
            </div>
          )}
        </form>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-3 border-b border-editor-border flex items-center justify-between text-xs text-gray-400 font-semibold uppercase tracking-wider shrink-0">
          <span>Results</span>
          {results.length > 0 && <span className="text-[10px]">{results.length} found</span>}
        </div>

        {!repositoryId ? (
          <div className="text-xs text-gray-500 p-4 text-center">
            Select a repository to search.
          </div>
        ) : loading ? (
          <div className="text-xs text-gray-500 p-4 text-center flex items-center justify-center gap-1.5">
            <div className="w-3 h-3 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
            Searching code...
          </div>
        ) : results.length === 0 ? (
          <div className="text-xs text-gray-500 p-4 text-center italic">
            No matching code structures found.
          </div>
        ) : (
          <div className="divide-y divide-editor-border">
            {results.map((item, idx) => {
              const scorePercent = searchMode === 'semantic' ? Math.round(item.similarity * 100) : null;
              
              return (
                <div
                  key={idx}
                  className="p-2.5 hover:bg-editor-hover cursor-pointer flex flex-col gap-1 transition-colors"
                  onClick={() => handleItemClick(item)}
                >
                  {/* Title & Metadata */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0">
                      {getResultIcon(item.type)}
                      <span className="font-semibold text-xs text-white truncate" title={item.name}>
                        {item.name}
                      </span>
                    </div>
                    {scorePercent !== null && (
                      <span className="text-[10px] bg-editor-accent/20 text-editor-accent px-1.5 py-0.5 rounded font-mono shrink-0">
                        {scorePercent}%
                      </span>
                    )}
                  </div>
                  
                  {/* File Path */}
                  <span className="text-[10px] text-gray-500 truncate" title={item.path}>
                    {item.path}
                  </span>

                  {/* Code snippet */}
                  <pre className="text-[10px] font-mono bg-editor-bg border border-editor-border p-1.5 rounded overflow-x-auto text-gray-400 max-h-24">
                    <code>{item.snippet || item.body || ''}</code>
                  </pre>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
