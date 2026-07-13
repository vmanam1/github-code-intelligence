import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Folder, FileCode, ChevronDown, ChevronRight, Download, RefreshCw, Trash2, Database, AlertCircle } from 'lucide-react';

interface Repo {
  id: string;
  name: string;
  url: string;
  status: string;
  error_message?: string;
}



interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: TreeNode[];
}

// Tree view helper
function buildFileTree(paths: string[]): TreeNode[] {
  const root: TreeNode[] = [];
  paths.forEach(p => {
    const parts = p.split('/');
    let currentLevel = root;
    let accumulatedPath = '';
    
    parts.forEach((part, index) => {
      accumulatedPath = accumulatedPath ? `${accumulatedPath}/${part}` : part;
      const isLast = index === parts.length - 1;
      
      let existing = currentLevel.find(node => node.name === part && node.type === (isLast ? 'file' : 'folder'));
      if (!existing) {
        existing = {
          name: part,
          path: accumulatedPath,
          type: isLast ? 'file' : 'folder'
        };
        if (!isLast) {
          existing.children = [];
        }
        currentLevel.push(existing);
      }
      if (!isLast) {
        currentLevel = existing.children!;
      }
    });
  });
  
  const sortTree = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) {
        return a.type === 'folder' ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
    nodes.forEach(node => {
      if (node.children) sortTree(node.children);
    });
  };
  
  sortTree(root);
  return root;
}

const FileTreeNode: React.FC<{
  node: TreeNode;
  onSelectFile: (path: string) => void;
  selectedFilePath: string | null;
  depth: number;
}> = ({ node, onSelectFile, selectedFilePath, depth }) => {
  const [isOpen, setIsOpen] = useState(false);
  const isSelected = selectedFilePath === node.path;

  if (node.type === 'file') {
    return (
      <div
        className={`flex items-center py-1 pr-2 hover:bg-editor-hover cursor-pointer text-xs ${
          isSelected ? 'bg-editor-active text-editor-accent border-l-2 border-editor-accent pl-[calc(depth*12px+10px)]' : ''
        }`}
        style={{ paddingLeft: `${depth * 12 + 12}px` }}
        onClick={() => onSelectFile(node.path)}
      >
        <FileCode size={14} className="mr-2 text-gray-400 shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
    );
  }

  return (
    <div>
      <div
        className="flex items-center py-1 pr-2 hover:bg-editor-hover cursor-pointer text-xs text-gray-300"
        style={{ paddingLeft: `${depth * 12 + 12}px` }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? (
          <ChevronDown size={14} className="mr-1 text-gray-500 shrink-0" />
        ) : (
          <ChevronRight size={14} className="mr-1 text-gray-500 shrink-0" />
        )}
        <Folder size={14} className="mr-2 text-yellow-600 shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
      {isOpen && node.children && (
        <div>
          {node.children.map((child, idx) => (
            <FileTreeNode
              key={idx}
              node={child}
              onSelectFile={onSelectFile}
              selectedFilePath={selectedFilePath}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const RepositoryExplorer: React.FC<{
  selectedRepoId: string | null;
  onSelectRepo: (id: string | null) => void;
  onSelectFile: (path: string) => void;
  selectedFilePath: string | null;
}> = ({ selectedRepoId, onSelectRepo, onSelectFile, selectedFilePath }) => {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [importUrl, setImportUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [repoFiles, setRepoFiles] = useState<string[]>([]);
  const [activeRepo, setActiveRepo] = useState<Repo | null>(null);

  // Poll repos list
  const fetchRepos = async () => {
    try {
      const res = await api.get('/repositories/');
      setRepos(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRepoFiles = async (repoId: string) => {
    try {
      // Find repo metadata to display files
      const res = await api.get(`/repositories/${repoId}`);
      setActiveRepo(res.data);
      
      // Let's get files from repo stats or standard list
      // Since we save File records in DB, let's fetch file records!
      const filesRes = await api.get(`/search/text?repository_id=${repoId}&q=&type=file&limit=500`);
      setRepoFiles(filesRes.data.map((f: any) => f.path));
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchRepos();
    const interval = setInterval(fetchRepos, 5000); // poll every 5s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedRepoId) {
      fetchRepoFiles(selectedRepoId);
    } else {
      setRepoFiles([]);
      setActiveRepo(null);
    }
  }, [selectedRepoId]);

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl.trim()) return;

    setImporting(true);
    try {
      const res = await api.post('/repositories/', { url: importUrl });
      setImportUrl('');
      fetchRepos();
      onSelectRepo(res.data.id);
    } catch (err) {
      alert('Failed to trigger repository clone.');
      console.error(err);
    } finally {
      setImporting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this repository and all indexed content?')) return;
    try {
      await api.delete(`/repositories/${id}`);
      if (selectedRepoId === id) {
        onSelectRepo(null);
      }
      fetchRepos();
    } catch (err) {
      alert('Failed to delete repository.');
    }
  };

  const handleReindex = async (id: string) => {
    try {
      await api.post(`/repositories/${id}/index`);
      fetchRepos();
    } catch (err) {
      alert('Failed to trigger re-indexing.');
    }
  };

  const fileTree = buildFileTree(repoFiles);

  return (
    <div className="flex flex-col h-full bg-editor-sidebar text-editor-fg border-r border-editor-border select-none">
      {/* Import Form */}
      <div className="p-3 border-b border-editor-border">
        <h2 className="text-xs uppercase font-bold text-gray-400 tracking-wider mb-2">Import Repository</h2>
        <form onSubmit={handleImport} className="flex flex-col gap-2">
          <input
            type="text"
            placeholder="GitHub Repo URL..."
            className="bg-editor-inactive border border-editor-border text-xs px-2 py-1.5 focus:outline-none focus:border-editor-accent text-white"
            value={importUrl}
            onChange={(e) => setImportUrl(e.target.value)}
            disabled={importing}
          />
          <button
            type="submit"
            className="bg-editor-accent hover:bg-editor-accentHover text-white text-xs py-1 px-3 rounded flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
            disabled={importing || !importUrl.trim()}
          >
            <Download size={14} />
            {importing ? 'Importing...' : 'Clone & Index'}
          </button>
        </form>
      </div>

      {/* Repository Selector */}
      <div className="p-3 border-b border-editor-border">
        <h2 className="text-xs uppercase font-bold text-gray-400 tracking-wider mb-2">Workspace</h2>
        <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
          {repos.length === 0 ? (
            <div className="text-xs text-gray-500 flex items-center gap-1.5 py-1">
              <Database size={14} />
              No repositories imported.
            </div>
          ) : (
            repos.map((repo) => (
              <div
                key={repo.id}
                className={`flex items-center justify-between p-1.5 rounded cursor-pointer group text-xs ${
                  selectedRepoId === repo.id ? 'bg-editor-active text-white' : 'hover:bg-editor-hover text-gray-300'
                }`}
                onClick={() => onSelectRepo(repo.id)}
              >
                <div className="flex flex-col min-w-0 pr-1">
                  <span className="font-semibold truncate">{repo.name}</span>
                  <span className={`text-[10px] ${
                    repo.status === 'COMPLETED' ? 'text-green-500' :
                    repo.status === 'FAILED' ? 'text-red-500' : 'text-blue-400 animate-pulse'
                  }`}>
                    {repo.status}
                  </span>
                </div>
                <div className="hidden group-hover:flex items-center gap-1 shrink-0">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleReindex(repo.id); }}
                    title="Reindex Repository"
                    className="p-1 hover:text-white text-gray-400"
                  >
                    <RefreshCw size={12} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(repo.id); }}
                    title="Delete Repository"
                    className="p-1 hover:text-red-500 text-gray-400"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* File Tree Explorer */}
      <div className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-3 border-b border-editor-border shrink-0 flex items-center justify-between">
          <h2 className="text-xs uppercase font-bold text-gray-400 tracking-wider">Explorer</h2>
          {activeRepo && activeRepo.status !== 'COMPLETED' && (
            <span className="text-[10px] text-blue-400 animate-pulse">indexing...</span>
          )}
        </div>
        
        {activeRepo && activeRepo.status === 'FAILED' && (
          <div className="p-3 text-xs text-red-400 flex items-start gap-2 bg-red-950/20 border-b border-editor-border">
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            <div className="min-w-0">
              <div className="font-semibold">Indexing Failed</div>
              <div className="text-[10px] truncate max-w-full" title={activeRepo.error_message}>
                {activeRepo.error_message || 'Unknown error occurred'}
              </div>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto py-2">
          {selectedRepoId ? (
            fileTree.length === 0 ? (
              <div className="text-xs text-gray-500 px-3 italic">
                {activeRepo?.status === 'COMPLETED' ? 'No indexable files found.' : 'Parsing repository structure...'}
              </div>
            ) : (
              fileTree.map((node, idx) => (
                <FileTreeNode
                  key={idx}
                  node={node}
                  onSelectFile={onSelectFile}
                  selectedFilePath={selectedFilePath}
                  depth={0}
                />
              ))
            )
          ) : (
            <div className="text-xs text-gray-500 p-4 text-center">
              Select or import a repository to explore source code.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
