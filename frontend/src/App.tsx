import React, { useState } from 'react';
import { RepositoryExplorer } from './components/RepositoryExplorer';
import { SearchPanel } from './components/SearchPanel';
import { GraphViewer } from './components/GraphViewer';
import { AIPanel } from './components/AIPanel';
import { StatisticsDashboard } from './components/StatisticsDashboard';
import { DuplicatePanel } from './components/DuplicatePanel';
import Editor from '@monaco-editor/react';
import api from './services/api';
import { 
  FolderTree, Search, Network, BarChart3, Copy, Brain, 
  X, Terminal, HelpCircle 
} from 'lucide-react';

interface FileFunction {
  id: string;
  name: string;
  signature: string;
  start_line: number;
  end_line: number;
}

export default function App() {
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  
  // Navigation & panels
  const [activeSidebar, setActiveSidebar] = useState<'explorer' | 'search' | 'graph' | 'stats' | 'duplicates'>('explorer');
  const [showAIPanel, setShowAIPanel] = useState(true);

  // Editor states
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [editorLoading, setEditorLoading] = useState(false);

  // Selected code element for AI explanation
  const [selectedFuncId, setSelectedFuncId] = useState<string | null>(null);
  const [selectedFuncName, setSelectedFuncName] = useState<string | null>(null);
  const [fileFunctions, setFileFunctions] = useState<FileFunction[]>([]);

  // Detect language based on file extension
  const getEditorLanguage = (path: string | null): string => {
    if (!path) return 'text';
    const ext = path.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'py': return 'python';
      case 'js':
      case 'jsx': return 'javascript';
      case 'ts':
      case 'tsx': return 'typescript';
      case 'go': return 'go';
      case 'cpp':
      case 'cc':
      case 'h':
      case 'hpp': return 'cpp';
      case 'java': return 'java';
      case 'json': return 'json';
      case 'md': return 'markdown';
      case 'yml':
      case 'yaml': return 'yaml';
      default: return 'text';
    }
  };

  // Open a file
  const handleSelectFile = async (path: string) => {
    if (!selectedRepoId) return;
    
    // Add to tabs if not already open
    if (!openTabs.includes(path)) {
      setOpenTabs([...openTabs, path]);
    }
    setActiveTab(path);
    
    // Fetch file content
    setEditorLoading(true);
    try {
      const res = await api.get(`/repositories/${selectedRepoId}/file?path=${encodeURIComponent(path)}`);
      setFileContent(res.data.content);
      
      // Fetch functions defined in this file for dropdown/list selection
      // This allows the user to click any method to trigger Ollama analysis
      const funcsRes = await api.get(`/search/text?repository_id=${selectedRepoId}&q=${encodeURIComponent(path)}&type=function&limit=100`);
      setFileFunctions(funcsRes.data.map((f: any) => ({
        id: f.id,
        name: f.name,
        signature: f.snippet.split('\n')[0] || f.name,
        // Since search results don't have start/end line, we fetch them on click if needed
      })));
      
      // Clear selected function
      setSelectedFuncId(null);
      setSelectedFuncName(null);
    } catch (err) {
      console.error(err);
      setFileContent('// Failed to load file contents.');
      setFileFunctions([]);
    } finally {
      setEditorLoading(false);
    }
  };

  const handleCloseTab = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = openTabs.filter(t => t !== path);
    setOpenTabs(updated);
    
    if (activeTab === path) {
      if (updated.length > 0) {
        handleSelectFile(updated[updated.length - 1]);
      } else {
        setActiveTab(null);
        setFileContent('');
        setFileFunctions([]);
      }
    }
  };

  // Trigger file loading on active tab change
  const handleSelectTab = (path: string) => {
    handleSelectFile(path);
  };

  // Automatically reset states when repo selection changes
  const handleSelectRepo = (repoId: string | null) => {
    setSelectedRepoId(repoId);
    setOpenTabs([]);
    setActiveTab(null);
    setFileContent('');
    setFileFunctions([]);
    setSelectedFuncId(null);
    setSelectedFuncName(null);
  };

  // Renders the main editor pane depending on active tab or visual dashboards
  const renderCenterPane = () => {
    if (activeSidebar === 'graph') {
      return <GraphViewer repositoryId={selectedRepoId} onSelectFile={handleSelectFile} />;
    }
    if (activeSidebar === 'stats') {
      return <StatisticsDashboard repositoryId={selectedRepoId} />;
    }
    if (activeSidebar === 'duplicates') {
      return <DuplicatePanel repositoryId={selectedRepoId} onSelectFile={handleSelectFile} />;
    }

    if (!activeTab) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center text-xs text-gray-500 bg-editor-bg select-none gap-2">
          <Brain size={48} className="text-gray-700 animate-pulse" />
          <h2 className="text-sm font-semibold text-gray-400">GitHub Code Intelligence Platform</h2>
          <p className="max-w-md text-center text-[11px] text-gray-500 mt-1">
            Import a public GitHub repository, analyze classes & functions, search full-text or semantically with AI, and review code graphs.
          </p>
        </div>
      );
    }

    return (
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Editor Tabs Bar */}
        <div className="flex bg-editor-inactive border-b border-editor-border select-none shrink-0 overflow-x-auto">
          {openTabs.map((path) => (
            <div
              key={path}
              className={`flex items-center gap-1.5 px-3 py-2 cursor-pointer text-xs border-r border-editor-border shrink-0 transition-colors ${
                activeTab === path ? 'bg-editor-bg text-white border-t-2 border-t-editor-accent' : 'text-gray-400 hover:bg-editor-hover hover:text-white'
              }`}
              onClick={() => handleSelectTab(path)}
            >
              <span>{path.split('/').pop()}</span>
              <button 
                onClick={(e) => handleCloseTab(path, e)}
                className="p-0.5 rounded hover:bg-editor-active text-gray-500 hover:text-white"
              >
                <X size={10} />
              </button>
            </div>
          ))}
        </div>

        {/* Monaco Editor Container */}
        <div className="flex-1 relative overflow-hidden bg-editor-bg">
          {editorLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-editor-bg/85 z-10 text-xs text-gray-400 gap-1.5">
              <div className="w-3.5 h-3.5 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
              Loading file...
            </div>
          )}
          <Editor
            height="100%"
            theme="vs-dark"
            language={getEditorLanguage(activeTab)}
            value={fileContent}
            options={{
              readOnly: true,
              fontSize: 12,
              minimap: { enabled: true },
              automaticLayout: true,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              wordWrap: 'on'
            }}
          />
        </div>

        {/* Functions defined in current file */}
        {fileFunctions.length > 0 && (
          <div className="h-32 bg-editor-sidebar border-t border-editor-border flex flex-col shrink-0">
            <div className="p-2 border-b border-editor-border bg-editor-inactive text-[10px] uppercase font-bold text-gray-400 tracking-wider flex items-center gap-1.5 shrink-0">
              <Terminal size={12} className="text-editor-accent" />
              Functions in this File ({fileFunctions.length})
            </div>
            <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 md:grid-cols-3 gap-1.5 bg-editor-bg">
              {fileFunctions.map((fn) => (
                <div
                  key={fn.id}
                  onClick={() => {
                    setSelectedFuncId(fn.id);
                    setSelectedFuncName(fn.name);
                    setShowAIPanel(true);
                  }}
                  className={`p-1.5 border rounded cursor-pointer text-[11px] truncate transition-colors ${
                    selectedFuncId === fn.id
                      ? 'bg-editor-accent/20 border-editor-accent text-white'
                      : 'bg-editor-sidebar border-editor-border text-gray-300 hover:border-gray-500'
                  }`}
                  title={`Analyze function: ${fn.signature}`}
                >
                  <span className="font-semibold text-editor-accent pr-1">def</span>
                  <span className="font-mono text-gray-100">{fn.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex w-full h-full bg-editor-bg text-editor-fg font-sans select-none overflow-hidden">
      
      {/* 1. VS Code Left Activity Bar */}
      <div className="w-12 bg-editor-activity border-r border-editor-border flex flex-col items-center justify-between py-4 shrink-0 select-none">
        <div className="flex flex-col gap-5 items-center w-full">
          <button
            onClick={() => setActiveSidebar('explorer')}
            title="Repository Explorer"
            className={`p-2 rounded transition-colors ${
              activeSidebar === 'explorer' ? 'text-editor-accent bg-editor-active' : 'text-gray-400 hover:text-white'
            }`}
          >
            <FolderTree size={20} />
          </button>
          
          <button
            onClick={() => setActiveSidebar('search')}
            title="Search Codebase"
            className={`p-2 rounded transition-colors ${
              activeSidebar === 'search' ? 'text-editor-accent bg-editor-active' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Search size={20} />
          </button>

          <button
            onClick={() => setActiveSidebar('graph')}
            title="Relations Graphs"
            className={`p-2 rounded transition-colors ${
              activeSidebar === 'graph' ? 'text-editor-accent bg-editor-active' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Network size={20} />
          </button>

          <button
            onClick={() => setActiveSidebar('stats')}
            title="Repository Metrics"
            className={`p-2 rounded transition-colors ${
              activeSidebar === 'stats' ? 'text-editor-accent bg-editor-active' : 'text-gray-400 hover:text-white'
            }`}
          >
            <BarChart3 size={20} />
          </button>

          <button
            onClick={() => setActiveSidebar('duplicates')}
            title="Duplicate Detections"
            className={`p-2 rounded transition-colors ${
              activeSidebar === 'duplicates' ? 'text-editor-accent bg-editor-active' : 'text-gray-400 hover:text-white'
            }`}
          >
            <Copy size={20} />
          </button>
        </div>

        <div className="flex flex-col gap-3 items-center">
          <button
            onClick={() => setShowAIPanel(!showAIPanel)}
            title="Toggle AI Panel"
            className={`p-2 rounded transition-colors ${
              showAIPanel ? 'text-editor-accent' : 'text-gray-500 hover:text-white'
            }`}
          >
            <Brain size={20} />
          </button>
          <a
            href="https://github.com/vmanam1/github-code-intelligence"
            target="_blank"
            rel="noreferrer"
            title="Help & Info"
            className="text-gray-500 hover:text-white p-2 rounded"
          >
            <HelpCircle size={20} />
          </a>
        </div>
      </div>

      {/* 2. Left Sidebar (Explorer/Search) */}
      <div className={`w-80 shrink-0 h-full overflow-hidden ${
        (activeSidebar === 'graph' || activeSidebar === 'stats' || activeSidebar === 'duplicates') ? 'hidden' : 'block'
      }`}>
        {activeSidebar === 'explorer' && (
          <RepositoryExplorer
            selectedRepoId={selectedRepoId}
            onSelectRepo={handleSelectRepo}
            onSelectFile={handleSelectFile}
            selectedFilePath={activeTab}
          />
        )}
        {activeSidebar === 'search' && (
          <SearchPanel
            repositoryId={selectedRepoId}
            onSelectFile={handleSelectFile}
          />
        )}
      </div>

      {/* 3. Central Working Area (Editor / Visualizer Boards) */}
      <div className="flex-1 h-full flex flex-col overflow-hidden">
        {renderCenterPane()}
      </div>

      {/* 4. Collapsible Right AI Assistant Panel */}
      {showAIPanel && (
        <div className="w-80 shrink-0 h-full overflow-hidden">
          <AIPanel
            selectedFunctionId={selectedFuncId}
            selectedFunctionName={selectedFuncName}
          />
        </div>
      )}

    </div>
  );
}
