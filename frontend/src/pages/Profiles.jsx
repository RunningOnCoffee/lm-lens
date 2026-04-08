import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useProfileStore from '../stores/profileStore';

export default function Profiles() {
  const { profiles, loading, error, fetchProfiles, deleteProfile, cloneProfile } = useProfileStore();
  const navigate = useNavigate();
  const [selected, setSelected] = useState(new Set());
  const [actionError, setActionError] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => { fetchProfiles(); }, [fetchProfiles]);

  const builtinProfiles = profiles.filter((p) => p.is_builtin);
  const customProfiles = profiles.filter((p) => !p.is_builtin);

  // Selection helpers (custom only)
  const selectableIds = customProfiles.map((p) => p.id);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));
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
    setSelected(allSelected ? new Set() : new Set(selectableIds));
    setConfirming(false);
  };

  const handleClone = async (id) => {
    try {
      setActionError(null);
      const clone = await cloneProfile(id);
      navigate(`/profiles/${clone.id}/edit`);
    } catch (err) {
      setActionError(err.message);
    }
  };

  const handleBulkClone = async () => {
    setBusy(true);
    setActionError(null);
    try {
      for (const id of selected) {
        await cloneProfile(id);
      }
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
      for (const id of selected) {
        await deleteProfile(id);
      }
      setSelected(new Set());
      setConfirming(false);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRowDelete = async (id) => {
    try {
      setActionError(null);
      await deleteProfile(id);
      setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
    } catch (err) {
      setActionError(err.message);
    }
  };

  if (loading && profiles.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Loading profiles...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">Profiles</h1>
        <button
          onClick={() => navigate('/profiles/new')}
          className="px-4 py-2 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors"
        >
          + New Profile
        </button>
      </div>

      {(error || actionError) && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error || actionError}
        </div>
      )}

      {/* Built-in profiles table */}
      <h2 className="font-heading text-sm uppercase tracking-wider text-gray-500 mb-2">
        Built-in Profiles
      </h2>
      <ProfileTable
        profiles={builtinProfiles}
        selectable={false}
        emptyMessage="No built-in profiles."
        onClone={handleClone}
        onEdit={(id) => navigate(`/profiles/${id}/edit`)}
      />

      {/* Custom profiles table */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-heading text-sm uppercase tracking-wider text-gray-500">
            Custom Profiles
          </h2>
        </div>

        {/* Bulk action bar */}
        {someSelected && (
          <div className="mb-2 flex items-center gap-3 px-4 py-2.5 bg-surface-800 border border-surface-600 rounded-lg">
            <span className="text-xs text-gray-400">{selected.size} selected</span>
            <div className="h-4 w-px bg-surface-600" />
            <button
              onClick={handleBulkClone}
              disabled={busy}
              className="px-3 py-1 text-xs rounded bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors disabled:opacity-50"
            >
              Clone ({selected.size})
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={busy}
              className={`px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 ${
                confirming
                  ? 'bg-danger/20 text-danger hover:bg-danger/30'
                  : 'bg-surface-700 text-gray-300 hover:text-danger hover:bg-surface-600'
              }`}
            >
              {confirming ? `Confirm Delete (${selected.size})` : `Delete (${selected.size})`}
            </button>
            <button
              onClick={() => { setSelected(new Set()); setConfirming(false); }}
              className="ml-auto px-2 py-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        <ProfileTable
          profiles={customProfiles}
          selectable
          selected={selected}
          allSelected={allSelected}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          emptyMessage="No custom profiles yet. Clone a built-in profile or create a new one."
          onClone={handleClone}
          onEdit={(id) => navigate(`/profiles/${id}/edit`)}
          onDelete={handleRowDelete}
        />
      </div>
    </div>
  );
}

function ProfileTable({
  profiles,
  selectable = false,
  selected,
  allSelected,
  onToggleSelect,
  onToggleSelectAll,
  emptyMessage,
  onClone,
  onView,
  onEdit,
  onDelete,
}) {
  const cols = selectable
    ? 'grid-cols-[40px_1fr_100px_100px_160px]'
    : 'grid-cols-[1fr_100px_100px_100px]';

  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl overflow-hidden">
      {/* Header */}
      <div className={`grid ${cols} items-center px-4 py-2.5 border-b border-surface-600`}>
        {selectable && (
          <div className="flex items-center justify-center">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={onToggleSelectAll}
              className="accent-accent w-3.5 h-3.5 cursor-pointer"
              title="Select all"
            />
          </div>
        )}
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Name</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Templates</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-center">Follow-ups</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold text-right">Actions</span>
      </div>

      {/* Rows */}
      {profiles.map((p) => (
        <ProfileRow
          key={p.id}
          profile={p}
          cols={cols}
          selectable={selectable}
          isSelected={selected?.has(p.id)}
          onToggle={() => onToggleSelect?.(p.id)}
          onClone={() => onClone(p.id)}
          onView={onView ? () => onView(p.id) : undefined}
          onEdit={onEdit ? () => onEdit(p.id) : undefined}
          onDelete={onDelete ? () => onDelete(p.id) : undefined}
        />
      ))}

      {profiles.length === 0 && (
        <div className="px-4 py-8 text-center text-gray-600 text-sm">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}

function ProfileRow({ profile, cols, selectable, isSelected, onToggle, onClone, onView, onEdit, onDelete }) {
  const [rowConfirm, setRowConfirm] = useState(false);

  return (
    <div
      className={`grid ${cols} items-center px-4 py-3 border-b border-surface-600/50 last:border-b-0 transition-colors ${
        isSelected ? 'bg-accent/5' : 'hover:bg-surface-700/50'
      }`}
    >
      {/* Checkbox */}
      {selectable && (
        <div className="flex items-center justify-center">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggle}
            className="accent-accent w-3.5 h-3.5 cursor-pointer"
          />
        </div>
      )}

      {/* Name + description */}
      <div className="min-w-0 pr-4">
        <span className="text-sm text-gray-200 font-medium truncate block">{profile.name}</span>
        <p className="text-xs text-gray-600 truncate mt-0.5">{profile.description}</p>
      </div>

      {/* Counts */}
      <span className="text-xs text-gray-400 text-center tabular-nums">{profile.template_count}</span>
      <span className="text-xs text-gray-400 text-center tabular-nums">{profile.follow_up_count}</span>

      {/* Actions */}
      <div className="flex items-center justify-end gap-1.5">
        <button
          onClick={onClone}
          className="px-2.5 py-1 text-[11px] rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors"
        >
          Clone
        </button>
        {onView && (
          <button
            onClick={onView}
            className="px-2.5 py-1 text-[11px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
          >
            View
          </button>
        )}
        {onEdit && (
          <button
            onClick={onEdit}
            className="px-2.5 py-1 text-[11px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
          >
            Edit
          </button>
        )}
        {onDelete && (
          rowConfirm ? (
            <button
              onClick={() => { onDelete(); setRowConfirm(false); }}
              className="px-2.5 py-1 text-[11px] rounded bg-danger/20 text-danger hover:bg-danger/30 transition-colors"
            >
              Confirm
            </button>
          ) : (
            <button
              onClick={() => setRowConfirm(true)}
              className="px-2.5 py-1 text-[11px] rounded bg-surface-700 text-gray-500 hover:text-danger hover:bg-surface-600 transition-colors"
            >
              Delete
            </button>
          )
        )}
      </div>
    </div>
  );
}
