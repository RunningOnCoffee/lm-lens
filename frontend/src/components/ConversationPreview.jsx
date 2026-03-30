import { useState } from 'react';
import { profilesApi } from '../api/client';

export default function ConversationPreview({ profileId }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await profilesApi.preview(profileId);
      setPreview(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={generate}
          disabled={loading}
          className="px-3 py-1.5 text-xs rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors disabled:opacity-50"
        >
          {loading ? 'Generating...' : preview ? 'Regenerate' : 'Generate Preview'}
        </button>
        {preview && (
          <span className="text-[10px] text-gray-600">
            {preview.template_category && `Category: ${preview.template_category}`}
            {preview.session_mode && ` | Mode: ${preview.session_mode.replace('_', '-')}`}
          </span>
        )}
      </div>

      {error && (
        <p className="text-danger text-xs mb-2">{error}</p>
      )}

      {preview && preview.turns.length === 0 && (
        <p className="text-gray-600 text-sm">No templates to preview. Add conversation templates first.</p>
      )}

      {preview && preview.turns.length > 0 && (
        <div className="space-y-2">
          {preview.turns.map((turn) => (
            <div
              key={turn.turn}
              className="flex gap-3 items-start"
            >
              <span className="text-[10px] text-gray-600 uppercase tracking-wider min-w-[50px] pt-1 text-right">
                Turn {turn.turn}
              </span>
              <div className="flex-1 bg-surface-900 border border-surface-600 rounded-lg px-3 py-2">
                <p className="text-sm text-gray-300 font-mono">{turn.content}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
