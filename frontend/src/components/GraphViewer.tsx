import React, { useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import api from '../services/api';
import { Network, Activity } from 'lucide-react';

interface GraphViewerProps {
  repositoryId: string | null;
  onSelectFile: (path: string) => void;
}

export const GraphViewer: React.FC<GraphViewerProps> = ({ repositoryId, onSelectFile }) => {
  const [graphType, setGraphType] = useState<'dependency' | 'call'>('dependency');
  const [loading, setLoading] = useState(false);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const fetchGraph = async () => {
    if (!repositoryId) return;
    setLoading(true);
    try {
      const endpoint = graphType === 'dependency' ? '/graphs/dependency' : '/graphs/call';
      const res = await api.get(`${endpoint}?repository_id=${repositoryId}`);
      
      const { nodes: apiNodes, edges: apiEdges } = res.data;

      // Position nodes in a grid to avoid overlaps without needing external layout engines
      const cols = 5;
      const xSpacing = 220;
      const ySpacing = 110;
      
      const flowNodes = apiNodes.map((node: any, idx: number) => {
        const colIdx = idx % cols;
        const rowIdx = Math.floor(idx / cols);
        return {
          id: node.id,
          type: 'default',
          data: { 
            label: (
              <div className="flex flex-col text-[10px] min-w-[120px] max-w-[180px] truncate">
                <span className="font-bold text-white truncate">{node.label}</span>
                {node.path && <span className="text-gray-400 text-[8px] truncate mt-0.5">{node.path}</span>}
              </div>
            ),
            path: node.path 
          },
          position: { x: colIdx * xSpacing + 50, y: rowIdx * ySpacing + 50 },
        };
      });

      const flowEdges = apiEdges.map((edge: any) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        animated: graphType === 'call',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 15,
          height: 15,
          color: '#555',
        },
        style: { stroke: '#555' }
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (err) {
      console.error(err);
      alert('Failed to load graphs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [repositoryId, graphType]);

  const handleNodeDoubleClick = (_: any, node: any) => {
    if (node.data && node.data.path) {
      onSelectFile(node.data.path);
    }
  };

  return (
    <div className="flex flex-col h-full bg-editor-bg select-none">
      {/* Toolbar */}
      <div className="p-3 bg-editor-sidebar border-b border-editor-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Network size={16} className="text-editor-accent" />
          <h2 className="text-xs uppercase font-bold text-gray-300 tracking-wider">
            Graph Visualizer
          </h2>
        </div>

        {/* Toggle Graph Mode */}
        <div className="flex border border-editor-border rounded overflow-hidden bg-editor-inactive">
          <button
            type="button"
            className={`px-3 py-1 text-[10px] flex items-center gap-1 ${
              graphType === 'dependency' ? 'bg-editor-active text-white font-medium' : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setGraphType('dependency')}
          >
            <Network size={12} />
            Dependency Graph
          </button>
          <button
            type="button"
            className={`px-3 py-1 text-[10px] flex items-center gap-1 ${
              graphType === 'call' ? 'bg-editor-active text-white font-medium' : 'text-gray-400 hover:text-white'
            }`}
            onClick={() => setGraphType('call')}
          >
            <Activity size={12} />
            Call Graph
          </button>
        </div>
      </div>

      {/* React Flow Board */}
      <div className="flex-1 relative bg-editor-bg">
        {!repositoryId ? (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-500">
            Select a repository to explore graphs.
          </div>
        ) : loading ? (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-400 gap-1.5 bg-editor-bg/85 z-10">
            <div className="w-4 h-4 border-2 border-editor-accent border-t-transparent rounded-full animate-spin"></div>
            Analyzing graph relations...
          </div>
        ) : nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-gray-500 italic">
            No relationship structures mapped. Run index first.
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDoubleClick={handleNodeDoubleClick}
            fitView
            attributionPosition="bottom-right"
          >
            <Background color="#333" gap={16} />
            <Controls />
            <MiniMap
              nodeColor={() => '#252526'}
              maskColor="rgba(30,30,30,0.6)"
              style={{ backgroundColor: '#1e1e1e', border: '1px solid #3c3c3c' }}
            />
          </ReactFlow>
        )}
      </div>
      
      {/* Footer Instructions */}
      <div className="p-2 bg-editor-sidebar border-t border-editor-border text-[9px] text-gray-500 text-center shrink-0">
        Tip: Double-click nodes to open the corresponding file/method in the Editor. Drag nodes to customize layouts.
      </div>
    </div>
  );
};
