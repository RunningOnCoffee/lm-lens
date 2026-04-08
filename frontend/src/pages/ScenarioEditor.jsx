import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { scenariosApi, profilesApi } from '../api/client';
import InfoTip from '../components/InfoTip';

const DEFAULT_LLM_PARAMS = {
  max_tokens: null,
  temperature: 0.7,
  top_p: 1.0,
  stop: [],
  frequency_penalty: 0.0,
  presence_penalty: 0.0,
};

const DEFAULT_LOAD_CONFIG = {
  test_mode: 'stress',
  duration_seconds: 60,
  ramp_users_per_step: 1,
  ramp_interval_seconds: 10,
  breaking_criteria: null,
};

const DEFAULT_BREAKING_CRITERIA = {
  max_ttft_ms: 5000,
  max_itl_ms: 500,
  max_error_rate_pct: 10.0,
};

const TEST_MODES = [
  {
    value: 'stress',
    label: 'Stress Test',
    description: 'All virtual users active simultaneously for the full duration. Best for measuring steady-state throughput and latency.',
  },
  {
    value: 'ramp',
    label: 'Ramp Up',
    description: 'Gradually add users over time to observe how performance degrades under increasing load.',
  },
  {
    value: 'breaking_point',
    label: 'Breaking Point',
    description: 'Ramp up users until performance criteria are breached, then report the breaking point.',
  },
];

const LLM_PARAM_TOOLTIPS = {
  max_tokens: 'Maximum tokens to generate per response. Leave empty for no limit — the model generates until it naturally completes or hits a stop sequence.',
  temperature: 'Controls output randomness. 0 = deterministic, 1 = balanced. OpenAI-compatible APIs support 0–2, but values above 1 produce increasingly chaotic output. Most use cases work best in 0–1.',
  top_p: 'Nucleus sampling — only considers tokens within this cumulative probability. 1.0 = consider all tokens. Generally adjust either temperature or top_p, not both.',
  frequency_penalty: 'Penalizes tokens based on how often they appear so far. Positive values reduce repetition. Range: -2 to 2 (OpenAI-compatible).',
  presence_penalty: 'Penalizes tokens that have appeared at all. Positive values encourage new topics. Range: -2 to 2 (OpenAI-compatible).',
  stop: 'Sequences where the model stops generating. The stop sequence itself is not included in the output. Up to 4 sequences.',
};

const BREAKING_TOOLTIPS = {
  max_ttft_ms: 'Maximum acceptable time to first token in milliseconds. The test stops if the rolling average exceeds this.',
  max_itl_ms: 'Maximum acceptable inter-token latency in milliseconds. Measures the perceived "typing speed" — if tokens arrive too slowly, the experience becomes unbearable.',
  max_error_rate_pct: 'Maximum acceptable error rate as a percentage. Includes timeouts, HTTP errors, and malformed responses.',
};

export default function ScenarioEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [llmParams, setLlmParams] = useState(DEFAULT_LLM_PARAMS);
  const [maxTokensInput, setMaxTokensInput] = useState('');
  const [loadConfig, setLoadConfig] = useState(DEFAULT_LOAD_CONFIG);
  const [breakingCriteria, setBreakingCriteria] = useState(DEFAULT_BREAKING_CRITERIA);
  const [maxConcurrency, setMaxConcurrency] = useState(100);
  const [scenarioProfiles, setScenarioProfiles] = useState([]);

  // UI state
  const [saveState, setSaveState] = useState('idle'); // idle | saving | saved
  const [error, setError] = useState(null);
  const [availableProfiles, setAvailableProfiles] = useState([]);

  // Load available profiles
  useEffect(() => {
    profilesApi.list().then((res) => {
      setAvailableProfiles(res.data);
    });
  }, []);

  // Load existing scenario
  useEffect(() => {
    if (!id) return;
    scenariosApi.get(id).then((res) => {
      const s = res.data;
      setName(s.name);
      setDescription(s.description);
      setLlmParams(s.llm_params);
      setMaxTokensInput(s.llm_params.max_tokens != null ? String(s.llm_params.max_tokens) : '');
      setLoadConfig(s.load_config);
      if (s.load_config.breaking_criteria) {
        setBreakingCriteria(s.load_config.breaking_criteria);
      }
      setMaxConcurrency(s.max_concurrency);
      setScenarioProfiles(
        s.profiles.map((p) => ({
          profile_id: p.profile_id,
          profile_name: p.profile_name,
          user_count: p.user_count,
          behavior_overrides: p.behavior_overrides,
        }))
      );
    }).catch((err) => setError(err.message));
  }, [id]);

  // --- Computed values ---
  const totalUsers = scenarioProfiles.reduce((sum, p) => sum + p.user_count, 0);

  // --- Profile management ---
  const addProfile = (profileId) => {
    const profile = availableProfiles.find((p) => p.id === profileId);
    if (!profile || scenarioProfiles.some((sp) => sp.profile_id === profileId)) return;
    setScenarioProfiles([...scenarioProfiles, {
      profile_id: profileId,
      profile_name: profile.name,
      user_count: 1,
      behavior_overrides: null,
    }]);
  };

  const removeProfile = (idx) => {
    setScenarioProfiles(scenarioProfiles.filter((_, i) => i !== idx));
  };

  const updateUserCount = (idx, count) => {
    const updated = [...scenarioProfiles];
    updated[idx] = { ...updated[idx], user_count: Math.max(1, count) };
    setScenarioProfiles(updated);
  };

  // --- Stop sequences management ---
  const addStopSequence = () => {
    setLlmParams({ ...llmParams, stop: [...llmParams.stop, ''] });
  };
  const removeStopSequence = (idx) => {
    setLlmParams({ ...llmParams, stop: llmParams.stop.filter((_, i) => i !== idx) });
  };
  const updateStopSequence = (idx, value) => {
    setLlmParams({
      ...llmParams,
      stop: llmParams.stop.map((s, i) => (i === idx ? value : s)),
    });
  };

  // --- Max tokens handling ---
  const handleMaxTokensChange = (val) => {
    setMaxTokensInput(val);
    const num = parseInt(val, 10);
    setLlmParams({ ...llmParams, max_tokens: val === '' ? null : (isNaN(num) ? null : num) });
  };

  // --- Save ---
  const handleSave = async () => {
    setSaveState('saving');
    setError(null);
    try {
      const finalLoadConfig = { ...loadConfig };
      if (loadConfig.test_mode === 'breaking_point') {
        finalLoadConfig.breaking_criteria = breakingCriteria;
      } else {
        finalLoadConfig.breaking_criteria = null;
      }

      const body = {
        name,
        description,
        llm_params: {
          ...llmParams,
          stop: llmParams.stop.filter(Boolean),
        },
        load_config: finalLoadConfig,
        max_concurrency: maxConcurrency,
        profiles: scenarioProfiles.map((p) => ({
          profile_id: p.profile_id,
          user_count: p.user_count,
          behavior_overrides: p.behavior_overrides,
        })),
      };

      let res;
      if (isEdit) {
        res = await scenariosApi.update(id, body);
      } else {
        res = await scenariosApi.create(body);
      }
      const savedId = res.data.id;
      setSaveState('saved');
      setTimeout(() => setSaveState('idle'), 2500);
      if (!isEdit) {
        navigate(`/scenarios/${savedId}/edit`, { replace: true });
      }
    } catch (err) {
      setError(err.message);
      setSaveState('idle');
    }
  };

  // --- Duration display helper ---
  const formatDuration = (seconds) => {
    if (!seconds || seconds <= 0) return '0s';
    if (seconds >= 3600) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    if (seconds >= 60) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  const canSave = !!name.trim();

  // Profiles not yet added
  const unaddedProfiles = availableProfiles.filter(
    (p) => !scenarioProfiles.some((sp) => sp.profile_id === p.id)
  );

  // Save button classes
  const saveButtonClass = saveState === 'saved'
    ? 'bg-green-500 text-white'
    : 'bg-accent text-surface-900 hover:bg-accent-bright';

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-heading text-2xl font-bold">
          {isEdit ? 'Edit Scenario' : 'New Scenario'}
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saveState === 'saving' || !canSave}
            className={`px-4 py-1.5 text-sm rounded-lg font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed ${saveButtonClass}`}
          >
            {saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved!' : isEdit ? 'Save Changes' : 'Create Scenario'}
          </button>
          <button
            onClick={() => navigate('/scenarios')}
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

      {/* Basic Info */}
      <Section title="Basic Info">
        <div className="grid grid-cols-1 gap-4">
          <Field label="Name">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. GPT-4o Load Test"
              className="input"
            />
          </Field>
          <Field label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Describe what this scenario tests..."
              className="input"
            />
          </Field>
        </div>
      </Section>

      {/* LLM Parameters */}
      <Section title="LLM Parameters" subtitle="These parameters are sent with every request to the LLM endpoint">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Max Tokens" tooltip={LLM_PARAM_TOOLTIPS.max_tokens}>
            <input
              type="number"
              min={1}
              value={maxTokensInput}
              onChange={(e) => handleMaxTokensChange(e.target.value)}
              placeholder="No limit"
              className="input placeholder:text-gray-600/60 placeholder:italic"
            />
          </Field>
          <SliderField
            label="Temperature"
            tooltip={LLM_PARAM_TOOLTIPS.temperature}
            value={llmParams.temperature}
            min={0} max={2} step={0.01}
            onChange={(v) => setLlmParams({ ...llmParams, temperature: v })}
          />
          <SliderField
            label="Top P"
            tooltip={LLM_PARAM_TOOLTIPS.top_p}
            value={llmParams.top_p}
            min={0} max={1} step={0.01}
            onChange={(v) => setLlmParams({ ...llmParams, top_p: v })}
          />
          <SliderField
            label="Frequency Penalty"
            tooltip={LLM_PARAM_TOOLTIPS.frequency_penalty}
            value={llmParams.frequency_penalty}
            min={-2} max={2} step={0.01}
            onChange={(v) => setLlmParams({ ...llmParams, frequency_penalty: v })}
          />
          <SliderField
            label="Presence Penalty"
            tooltip={LLM_PARAM_TOOLTIPS.presence_penalty}
            value={llmParams.presence_penalty}
            min={-2} max={2} step={0.01}
            onChange={(v) => setLlmParams({ ...llmParams, presence_penalty: v })}
          />
        </div>
        <div className="mt-4">
          <Field label="Stop Sequences" tooltip={LLM_PARAM_TOOLTIPS.stop}>
            {llmParams.stop.length === 0 && (
              <p className="text-gray-600 text-xs mb-2">No stop sequences defined.</p>
            )}
            {llmParams.stop.map((s, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={s}
                  onChange={(e) => updateStopSequence(i, e.target.value)}
                  placeholder="Stop sequence..."
                  className="input flex-1 font-mono"
                />
                <button
                  onClick={() => removeStopSequence(i)}
                  className="text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
                >
                  x
                </button>
              </div>
            ))}
            {llmParams.stop.length < 4 && (
              <button onClick={addStopSequence} className="text-xs text-accent hover:text-accent-bright">
                + Add Stop Sequence
              </button>
            )}
          </Field>
        </div>
      </Section>

      {/* Profile Mix */}
      <Section
        title="Profile Mix"
        subtitle="Define the virtual user composition. Each number represents how many users of that type to simulate."
        action={
          unaddedProfiles.length > 0 && (
            <select
              onChange={(e) => { addProfile(e.target.value); e.target.value = ''; }}
              value=""
              className="input text-xs w-48"
            >
              <option value="" disabled>+ Add Profile</option>
              {unaddedProfiles.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )
        }
      >
        {scenarioProfiles.length === 0 && (
          <p className="text-gray-600 text-sm">Add profiles to define your virtual user mix.</p>
        )}

        {scenarioProfiles.map((sp, idx) => {
          const pct = totalUsers > 0 ? Math.round((sp.user_count / totalUsers) * 100) : 0;
          return (
            <div key={sp.profile_id} className="bg-surface-900 border border-surface-600 rounded-lg p-4 mb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1">
                  <span className="text-sm text-gray-200 font-medium w-48 truncate">{sp.profile_name}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateUserCount(idx, sp.user_count - 1)}
                      disabled={sp.user_count <= 1}
                      className="w-7 h-7 flex items-center justify-center rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      min={1}
                      value={sp.user_count}
                      onChange={(e) => updateUserCount(idx, parseInt(e.target.value, 10) || 1)}
                      className="input w-16 text-center tabular-nums"
                    />
                    <button
                      onClick={() => updateUserCount(idx, sp.user_count + 1)}
                      className="w-7 h-7 flex items-center justify-center rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors text-sm font-bold"
                    >
                      +
                    </button>
                    <span className="text-xs text-gray-500 tabular-nums w-12 text-right">
                      {pct}%
                    </span>
                  </div>
                  {/* Weight bar */}
                  <div className="flex-1 h-2 bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
                <button
                  onClick={() => removeProfile(idx)}
                  className="ml-4 text-xs text-danger/70 border border-danger/30 rounded px-2 py-0.5 hover:bg-danger/10 hover:text-danger hover:border-danger/50 transition-colors"
                >
                  Remove
                </button>
              </div>
            </div>
          );
        })}

        {scenarioProfiles.length > 0 && (
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-surface-600">
            <span className="text-sm text-gray-400 tabular-nums">
              Total: <span className="text-gray-200 font-medium">{totalUsers}</span> virtual user{totalUsers !== 1 ? 's' : ''}
            </span>
          </div>
        )}
      </Section>

      {/* Test Configuration */}
      <Section title="Test Configuration" subtitle="Choose how the virtual users are deployed during the benchmark">
        {/* Test Mode Selection */}
        <div className="mb-5">
          <span className="text-xs text-gray-500 mb-2 block">Test Mode</span>
          <div className="grid grid-cols-3 gap-3">
            {TEST_MODES.map((mode) => (
              <button
                key={mode.value}
                onClick={() => setLoadConfig({ ...loadConfig, test_mode: mode.value })}
                className={`text-left p-3 rounded-lg border transition-colors ${
                  loadConfig.test_mode === mode.value
                    ? 'border-accent bg-accent/5 text-gray-200'
                    : 'border-surface-600 text-gray-400 hover:border-gray-500 hover:bg-surface-700/50'
                }`}
              >
                <span className={`text-sm font-medium block mb-1 ${
                  loadConfig.test_mode === mode.value ? 'text-accent' : ''
                }`}>
                  {mode.label}
                </span>
                <span className="text-[11px] text-gray-500 block leading-snug">{mode.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field
            label={loadConfig.test_mode === 'breaking_point' ? 'Max Duration (seconds)' : 'Duration (seconds)'}
            tooltip={loadConfig.test_mode === 'breaking_point'
              ? 'Safety timeout — the test stops after this even if the breaking point hasn\'t been found.'
              : 'How long the test runs in total.'}
          >
            <input
              type="number"
              min={1}
              value={loadConfig.duration_seconds}
              onChange={(e) => setLoadConfig({ ...loadConfig, duration_seconds: Number(e.target.value) })}
              className="input"
            />
            <span className="text-[10px] text-gray-600 mt-0.5 block">
              {formatDuration(loadConfig.duration_seconds)}
            </span>
          </Field>
          <Field label="Max Concurrency" tooltip="Safety cap on simultaneous active requests. Prevents accidental overload of the endpoint.">
            <input
              type="number"
              min={1}
              max={10000}
              value={maxConcurrency}
              onChange={(e) => setMaxConcurrency(Number(e.target.value))}
              className="input"
            />
          </Field>
        </div>

        {/* Ramp config — shown for ramp and breaking_point modes */}
        {(loadConfig.test_mode === 'ramp' || loadConfig.test_mode === 'breaking_point') && (
          <div className="mt-4 pt-4 border-t border-surface-600">
            <span className="text-xs text-gray-500 mb-3 block">Ramp Configuration</span>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Users Per Step" tooltip="How many users to add at each ramp step. Users are distributed across profiles proportionally.">
                <input
                  type="number"
                  min={1}
                  value={loadConfig.ramp_users_per_step}
                  onChange={(e) => setLoadConfig({ ...loadConfig, ramp_users_per_step: Number(e.target.value) })}
                  className="input"
                />
              </Field>
              <Field label="Step Interval (seconds)" tooltip="Time between each ramp step. Lower values = faster ramp.">
                <input
                  type="number"
                  min={1}
                  value={loadConfig.ramp_interval_seconds}
                  onChange={(e) => setLoadConfig({ ...loadConfig, ramp_interval_seconds: Number(e.target.value) })}
                  className="input"
                />
              </Field>
            </div>
            {totalUsers > 0 && (
              <p className="text-[11px] text-gray-600 mt-2">
                Ramp: 0 &rarr; {totalUsers} users over ~{formatDuration(Math.ceil(totalUsers / loadConfig.ramp_users_per_step) * loadConfig.ramp_interval_seconds)}
              </p>
            )}
          </div>
        )}

        {/* Breaking criteria — only for breaking_point mode */}
        {loadConfig.test_mode === 'breaking_point' && (
          <div className="mt-4 pt-4 border-t border-surface-600">
            <span className="text-xs text-gray-500 mb-1 block">Failure Criteria</span>
            <p className="text-[11px] text-gray-600 mb-3">The test stops when any of these thresholds are breached.</p>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Max TTFT (ms)" tooltip={BREAKING_TOOLTIPS.max_ttft_ms}>
                <input
                  type="number"
                  min={100}
                  value={breakingCriteria.max_ttft_ms}
                  onChange={(e) => setBreakingCriteria({ ...breakingCriteria, max_ttft_ms: Number(e.target.value) })}
                  className="input"
                />
              </Field>
              <Field label="Max ITL (ms)" tooltip={BREAKING_TOOLTIPS.max_itl_ms}>
                <input
                  type="number"
                  min={10}
                  value={breakingCriteria.max_itl_ms}
                  onChange={(e) => setBreakingCriteria({ ...breakingCriteria, max_itl_ms: Number(e.target.value) })}
                  className="input"
                />
              </Field>
              <Field label="Max Error Rate (%)" tooltip={BREAKING_TOOLTIPS.max_error_rate_pct}>
                <input
                  type="number"
                  min={0.1}
                  max={100}
                  step={0.1}
                  value={breakingCriteria.max_error_rate_pct}
                  onChange={(e) => setBreakingCriteria({ ...breakingCriteria, max_error_rate_pct: Number(e.target.value) })}
                  className="input"
                />
              </Field>
            </div>
          </div>
        )}
      </Section>

      {/* Save */}
      <div className="flex gap-3 mt-6 mb-12">
        <button
          onClick={handleSave}
          disabled={saveState === 'saving' || !canSave}
          className={`px-6 py-2.5 text-sm rounded-lg font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed ${saveButtonClass}`}
        >
          {saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Saved!' : isEdit ? 'Save Changes' : 'Create Scenario'}
        </button>
        <button
          onClick={() => navigate('/scenarios')}
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

function Field({ label, tooltip, children }) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500 mb-1 inline-flex items-center gap-1.5">
        {label}
        {tooltip && <InfoTip text={tooltip} />}
      </span>
      {children}
    </label>
  );
}

function SliderField({ label, tooltip, value, min, max, step, onChange }) {
  return (
    <Field label={label} tooltip={tooltip}>
      <div className="flex items-center gap-3">
        <input
          type="range"
          min={min} max={max} step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 accent-accent"
        />
        <input
          type="number"
          min={min} max={max} step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="input w-20 text-center tabular-nums"
        />
      </div>
    </Field>
  );
}
