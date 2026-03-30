import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { profilesApi } from '../api/client';
import ConversationPreview from '../components/ConversationPreview';

export default function ProfileView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    profilesApi.get(id)
      .then((res) => setProfile(res.data))
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) {
    return (
      <div className="p-4 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
        {error}
      </div>
    );
  }

  if (!profile) {
    return <p className="text-gray-500">Loading...</p>;
  }

  const b = profile.behavior_defaults;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-2xl font-bold">{profile.name}</h1>
          {profile.is_builtin && (
            <span className="inline-block mt-1 px-2 py-0.5 text-[10px] uppercase tracking-wider font-semibold bg-accent/10 text-accent rounded">
              Built-in
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              profilesApi.clone(id).then((res) => {
                navigate(`/profiles/${res.data.id}/edit`);
              });
            }}
            className="px-4 py-2 text-sm rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
          >
            Clone & Edit
          </button>
          <button
            onClick={() => navigate('/profiles')}
            className="px-4 py-2 text-sm rounded-lg bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors"
          >
            Back
          </button>
        </div>
      </div>

      <p className="text-gray-400 text-sm mb-6">{profile.description}</p>

      {/* Behavior */}
      <Section title="Behavior Defaults">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Stat label="Session Mode" value={b.session_mode.replace('_', '-')} />
          <Stat label="Turns/Session" value={`${b.turns_per_session.min} - ${b.turns_per_session.max}`} />
          <Stat label="Think Time" value={`${b.think_time_seconds.min}s - ${b.think_time_seconds.max}s`} />
          <Stat label="Sessions/User" value={`${b.sessions_per_user.min} - ${b.sessions_per_user.max}`} />
          <Stat label="Read Time Factor" value={`${b.read_time_factor} s/token`} />
        </div>
      </Section>

      {/* Templates */}
      <Section title={`Conversation Templates (${profile.conversation_templates.length})`}>
        {profile.conversation_templates.map((t) => (
          <div key={t.id} className="bg-surface-900 border border-surface-600 rounded-lg p-4 mb-3 last:mb-0">
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2 py-0.5 text-[10px] uppercase tracking-wider bg-surface-700 text-gray-400 rounded">
                {t.category}
              </span>
              <span className="text-[10px] text-gray-600">
                {t.expected_response_tokens.min}-{t.expected_response_tokens.max} tokens
              </span>
            </div>
            <p className="text-sm text-gray-300 mb-2 font-mono">{t.starter_prompt}</p>
            {t.follow_ups.length > 0 && (
              <div className="mt-2 pl-3 border-l border-surface-600">
                <span className="text-[10px] text-gray-600 uppercase tracking-wider">Follow-ups</span>
                {t.follow_ups.map((f) => (
                  <p key={f.id} className="text-xs text-gray-500 mt-1">{f.content}</p>
                ))}
              </div>
            )}
          </div>
        ))}
      </Section>

      {/* Universal Follow-ups */}
      {profile.follow_up_prompts.filter((f) => f.is_universal).length > 0 && (
        <Section title="Universal Follow-ups">
          {profile.follow_up_prompts.filter((f) => f.is_universal).map((f) => (
            <p key={f.id} className="text-sm text-gray-400 mb-1">{f.content}</p>
          ))}
        </Section>
      )}

      {/* Variables */}
      {profile.template_variables.length > 0 && (
        <Section title="Template Variables">
          <div className="space-y-2">
            {profile.template_variables.map((v) => (
              <div key={v.id} className="flex gap-3 items-start">
                <code className="text-xs text-accent bg-surface-900 px-2 py-1 rounded min-w-[140px]">
                  {`$${v.name}`}
                </code>
                <p className="text-xs text-gray-500 flex-1">
                  {v.values.join(', ')}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Preview */}
      <Section title="Conversation Preview">
        <ConversationPreview profileId={id} />
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h2 className="font-heading text-sm uppercase tracking-wider text-gray-400 mb-3">{title}</h2>
      <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
        {children}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-0.5">{label}</p>
      <p className="text-sm text-gray-300">{value}</p>
    </div>
  );
}
