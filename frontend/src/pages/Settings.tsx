import { useState, useEffect } from 'react'
import { 
  Monitor,
  Bell,
  Database,
  Save,
  RotateCcw,
  Loader2,
  CheckCircle,
  Server,
  Zap,
  Shield,
  Clock,
  Camera,
  Mail,
  Key,
  Globe,
  HardDrive,
  Brain,
  Sparkles,
  FileText,
  MessageSquare,
  Settings as SettingsIcon,
  RefreshCw,
  Play,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Check
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import axios from 'axios'
import { AISettings, AISettingsUpdate, QuestionPromptInfo, FormFieldInfo, aiSettingsApi } from '../services/api'

interface SystemInfo {
  name: string
  version: string
  status: string
  database: string
  background_jobs: string
}

export default function Settings() {
  // Browser settings are now part of aiSettingsForm

  // Notification settings
  const [notificationSettings, setNotificationSettings] = useState({
    enableEmailNotifications: false,
    smtpHost: '',
    smtpPort: 587,
    smtpUser: '',
    smtpPassword: '',
  })

  // AI Settings
  const [aiSettings, setAiSettings] = useState<AISettings | null>(null)
  const [aiSettingsForm, setAiSettingsForm] = useState<AISettingsUpdate>({})
  const [questionPromptsList, setQuestionPromptsList] = useState<QuestionPromptInfo[]>([])
  const [formFieldsList, setFormFieldsList] = useState<FormFieldInfo[]>([])
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null)
  const [expandedAnswer, setExpandedAnswer] = useState<string | null>(null)

  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [activeTab, setActiveTab] = useState<'ai' | 'browser' | 'notifications' | 'system'>('ai')

  // Fetch all settings on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true)
      try {
        // Fetch system info
        const { data: sysInfo } = await axios.get<SystemInfo>('/')
        setSystemInfo(sysInfo)

        // Fetch AI settings
        const aiData = await aiSettingsApi.get()
        setAiSettings(aiData)
        setAiSettingsForm({
          openai_model: aiData.openai_model,
          temperature: aiData.temperature,
          max_tokens: aiData.max_tokens,
          enable_resume_generation: aiData.enable_resume_generation,
          enable_cover_letter_generation: aiData.enable_cover_letter_generation,
          enable_answer_generation: aiData.enable_answer_generation,
          resume_tone: aiData.resume_tone,
          resume_format: aiData.resume_format,
          resume_max_pages: aiData.resume_max_pages,
          resume_system_prompt: aiData.resume_system_prompt,
          cover_letter_tone: aiData.cover_letter_tone,
          cover_letter_length: aiData.cover_letter_length,
          cover_letter_system_prompt: aiData.cover_letter_system_prompt,
          question_prompts: aiData.question_prompts,
          default_answers: aiData.default_answers,
          max_concurrent_jobs: aiData.max_concurrent_jobs,
          browser_timeout: aiData.browser_timeout,
          browser_headless: aiData.browser_headless,
          screenshot_on_error: aiData.screenshot_on_error,
          auto_retry_failed: aiData.auto_retry_failed,
          max_retries: aiData.max_retries,
          ai_timeout_seconds: aiData.ai_timeout_seconds,
          use_fallback_on_error: aiData.use_fallback_on_error,
        })

        // Fetch defaults for UI
        const defaults = await aiSettingsApi.getDefaults()
        setQuestionPromptsList(defaults.question_prompts_list)
        setFormFieldsList(defaults.form_fields_list)

      } catch (error) {
        console.error('Failed to fetch settings:', error)
      } finally {
        setIsLoading(false)
      }
    }
    fetchData()
  }, [])

  const handleSaveAI = async () => {
    setIsSaving(true)
    try {
      const updated = await aiSettingsApi.update(aiSettingsForm)
      setAiSettings(updated)
      setSaved(true)
      toast.success('AI settings saved successfully')
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      toast.error('Failed to save AI settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTestConnection = async () => {
    setTestingConnection(true)
    setConnectionStatus('idle')
    try {
      // Save API key first if changed
      if (aiSettingsForm.openai_api_key) {
        await aiSettingsApi.update({ openai_api_key: aiSettingsForm.openai_api_key })
      }
      
      const result = await aiSettingsApi.testConnection()
      if (result.success) {
        setConnectionStatus('success')
        toast.success(result.message)
      } else {
        setConnectionStatus('error')
        toast.error(result.message)
      }
    } catch {
      setConnectionStatus('error')
      toast.error('Connection test failed')
    } finally {
      setTestingConnection(false)
    }
  }

  const handleResetPrompts = async () => {
    if (!confirm('Reset all prompts to defaults? This cannot be undone.')) return
    try {
      await aiSettingsApi.resetPrompts()
      const aiData = await aiSettingsApi.get()
      setAiSettings(aiData)
      setAiSettingsForm(prev => ({
        ...prev,
        question_prompts: aiData.question_prompts,
        default_answers: aiData.default_answers,
      }))
      toast.success('Prompts reset to defaults')
    } catch {
      toast.error('Failed to reset prompts')
    }
  }

  const updateQuestionPrompt = (key: string, value: string) => {
    setAiSettingsForm(prev => ({
      ...prev,
      question_prompts: {
        ...(prev.question_prompts || {}),
        [key]: value,
      },
    }))
  }

  const updateDefaultAnswer = (key: string, value: string) => {
    setAiSettingsForm(prev => ({
      ...prev,
      default_answers: {
        ...(prev.default_answers || {}),
        [key]: value,
      },
    }))
  }

  const handleSaveBrowser = async () => {
    setIsSaving(true)
    try {
      const updated = await aiSettingsApi.update({
        max_concurrent_jobs: aiSettingsForm.max_concurrent_jobs,
        browser_timeout: aiSettingsForm.browser_timeout,
        browser_headless: aiSettingsForm.browser_headless,
        screenshot_on_error: aiSettingsForm.screenshot_on_error,
        auto_retry_failed: aiSettingsForm.auto_retry_failed,
        max_retries: aiSettingsForm.max_retries,
      })
      setAiSettings(updated)
      setSaved(true)
      toast.success('Browser settings saved')
      setTimeout(() => setSaved(false), 2000)
    } catch {
      toast.error('Failed to save browser settings')
    } finally {
      setIsSaving(false)
    }
  }

  const tabs = [
    { id: 'ai' as const, label: 'AI & Prompts', icon: Brain },
    { id: 'browser' as const, label: 'Browser & Automation', icon: Monitor },
    { id: 'notifications' as const, label: 'Notifications', icon: Bell },
    { id: 'system' as const, label: 'System Status', icon: Server },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
        <span className="ml-3 text-surface-400">Loading settings...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Settings</h1>
          <p className="text-surface-400 mt-1">Configure AI, automation, and system preferences</p>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm whitespace-nowrap transition-all",
              activeTab === tab.id
                ? "bg-primary-500/20 text-primary-400 border border-primary-500/30"
                : "bg-surface-800/50 text-surface-400 hover:text-white hover:bg-surface-800 border border-transparent"
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* AI & Prompts Tab */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          {/* Save Button */}
          <div className="flex justify-end">
            <button 
              onClick={handleSaveAI}
              disabled={isSaving}
              className={clsx(
                "btn-primary",
                saved && "bg-emerald-600 hover:bg-emerald-600"
              )}
            >
              {isSaving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : saved ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saved ? 'Saved!' : 'Save AI Settings'}
            </button>
          </div>

          {/* AI Provider Configuration */}
          <div className="card">
            <div className="p-5 border-b border-surface-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-500/20 to-purple-600/10">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">AI Provider</h2>
                  <p className="text-sm text-surface-500">OpenAI API configuration</p>
                </div>
              </div>
            </div>
            <div className="p-5 space-y-5">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <div className="lg:col-span-2">
                  <label className="label flex items-center gap-2">
                    <Key className="w-3.5 h-3.5 text-amber-400" />
                    API Key
                    {aiSettings?.openai_api_key_masked && (
                      <span className="ml-2 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Saved
                      </span>
                    )}
                  </label>
                  {aiSettings?.openai_api_key_masked && !aiSettingsForm.openai_api_key && (
                    <div className="mb-2 px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-sm font-mono text-surface-300">
                      {aiSettings.openai_api_key_masked}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={aiSettingsForm.openai_api_key || ''}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, openai_api_key: e.target.value })}
                      placeholder={aiSettings?.openai_api_key_masked ? 'Enter new key to update...' : 'sk-...'}
                      className="input flex-1"
                    />
                    <button
                      onClick={handleTestConnection}
                      disabled={testingConnection}
                      className={clsx(
                        "btn-secondary px-3",
                        connectionStatus === 'success' && "border-emerald-500 text-emerald-400",
                        connectionStatus === 'error' && "border-red-500 text-red-400"
                      )}
                      title="Test API Connection"
                    >
                      {testingConnection ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : connectionStatus === 'success' ? (
                        <Check className="w-4 h-4" />
                      ) : connectionStatus === 'error' ? (
                        <AlertCircle className="w-4 h-4" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-surface-500 mt-1">
                    {aiSettings?.openai_api_key_masked 
                      ? 'Enter a new key to update, or leave empty to keep existing' 
                      : 'Enter your OpenAI API key to enable AI features'}
                  </p>
                </div>
                <div>
                  <label className="label flex items-center gap-2">
                    <Brain className="w-3.5 h-3.5 text-blue-400" />
                    Model
                  </label>
                  <select
                    value={aiSettingsForm.openai_model || 'gpt-4o'}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, openai_model: e.target.value })}
                    className="input"
                  >
                    <option value="gpt-4o">GPT-4o (Recommended)</option>
                    <option value="gpt-4o-mini">GPT-4o Mini</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  </select>
                </div>
                <div>
                  <label className="label flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5 text-emerald-400" />
                    Temperature
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.1}
                      value={aiSettingsForm.temperature || 0.7}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, temperature: parseFloat(e.target.value) })}
                      className="flex-1 h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                    />
                    <span className="text-sm font-medium text-white w-8">{aiSettingsForm.temperature || 0.7}</span>
                  </div>
                </div>
              </div>

              {/* Feature Toggles */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-surface-800">
                <label className="flex items-center gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSettingsForm.enable_resume_generation ?? true}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, enable_resume_generation: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-white">Resume Generation</p>
                    <p className="text-xs text-surface-500">AI-powered resumes</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSettingsForm.enable_cover_letter_generation ?? true}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, enable_cover_letter_generation: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-white">Cover Letters</p>
                    <p className="text-xs text-surface-500">AI-generated letters</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSettingsForm.enable_answer_generation ?? true}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, enable_answer_generation: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-white">Form Answers</p>
                    <p className="text-xs text-surface-500">Auto-fill responses</p>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Resume & Cover Letter Settings */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Resume Settings */}
            <div className="card">
              <div className="p-5 border-b border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/10">
                    <FileText className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Resume Generation</h2>
                    <p className="text-sm text-surface-500">How AI generates resumes</p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="label text-xs">Tone</label>
                    <select
                      value={aiSettingsForm.resume_tone || 'professional'}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, resume_tone: e.target.value })}
                      className="input text-sm"
                    >
                      <option value="professional">Professional</option>
                      <option value="creative">Creative</option>
                      <option value="technical">Technical</option>
                      <option value="executive">Executive</option>
                    </select>
                  </div>
                  <div>
                    <label className="label text-xs">Format</label>
                    <select
                      value={aiSettingsForm.resume_format || 'bullet'}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, resume_format: e.target.value })}
                      className="input text-sm"
                    >
                      <option value="bullet">Bullet Points</option>
                      <option value="narrative">Narrative</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                  </div>
                  <div>
                    <label className="label text-xs">Max Pages</label>
                    <select
                      value={aiSettingsForm.resume_max_pages || 2}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, resume_max_pages: parseInt(e.target.value) })}
                      className="input text-sm"
                    >
                      <option value={1}>1 Page</option>
                      <option value={2}>2 Pages</option>
                      <option value={3}>3 Pages</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label text-xs">System Prompt (Optional)</label>
                  <textarea
                    value={aiSettingsForm.resume_system_prompt || ''}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, resume_system_prompt: e.target.value })}
                    placeholder="Custom instructions for resume generation..."
                    className="input min-h-[80px] text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Cover Letter Settings */}
            <div className="card">
              <div className="p-5 border-b border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                    <Mail className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Cover Letter Generation</h2>
                    <p className="text-sm text-surface-500">How AI generates cover letters</p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label text-xs">Tone</label>
                    <select
                      value={aiSettingsForm.cover_letter_tone || 'professional'}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, cover_letter_tone: e.target.value })}
                      className="input text-sm"
                    >
                      <option value="professional">Professional</option>
                      <option value="creative">Creative</option>
                      <option value="technical">Technical</option>
                      <option value="executive">Executive</option>
                    </select>
                  </div>
                  <div>
                    <label className="label text-xs">Length</label>
                    <select
                      value={aiSettingsForm.cover_letter_length || 'medium'}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, cover_letter_length: e.target.value })}
                      className="input text-sm"
                    >
                      <option value="short">Short (~150 words)</option>
                      <option value="medium">Medium (~250 words)</option>
                      <option value="long">Long (~400 words)</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label text-xs">System Prompt (Optional)</label>
                  <textarea
                    value={aiSettingsForm.cover_letter_system_prompt || ''}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, cover_letter_system_prompt: e.target.value })}
                    placeholder="Custom instructions for cover letter generation..."
                    className="input min-h-[80px] text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Question Prompts */}
          <div className="card">
            <div className="p-5 border-b border-surface-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/10">
                  <MessageSquare className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">Interview Question Prompts</h2>
                  <p className="text-sm text-surface-500">Templates for generating answers to common questions</p>
                </div>
              </div>
              <button onClick={handleResetPrompts} className="btn-secondary text-xs">
                <RefreshCw className="w-3.5 h-3.5" />
                Reset to Defaults
              </button>
            </div>
            <div className="divide-y divide-surface-800">
              {questionPromptsList.map((q) => (
                <div key={q.key} className="p-4">
                  <button
                    onClick={() => setExpandedPrompt(expandedPrompt === q.key ? null : q.key)}
                    className="w-full flex items-center justify-between text-left"
                  >
                    <div>
                      <p className="text-sm font-medium text-white">{q.name}</p>
                      {q.description && <p className="text-xs text-surface-500">{q.description}</p>}
                    </div>
                    {expandedPrompt === q.key ? (
                      <ChevronUp className="w-4 h-4 text-surface-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-surface-500" />
                    )}
                  </button>
                  {expandedPrompt === q.key && (
                    <textarea
                      value={aiSettingsForm.question_prompts?.[q.key] || ''}
                      onChange={(e) => updateQuestionPrompt(q.key, e.target.value)}
                      className="input mt-3 min-h-[100px] text-sm font-mono"
                      placeholder="Enter prompt template..."
                    />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Default Form Answers */}
          <div className="card">
            <div className="p-5 border-b border-surface-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-pink-500/20 to-pink-600/10">
                  <SettingsIcon className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">Default Form Answers</h2>
                  <p className="text-sm text-surface-500">Auto-fill values for common application fields</p>
                </div>
              </div>
            </div>
            <div className="divide-y divide-surface-800">
              {formFieldsList.map((field) => (
                <div key={field.key} className="p-4">
                  <button
                    onClick={() => setExpandedAnswer(expandedAnswer === field.key ? null : field.key)}
                    className="w-full flex items-center justify-between text-left"
                  >
                    <p className="text-sm font-medium text-white">{field.name}</p>
                    {expandedAnswer === field.key ? (
                      <ChevronUp className="w-4 h-4 text-surface-500" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-surface-500" />
                    )}
                  </button>
                  {expandedAnswer === field.key && (
                    <input
                      type="text"
                      value={aiSettingsForm.default_answers?.[field.key] || ''}
                      onChange={(e) => updateDefaultAnswer(field.key, e.target.value)}
                      className="input mt-3 text-sm"
                      placeholder={`Default value for ${field.name}...`}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Browser & Automation Tab */}
      {activeTab === 'browser' && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <button onClick={handleSaveBrowser} disabled={isSaving} className={clsx("btn-primary", saved && "bg-emerald-600")}>
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              {saved ? 'Saved!' : 'Save Changes'}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Browser Settings */}
            <div className="card">
              <div className="p-5 border-b border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/10">
                    <Monitor className="w-5 h-5 text-primary-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Browser Settings</h2>
                    <p className="text-sm text-surface-500">Configure Chrome automation</p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label flex items-center gap-2">
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      Max Concurrent Jobs
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={aiSettingsForm.max_concurrent_jobs ?? 5}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, max_concurrent_jobs: parseInt(e.target.value) })}
                      className="input"
                    />
                    <p className="text-xs text-surface-500 mt-1">Jobs processed in parallel</p>
                  </div>
                  <div>
                    <label className="label flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-blue-400" />
                      Timeout (sec)
                    </label>
                    <input
                      type="number"
                      min={60}
                      max={600}
                      value={aiSettingsForm.browser_timeout ?? 300}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, browser_timeout: parseInt(e.target.value) })}
                      className="input"
                    />
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="flex items-start gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!(aiSettingsForm.browser_headless ?? false)}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, browser_headless: !e.target.checked })}
                      className="w-5 h-5 mt-0.5 rounded"
                    />
                    <div>
                      <p className="text-sm font-medium text-white">Show Browser Windows</p>
                      <p className="text-xs text-surface-500">Required for OTP/CAPTCHA</p>
                    </div>
                  </label>
                  <label className="flex items-start gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={aiSettingsForm.screenshot_on_error ?? true}
                      onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, screenshot_on_error: e.target.checked })}
                      className="w-5 h-5 mt-0.5 rounded"
                    />
                    <div className="flex items-center gap-2">
                      <Camera className="w-4 h-4 text-surface-400" />
                      <p className="text-sm font-medium text-white">Screenshot on Error</p>
                    </div>
                  </label>
                </div>
              </div>
            </div>

            {/* Retry Settings */}
            <div className="card">
              <div className="p-5 border-b border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/10">
                    <RotateCcw className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">Retry Settings</h2>
                    <p className="text-sm text-surface-500">Automatic retry behavior</p>
                  </div>
                </div>
              </div>
              <div className="p-5 space-y-5">
                <label className="flex items-start gap-3 p-3 rounded-lg bg-surface-800/30 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSettingsForm.auto_retry_failed ?? true}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, auto_retry_failed: e.target.checked })}
                    className="w-5 h-5 mt-0.5 rounded"
                  />
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-surface-400" />
                    <p className="text-sm font-medium text-white">Auto-retry Failed Jobs</p>
                  </div>
                </label>
                <div>
                  <label className="label">Maximum Retries: {aiSettingsForm.max_retries ?? 3}</label>
                  <input
                    type="range"
                    min={0}
                    max={5}
                    value={aiSettingsForm.max_retries ?? 3}
                    onChange={(e) => setAiSettingsForm({ ...aiSettingsForm, max_retries: parseInt(e.target.value) })}
                    className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                    disabled={!(aiSettingsForm.auto_retry_failed ?? true)}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="card">
          <div className="p-5 border-b border-surface-800">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-accent-500/20 to-accent-600/10">
                <Bell className="w-5 h-5 text-accent-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Email Notifications</h2>
                <p className="text-sm text-surface-500">Get notified when jobs complete</p>
              </div>
            </div>
          </div>
          <div className="p-5 space-y-5">
            <label className="flex items-start gap-3 p-4 rounded-lg bg-surface-800/30 cursor-pointer border border-surface-700">
              <input
                type="checkbox"
                checked={notificationSettings.enableEmailNotifications}
                onChange={(e) => setNotificationSettings({ ...notificationSettings, enableEmailNotifications: e.target.checked })}
                className="w-5 h-5 mt-0.5 rounded"
              />
              <div>
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-accent-400" />
                  <p className="text-sm font-medium text-white">Enable Email Notifications</p>
                </div>
                <p className="text-xs text-surface-500 mt-0.5">Receive emails for job completions and errors</p>
              </div>
            </label>

            {notificationSettings.enableEmailNotifications && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-lg border border-surface-700 bg-surface-800/20">
                <div>
                  <label className="label flex items-center gap-2">
                    <Globe className="w-3.5 h-3.5 text-blue-400" />
                    SMTP Host
                  </label>
                  <input
                    type="text"
                    value={notificationSettings.smtpHost}
                    onChange={(e) => setNotificationSettings({ ...notificationSettings, smtpHost: e.target.value })}
                    placeholder="smtp.gmail.com"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label flex items-center gap-2">
                    <Server className="w-3.5 h-3.5 text-purple-400" />
                    SMTP Port
                  </label>
                  <input
                    type="number"
                    value={notificationSettings.smtpPort}
                    onChange={(e) => setNotificationSettings({ ...notificationSettings, smtpPort: parseInt(e.target.value) })}
                    className="input"
                  />
                </div>
                <div>
                  <label className="label flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-emerald-400" />
                    Username
                  </label>
                  <input
                    type="email"
                    value={notificationSettings.smtpUser}
                    onChange={(e) => setNotificationSettings({ ...notificationSettings, smtpUser: e.target.value })}
                    placeholder="your-email@gmail.com"
                    className="input"
                  />
                </div>
                <div>
                  <label className="label flex items-center gap-2">
                    <Key className="w-3.5 h-3.5 text-amber-400" />
                    Password
                  </label>
                  <input
                    type="password"
                    value={notificationSettings.smtpPassword}
                    onChange={(e) => setNotificationSettings({ ...notificationSettings, smtpPassword: e.target.value })}
                    placeholder="••••••••"
                    className="input"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* System Status Tab */}
      {activeTab === 'system' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-emerald-500/20">
                  <Zap className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-xs text-surface-500 uppercase tracking-wider">Status</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 bg-emerald-400 rounded-full animate-pulse" />
                <p className="text-lg font-semibold text-emerald-400">{systemInfo?.status || 'Online'}</p>
              </div>
            </div>
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-blue-500/20">
                  <Database className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-xs text-surface-500 uppercase tracking-wider">Database</p>
              </div>
              <p className="text-lg font-semibold text-white capitalize">{systemInfo?.database || 'SQLite'}</p>
            </div>
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-purple-500/20">
                  <Server className="w-4 h-4 text-purple-400" />
                </div>
                <p className="text-xs text-surface-500 uppercase tracking-wider">Jobs</p>
              </div>
              <p className="text-lg font-semibold text-white capitalize">{systemInfo?.background_jobs || 'Sync'}</p>
            </div>
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-lg bg-amber-500/20">
                  <HardDrive className="w-4 h-4 text-amber-400" />
                </div>
                <p className="text-xs text-surface-500 uppercase tracking-wider">Version</p>
              </div>
              <p className="text-lg font-semibold text-white">{systemInfo?.version || 'v1.0.0'}</p>
            </div>
          </div>

          <div className="card">
            <div className="p-5 border-b border-surface-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10">
                  <Database className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">System Information</h2>
                  <p className="text-sm text-surface-500">Current configuration</p>
                </div>
              </div>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-surface-800/30 border border-surface-700/50">
                  <p className="text-xs text-surface-500 uppercase tracking-wider mb-2">Application</p>
                  <p className="text-white font-medium">{systemInfo?.name || 'Job Application System'}</p>
                </div>
                <div className="p-4 rounded-lg bg-surface-800/30 border border-surface-700/50">
                  <p className="text-xs text-surface-500 uppercase tracking-wider mb-2">AI Model</p>
                  <p className="text-white font-medium">{aiSettings?.openai_model || 'GPT-4o'}</p>
                </div>
                <div className="p-4 rounded-lg bg-surface-800/30 border border-surface-700/50">
                  <p className="text-xs text-surface-500 uppercase tracking-wider mb-2">API Endpoint</p>
                  <p className="text-white font-medium font-mono text-sm">localhost:8000</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
