import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { profilesApi } from '../api/client';
import ConversationPreview from '../components/ConversationPreview';

const DEFAULT_BEHAVIOR = {
  session_mode: 'multi_turn',
  turns_per_session: { min: 3, max: 8 },
  think_time_seconds: { min: 5, max: 45 },
  sessions_per_user: { min: 1, max: 3 },
  read_time_factor: 0.02,
};

const EMPTY_TEMPLATE = {
  category: 'general',
  starter_prompt: '',
  expected_response_tokens: { min: 50, max: 500 },
  follow_ups: [],
};

const TOOLTIPS = {
  session_mode: 'Whether each simulated session is a single prompt or a multi-turn conversation',
  read_time_factor: 'Seconds the simulated user spends per output token before responding (simulates reading time)',
  turns_per_session: 'Range of conversation turns per session — ignored in single-shot mode',
  think_time_seconds: 'Seconds the simulated user pauses between turns (simulates thinking)',
  sessions_per_user: 'How many separate sessions each simulated user will initiate',
};

export default function ProfileEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [behavior, setBehavior] = useState(DEFAULT_BEHAVIOR);
  const [templates, setTemplates] = useState([]);
  const [variables, setVariables] = useState([]);
  const [universalFollowUps, setUniversalFollowUps] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [profileId, setProfileId] = useState(id || null);
  const [isBuiltin, setIsBuiltin] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);

  useEffect(() => {
    if (!id) return;
    profilesApi.get(id).then((res) => {
      const p = res.data;
      setName(p.name);
      setDescription(p.description);
      setBehavior(p.behavior_defaults);
      setTemplates(
        p.conversation_templates.map((t) => ({
          category: t.category,
          starter_prompt: t.starter_prompt,
          expected_response_tokens: t.expected_response_tokens,
          follow_ups: t.follow_ups.map((f) => ({ content: f.content })),
        }))
      );
      setVariables(
        p.template_variables.map((v) => ({ name: v.name, values: v.values }))
      );
      setUniversalFollowUps(
        p.follow_up_prompts
          .filter((f) => f.is_universal)
          .map((f) => ({ content: f.content, is_universal: true }))
      );
      setProfileId(p.id);
      setIsBuiltin(p.is_builtin);
    }).catch((err) => setError(err.message));
  }, [id]);

  // --- Validation ---
  const rangeErrors = {};
  const checkRange = (key, val) => {
    if (val.max < val.min) rangeErrors[key] = true;
  };
  checkRange('turns_per_session', behavior.turns_per_session);
  checkRange('think_time_seconds', behavior.think_time_seconds);
  checkRange('sessions_per_user', behavior.sessions_per_user);
  const hasRangeErrors = Object.keys(rangeErrors).length > 0;

  // --- Save ---
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const body = {
        name,
        description,
        behavior_defaults: behavior,
        conversation_templates: templates,
        template_variables: variables,
        follow_up_prompts: universalFollowUps.map((f) => ({
          content: f.content,
          is_universal: true,
        })),
      };

      let res;
      if (isEdit) {
        res = await profilesApi.update(id, body);
      } else {
        res = await profilesApi.create(body);
      }
      const savedId = res.data.id;
      setProfileId(savedId);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      // For new profiles, switch to edit mode
      if (!isEdit) {
        navigate(`/profiles/${savedId}/edit`, { replace: true });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirmReset) {
      setConfirmReset(true);
      setTimeout(() => setConfirmReset(false), 5000);
      return;
    }
    setResetting(true);
    setConfirmReset(false);
    setError(null);
    try {
      const res = await profilesApi.reset(id);
      const p = res.data;
      setName(p.name);
      setDescription(p.description);
      setBehavior(p.behavior_defaults);
      setTemplates(
        p.conversation_templates.map((t) => ({
          category: t.category,
          starter_prompt: t.starter_prompt,
          expected_response_tokens: t.expected_response_tokens,
          follow_ups: t.follow_ups.map((f) => ({ content: f.content })),
        }))
      );
      setVariables(
        p.template_variables.map((v) => ({ name: v.name, values: v.values }))
      );
      setUniversalFollowUps(
        p.follow_up_prompts
          .filter((f) => f.is_universal)
          .map((f) => ({ content: f.content, is_universal: true }))
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setResetting(false);
    }
  };

  // --- Template management ---
  const addTemplate = () => setTemplates([...templates, { ...EMPTY_TEMPLATE, follow_ups: [] }]);
  const removeTemplate = (i) => setTemplates(templates.filter((_, idx) => idx !== i));
  const updateTemplate = (i, field, value) => {
    const updated = [...templates];
    updated[i] = { ...updated[i], [field]: value };
    setTemplates(updated);
  };

  // Follow-up management for a template
  const addFollowUp = (tmplIdx) => {
    const updated = [...templates];
    updated[tmplIdx] = {
      ...updated[tmplIdx],
      follow_ups: [...updated[tmplIdx].follow_ups, { content: '' }],
    };
    setTemplates(updated);
  };
  const removeFollowUp = (tmplIdx, fuIdx) => {
    const updated = [...templates];
    updated[tmplIdx] = {
      ...updated[tmplIdx],
      follow_ups: updated[tmplIdx].follow_ups.filter((_, i) => i !== fuIdx),
    };
    setTemplates(updated);
  };
  const updateFollowUp = (tmplIdx, fuIdx, content) => {
    const updated = [...templates];
    updated[tmplIdx] = {
      ...updated[tmplIdx],
      follow_ups: updated[tmplIdx].follow_ups.map((f, i) =>
        i === fuIdx ? { ...f, content } : f
      ),
    };
    setTemplates(updated);
  };

  // --- Variable management ---
  const addVariable = () => setVariables([...variables, { name: '', values: [''] }]);
  const removeVariable = (i) => setVariables(variables.filter((_, idx) => idx !== i));
  const updateVariableName = (i, rawName) => {
    const sanitized = rawName.toUpperCase().replace(/[^A-Z0-9_]/g, '');
    const updated = [...variables];
    updated[i] = { ...updated[i], name: sanitized };
    setVariables(updated);
  };
  const addVariableValue = (varIdx) => {
    const updated = [...variables];
    updated[varIdx] = { ...updated[varIdx], values: [...updated[varIdx].values, ''] };
    setVariables(updated);
  };
  const removeVariableValue = (varIdx, valIdx) => {
    const updated = [...variables];
    updated[varIdx] = {
      ...updated[varIdx],
      values: updated[varIdx].values.filter((_, i) => i !== valIdx),
    };
    setVariables(updated);
  };
  const updateVariableValue = (varIdx, valIdx, newValue) => {
    const updated = [...variables];
    updated[varIdx] = {
      ...updated[varIdx],
      values: updated[varIdx].values.map((v, i) => (i === valIdx ? newValue : v)),
    };
    setVariables(updated);
  };

  // --- Universal follow-up management ---
  const addUniversalFollowUp = () =>
    setUniversalFollowUps([...universalFollowUps, { content: '', is_universal: true }]);
  const removeUniversalFollowUp = (i) =>
    setUniversalFollowUps(universalFollowUps.filter((_, idx) => idx !== i));
  const updateUniversalFollowUp = (i, content) => {
    const updated = [...universalFollowUps];
    updated[i] = { ...updated[i], content };
    setUniversalFollowUps(updated);
  };

  // --- Behavior update helper ---
  const updateBehaviorRange = (field, key, value) => {
    setBehavior({
      ...behavior,
      [field]: { ...behavior[field], [key]: Number(value) },
    });
  };

  const isSingleShot = behavior.session_mode === 'single_shot';

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">
          {isEdit ? 'Edit Profile' : 'New Profile'}
        </h1>
        <div className="flex items-center gap-2">
          {isBuiltin && (
            <button
              onClick={handleReset}
              disabled={resetting}
              className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                confirmReset
                  ? 'bg-danger/20 text-danger hover:bg-danger/30'
                  : 'bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600'
              }`}
            >
              {resetting ? 'Resetting...' : confirmReset ? 'Confirm Reset' : 'Reset to Defaults'}
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={saving || !name.trim() || hasRangeErrors}
            className="px-4 py-1.5 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Profile'}
          </button>
          <button
            onClick={() => navigate('/profiles')}
            className="px-3 py-1.5 text-sm rounded-lg text-gray-400 hover:text-gray-200 hover:bg-surface-700 transition-colors"
          >
            &larr; Back
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">
          {error}
        </div>
      )}
      {saved && (
        <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm">
          Profile saved successfully.
        </div>
      )}

      {/* Basic Info */}
      <Section title="Basic Info">
        <div className="grid grid-cols-1 gap-4">
          <Field label="Name">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. API Tester"
              className="input"
            />
          </Field>
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Describe what this profile simulates..."
              className="input"
            />
          </Field>
        </div>
      </Section>

      {/* Behavior Config */}
      <Section title="Behavior Defaults">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Session Mode" tooltip={TOOLTIPS.session_mode}>
            <select
              value={behavior.session_mode}
              onChange={(e) => setBehavior({ ...behavior, session_mode: e.target.value })}
              className="input"
            >
              <option value="multi_turn">Multi-turn</option>
              <option value="single_shot">Single-shot</option>
            </select>
          </Field>
          <Field label="Read Time Factor (s/token)" tooltip={TOOLTIPS.read_time_factor}>
            <input
              type="number"
              step="0.001"
              value={behavior.read_time_factor}
              onChange={(e) => setBehavior({ ...behavior, read_time_factor: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <div className={isSingleShot ? 'opacity-40 pointer-events-none' : ''}>
            <RangeField
              label="Turns per Session"
              tooltip={TOOLTIPS.turns_per_session}
              value={behavior.turns_per_session}
              onChange={(key, val) => updateBehaviorRange('turns_per_session', key, val)}
              hasError={rangeErrors.turns_per_session}
            />
          </div>
          <RangeField
            label="Think Time (seconds)"
            tooltip={TOOLTIPS.think_time_seconds}
            value={behavior.think_time_seconds}
            onChange={(key, val) => updateBehaviorRange('think_time_seconds', key, val)}
            hasError={rangeErrors.think_time_seconds}
          />
          <RangeField
            label="Sessions per User"
            tooltip={TOOLTIPS.sessions_per_user}
            value={behavior.sessions_per_user}
            onChange={(key, val) => updateBehaviorRange('sessions_per_user', key, val)}
            hasError={rangeErrors.sessions_per_user}
          />
        </div>
      </Section>

      {/* Conversation Templates */}
      <Section
        title="Conversation Templates"
        action={
          <button onClick={addTemplate} className="text-xs text-accent hover:text-accent-bright">
            + Add Template
          </button>
        }
      >
        {templates.length === 0 && (
          <p className="text-gray-600 text-sm">No templates yet. Add one to define starter prompts.</p>
        )}
        {templates.map((tmpl, i) => (
          <div key={i} className="bg-surface-900 border border-surface-600 rounded-lg p-4 mb-3">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-gray-500 uppercase tracking-wider">
                Template {i + 1}
              </span>
              <button
                onClick={() => removeTemplate(i)}
                className="text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
              >
                Remove
              </button>
            </div>
            <Field label="Title" compact>
              <input
                type="text"
                value={tmpl.category}
                onChange={(e) => updateTemplate(i, 'category', e.target.value)}
                placeholder="e.g. code-review, question, debugging"
                className="input"
              />
            </Field>
            <Field label="Starter Prompt" compact>
              <textarea
                value={tmpl.starter_prompt}
                onChange={(e) => updateTemplate(i, 'starter_prompt', e.target.value)}
                rows={2}
                placeholder="Use $VARIABLE_NAME for substitution"
                className="input"
              />
            </Field>

            {/* Template-specific follow-ups */}
            <div className="mt-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500">Follow-ups</span>
                <button
                  onClick={() => addFollowUp(i)}
                  className="text-xs text-accent hover:text-accent-bright"
                >
                  + Add
                </button>
              </div>
              {tmpl.follow_ups.map((fu, fi) => (
                <div key={fi} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={fu.content}
                    onChange={(e) => updateFollowUp(i, fi, e.target.value)}
                    placeholder="Follow-up prompt..."
                    className="input flex-1"
                  />
                  <button
                    onClick={() => removeFollowUp(i, fi)}
                    className="text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Section>

      {/* Universal Follow-ups */}
      <Section
        title="Universal Follow-ups"
        subtitle="Used across all templates in this profile"
        action={
          <button onClick={addUniversalFollowUp} className="text-xs text-accent hover:text-accent-bright">
            + Add
          </button>
        }
      >
        {universalFollowUps.length === 0 && (
          <p className="text-gray-600 text-sm">No universal follow-ups.</p>
        )}
        {universalFollowUps.map((fu, i) => (
          <div key={i} className="flex gap-2 mb-2">
            <input
              type="text"
              value={fu.content}
              onChange={(e) => updateUniversalFollowUp(i, e.target.value)}
              placeholder="Universal follow-up..."
              className="input flex-1"
            />
            <button
              onClick={() => removeUniversalFollowUp(i)}
              className="text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
            >
              x
            </button>
          </div>
        ))}
      </Section>

      {/* Template Variables */}
      <Section
        title="Template Variables"
        subtitle="Define $VARIABLE pools. One value is randomly selected per variable for each conversation."
        action={
          <button onClick={addVariable} className="text-xs text-accent hover:text-accent-bright">
            + Add Variable
          </button>
        }
      >
        {variables.length === 0 && (
          <p className="text-gray-600 text-sm">No variables defined.</p>
        )}
        {variables.map((v, i) => (
          <div key={i} className="bg-surface-900 border border-surface-600 rounded-lg p-4 mb-3">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={v.name}
                  onChange={(e) => updateVariableName(i, e.target.value)}
                  placeholder="VARIABLE_NAME"
                  className="input w-48 font-mono text-accent"
                />
                <span className="text-[10px] text-gray-600">
                  {v.values.filter(Boolean).length} value{v.values.filter(Boolean).length !== 1 ? 's' : ''}
                </span>
                {v.name && (
                  <code className="text-[10px] text-gray-600 bg-surface-800 px-1.5 py-0.5 rounded">
                    ${v.name}
                  </code>
                )}
              </div>
              <button
                onClick={() => removeVariable(i)}
                className="text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
              >
                Remove
              </button>
            </div>
            <div className="space-y-2">
              {v.values.map((val, vi) => (
                <div key={vi} className="flex gap-2 items-start">
                  <AutoTextarea
                    value={val}
                    onChange={(newVal) => updateVariableValue(i, vi, newVal)}
                    placeholder={`Value ${vi + 1}`}
                    className="input flex-1 font-mono text-xs"
                  />
                  <button
                    onClick={() => removeVariableValue(i, vi)}
                    className="mt-2 text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
                  >
                    x
                  </button>
                </div>
              ))}
              <button
                onClick={() => addVariableValue(i)}
                className="text-xs text-accent hover:text-accent-bright"
              >
                + Add Value
              </button>
            </div>
          </div>
        ))}
      </Section>

      {/* Conversation Preview */}
      {profileId && (
        <Section title="Conversation Preview">
          <ConversationPreview profileId={profileId} />
        </Section>
      )}

      {/* Save */}
      <div className="flex gap-3 mt-6 mb-12">
        <button
          onClick={handleSave}
          disabled={saving || !name.trim() || hasRangeErrors}
          className="px-6 py-2.5 text-sm rounded-lg bg-accent text-surface-900 font-semibold hover:bg-accent-bright transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : isEdit ? 'Save Changes' : 'Create Profile'}
        </button>
        <button
          onClick={() => navigate('/profiles')}
          className="px-6 py-2.5 text-sm rounded-lg bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors"
        >
          &larr; Back
        </button>
      </div>
    </div>
  );
}

// --- Reusable UI components ---

function Section({ title, subtitle, action, children }) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="font-heading text-sm uppercase tracking-wider text-gray-400">{title}</h2>
          {subtitle && <p className="text-xs text-gray-600 mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="bg-surface-800 border border-surface-600 rounded-xl p-4">
        {children}
      </div>
    </div>
  );
}

function Field({ label, tooltip, compact, className, children }) {
  return (
    <label className={`block ${compact ? 'mb-2' : ''} ${className || ''}`}>
      <span className="text-xs text-gray-500 mb-1 inline-flex items-center gap-1.5">
        {label}
        {tooltip && <InfoTip text={tooltip} />}
      </span>
      {children}
    </label>
  );
}

function InfoTip({ text }) {
  return (
    <span className="relative group cursor-help">
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-surface-600 text-gray-500 text-[9px] font-bold leading-none">
        i
      </span>
      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 text-[11px] text-gray-300 bg-surface-700 border border-surface-600 rounded-lg shadow-lg whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
        {text}
      </span>
    </span>
  );
}

function RangeField({ label, tooltip, value, onChange, hasError }) {
  return (
    <Field label={label} tooltip={tooltip}>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-[10px] text-gray-600 block mb-0.5">Min</span>
          <input
            type="number"
            value={value.min}
            onChange={(e) => onChange('min', e.target.value)}
            className={`input ${hasError ? 'border-danger/50' : ''}`}
          />
        </div>
        <div>
          <span className="text-[10px] text-gray-600 block mb-0.5">Max</span>
          <input
            type="number"
            value={value.max}
            onChange={(e) => onChange('max', e.target.value)}
            className={`input ${hasError ? 'border-danger/50' : ''}`}
          />
        </div>
      </div>
      {hasError && <p className="text-danger text-[10px] mt-1">Max must be &ge; Min</p>}
    </Field>
  );
}

function AutoTextarea({ value, onChange, placeholder, className }) {
  const ref = useRef(null);

  const adjustHeight = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  };

  useEffect(() => { adjustHeight(); }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onInput={adjustHeight}
      placeholder={placeholder}
      rows={1}
      className={`${className} resize-none overflow-hidden`}
    />
  );
}
