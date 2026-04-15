import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { endpointsApi } from '../api/client';
import Spinner from '../components/Spinner';

export default function EndpointEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = !!id;

  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [saveFlash, setSaveFlash] = useState(false);
  const [error, setError] = useState(null);

  // Fields
  const [name, setName] = useState('');
  const [endpointUrl, setEndpointUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [modelName, setModelName] = useState('');
  const [gpu, setGpu] = useState('');
  const [inferenceEngine, setInferenceEngine] = useState('');
  const [notes, setNotes] = useState('');

  // Test connection
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Load existing endpoint
  useEffect(() => {
    if (!isEdit) return;
    (async () => {
      try {
        const res = await endpointsApi.get(id);
        const ep = res.data;
        setName(ep.name);
        setEndpointUrl(ep.endpoint_url);
        setApiKey(ep.api_key || '');
        setModelName(ep.model_name);
        setGpu(ep.gpu || '');
        setInferenceEngine(ep.inference_engine || '');
        setNotes(ep.notes || '');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [id, isEdit]);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await endpointsApi.testConnection({
        endpoint_url: endpointUrl,
        api_key: apiKey || null,
        model_name: modelName,
      });
      setTestResult(res.data);
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const body = {
        name: name.trim(),
        endpoint_url: endpointUrl.trim(),
        api_key: apiKey.trim() || null,
        model_name: modelName.trim(),
        gpu: gpu.trim() || null,
        inference_engine: inferenceEngine.trim() || null,
        notes: notes.trim() || null,
      };

      if (isEdit) {
        await endpointsApi.update(id, body);
      } else {
        const res = await endpointsApi.create(body);
        navigate(`/endpoints/${res.data.id}/edit`, { replace: true });
      }
      setSaveFlash(true);
      setTimeout(() => setSaveFlash(false), 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const canSave = name.trim() && endpointUrl.trim() && modelName.trim();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-2 text-gray-500"><Spinner size="sm" /> Loading endpoint...</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate('/endpoints')} className="text-xs text-gray-500 hover:text-gray-300 mb-1 block">
            &larr; Back to Endpoints
          </button>
          <h1 className="font-heading text-2xl font-bold">
            {isEdit ? 'Edit Endpoint' : 'New Endpoint'}
          </h1>
        </div>
        <button
          onClick={handleSave}
          disabled={!canSave || saving}
          className={`px-5 py-2 text-sm rounded-lg font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
            saveFlash
              ? 'bg-green-500 text-white'
              : 'bg-accent text-surface-900 hover:bg-accent-bright'
          }`}
        >
          {saveFlash ? 'Saved!' : saving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger/10 border border-danger/30 text-danger text-sm">{error}</div>
      )}

      <div className="space-y-6">
        {/* Basic Info */}
        <Section title="Basic Info">
          <div className="grid grid-cols-1 gap-4">
            <Field label="Name">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. DGX Spark — Qwen 32B"
                className="input"
              />
            </Field>
            <Field label="Notes">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Optional notes about this endpoint..."
                className="input"
              />
            </Field>
          </div>
        </Section>

        {/* Connection */}
        <Section title="Connection" subtitle="Works with any OpenAI-compatible API — llama.cpp, vLLM, Ollama, LM Studio, OpenAI, etc.">
          <div className="grid grid-cols-1 gap-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Endpoint URL" tooltip="Base URL of the OpenAI-compatible API. For local LLMs, this is typically http://localhost:PORT. The /v1/chat/completions path is appended automatically.">
                <input
                  type="text"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  placeholder="http://localhost:8081/v1"
                  className="input"
                />
              </Field>
              <Field label="Model Name" tooltip="The model identifier to send in API requests. For local LLMs, check your server's model list. For OpenAI, use names like gpt-4o.">
                <input
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="gpt-3.5-turbo"
                  className="input"
                />
              </Field>
            </div>
            <Field label="API Key" tooltip="Authentication key for the LLM endpoint. Leave empty for local servers that don't require authentication.">
              <div className="flex gap-2">
                <input
                  type={showApiKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Optional — leave blank for local LLMs"
                  className="input flex-1"
                />
                <button
                  type="button"
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="px-3 py-1.5 text-xs rounded bg-surface-700 text-gray-400 hover:text-gray-200 hover:bg-surface-600 transition-colors"
                >
                  {showApiKey ? 'Hide' : 'Show'}
                </button>
              </div>
            </Field>
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestConnection}
                disabled={testing || !endpointUrl.trim() || !modelName.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-surface-700 text-gray-300 hover:bg-surface-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              {testResult && (
                <span className={`text-sm ${testResult.success ? 'text-green-400' : 'text-danger'}`}>
                  {testResult.success
                    ? `Connected (${testResult.latency_ms}ms${testResult.model_reported ? `, model: ${testResult.model_reported}` : ''})`
                    : testResult.error}
                </span>
              )}
            </div>
          </div>
        </Section>

        {/* Hardware Info */}
        <Section title="Hardware" subtitle="Optional metadata to help identify and compare endpoints in benchmark results">
          <div className="grid grid-cols-2 gap-4">
            <Field label="GPU" tooltip="GPU model used for inference, e.g. RTX 4090, H100 SXM, DGX Spark. Displayed in benchmark results for easy comparison.">
              <input
                type="text"
                value={gpu}
                onChange={(e) => setGpu(e.target.value)}
                placeholder="e.g. RTX 4090, H100 SXM"
                className="input"
              />
            </Field>
            <Field label="Inference Engine" tooltip="The software running inference, e.g. llama.cpp, vLLM, TensorRT-LLM, Ollama, OpenAI API.">
              <input
                type="text"
                value={inferenceEngine}
                onChange={(e) => setInferenceEngine(e.target.value)}
                placeholder="e.g. llama.cpp, vLLM"
                className="input"
              />
            </Field>
          </div>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <div className="bg-surface-800 border border-surface-600 rounded-xl p-5">
      <h2 className="font-heading text-sm uppercase tracking-wider text-gray-400 mb-1">{title}</h2>
      {subtitle && <p className="text-xs text-gray-600 mb-4">{subtitle}</p>}
      {!subtitle && <div className="mb-4" />}
      {children}
    </div>
  );
}

function Field({ label, tooltip, children }) {
  const [showTip, setShowTip] = useState(false);
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <label className="text-xs text-gray-400 font-medium">{label}</label>
        {tooltip && (
          <div className="relative">
            <button
              type="button"
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
              className="w-3.5 h-3.5 rounded-full bg-surface-600 text-gray-500 text-[9px] flex items-center justify-center hover:bg-surface-500 hover:text-gray-300 transition-colors"
            >
              ?
            </button>
            {showTip && (
              <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2.5 rounded-lg bg-surface-700 border border-surface-500 text-xs text-gray-300 leading-relaxed shadow-xl">
                {tooltip}
              </div>
            )}
          </div>
        )}
      </div>
      {children}
    </div>
  );
}
