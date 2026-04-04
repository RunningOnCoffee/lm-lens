import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useEndpointStore from '../stores/endpointStore';

export default function Endpoints() {
  const { endpoints, loading, error, fetchEndpoints, deleteEndpoint, cloneEndpoint } = useEndpointStore();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(new Set());
  const [actionError, setActionError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => { fetchEndpoints(); }, [fetchEndpoints]);

  const allIds = endpoints.map((e) => e.id);
  const allSelected = allIds.length > 0 && allIds.every((id) => selected.has(id));
  const someSelected = selected.size > 0;

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
    setConfirming(false);
  };

  const toggleSelectAll = () => {
    setSelected(allSelected ? new Set() : new Set(allIds));
    setConfirming(false);
  };

  const handleClone = async (id) => {
    try {
      setActionError(null);
      const clone = await cloneEndpoint(id);
      navigate(`/endpoints/${clone.id}/edit`);
    } catch (err) {
      setActionError(err.message);
    }
  };

  const handleDelete = async (id) => {
    try {
      setActionError(null);
      await deleteEndpoint(id);
      setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
    } catch (err) {
      setActionError(err.message);
    }
  };

  const handleBulkClone = async () => {
    setBusy(true);
    setActionError(null);
    try {
      for (const id of selected) { await cloneEndpoint(id); }
      setSelected(new Set());
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleBulkDelete = async () => {
    if (!confirming) { setConfirming(true); return; }
    setBusy(true);
    setActionError(null);
    try {
      for (const id of selected) { await deleteEndpoint(id); }
      setSelected(new Set());
      setConfirming(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (loading && endpoints.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading endpoints...</p>
      </div>
    );
  }

  const cols = 'grid-cols-[40px_1fr_140px_120px_120px_160px]';

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">AI Endpoints</h1>
        <button
          onClick={() => navigate('/endpoints/new')}
          className="px-4 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors"
        >
          + New Endpoint
        </button>
      </div>

      {(error || actionError) && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error || actionError}
        </div>
      )}

      {someSelected && (
        <div className="mb-2 flex items-center gap-3 px-4 py-2.5 bg-surface-800 border border-surface-600 rounded-lg">
          <span className="text-xs text-gray-400">{selected.size} selected</span>
          <div className="h-4 w-px bg-surface-600" />
          <button onClick={handleBulkClone} disabled={busy} className="px-3 py-1 text-xs rounded bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors disabled:opacity-50">
            Clone ({selected.size})
          </button>
          <button onClick={handleBulkDelete} disabled={busy} className={`px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 ${confirming ? 'bg-danger/20 text-danger hover:bg-danger/30' : 'bg-surface-700 text-gray-300 hover:text-danger hover:bg-surface-600'}`}>
            {confirming ? `Confirm Delete (${selected.size})` : `Delete (${selected.size})`}
          </button>
          <button onClick={() => { setSelected(new Set()); setConfirming(false); }} className="ml-auto px-2 py-1 text-xs text-gray-500 hover:text-gray-300 transition-colors">
            Clear
          </button>
        </div>
      )}

      <div className="bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
        <div className={`grid ${cols} items-center px-4 py-2.5 border-b border-surface-600`}>
          <div className="flex items-center justify-center">
            <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} className="accent-accent w-3.5 h-3.5 cursor-pointer" title="Select all" />
          </div>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Name</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Model</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">GPU</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Engine</span>
          <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-right">Actions</span>
        </div>

        {endpoints.map((ep) => (
          <EndpointRow
            key={ep.id}
            endpoint={ep}
            cols={cols}
            isSelected={selected.has(ep.id)}
            onToggle={() => toggleSelect(ep.id)}
            onClone={() => handleClone(ep.id)}
            onEdit={() => navigate(`/endpoints/${ep.id}/edit`)}
            onDelete={() => handleDelete(ep.id)}
          />
        ))}

        {endpoints.length === 0 && (
          <div className="px-4 py-8 text-center text-gray-600 text-sm">
            No endpoints yet. Add one to connect to an LLM server.
          </div>
        )}
      </div>
    </div>
  );
}

function EndpointRow({ endpoint, cols, isSelected, onToggle, onClone, onEdit, onDelete }) {
  const [rowConfirm, setRowConfirm] = useState(false);

  return (
    <div className={`grid ${cols} items-center px-4 py-3 border-b border-surface-600/50 last:border-b-0 transition-colors ${isSelected ? 'bg-accent/5' : 'hover:bg-surface-700/50'}`}>
      <div className="flex items-center justify-center">
        <input type="checkbox" checked={isSelected} onChange={onToggle} className="accent-accent w-3.5 h-3.5 cursor-pointer" />
      </div>
      <div className="min-w-0 pr-4">
        <span className="text-sm text-gray-200 font-medium truncate block">{endpoint.name}</span>
        <p className="text-xs text-gray-600 truncate mt-0.5 font-mono">{endpoint.endpoint_url}</p>
      </div>
      <span className="text-xs text-gray-400 text-center truncate" title={endpoint.model_name}>{endpoint.model_name}</span>
      <span className="text-xs text-gray-400 text-center truncate">{endpoint.gpu || '-'}</span>
      <span className="text-xs text-gray-400 text-center truncate">{endpoint.inference_engine || '-'}</span>
      <div className="flex items-center justify-end gap-1.5">
        <button onClick={onClone} className="px-2.5 py-1 text-[11px] rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors">Clone</button>
        <button onClick={onEdit} className="px-2.5 py-1 text-[11px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors">Edit</button>
        {rowConfirm ? (
          <button onClick={() => { onDelete(); setRowConfirm(false); }} className="px-2.5 py-1 text-[11px] rounded bg-danger/20 text-danger hover:bg-danger/30 transition-colors">Confirm</button>
        ) : (
          <button onClick={() => setRowConfirm(true)} className="px-2.5 py-1 text-[11px] rounded bg-surface-700 text-gray-500 hover:text-danger hover:bg-surface-600 transition-colors">Delete</button>
        )}
      </div>
    </div>
  );
}
