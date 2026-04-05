import React, { useState, useEffect, useCallback } from 'react'

const API = '/api'

interface JobResult {
  final_video: string
  final_video_captioned: string
  final_video_music: string
  metadata_path: string
  sources: Array<{ index: number; title: string; url: string; type: string }>
  duration_seconds: number
}

interface Job {
  job_id: string
  status: string
  step: string
  message: string
  result?: JobResult
}

interface ProgressEntry {
  step: string
  message: string
}

const STYLES: Record<string, React.CSSProperties> = {
  body: { fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif', background: '#0d1117', color: '#c9d1d9', minHeight: '100vh', margin: 0, padding: '24px' },
  container: { maxWidth: 900, margin: '0 auto' },
  h1: { fontSize: 28, fontWeight: 700, color: '#58a6ff', marginBottom: 4 },
  subtitle: { color: '#8b949e', marginBottom: 32, fontSize: 14 },
  card: { background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 24, marginBottom: 16 },
  label: { display: 'block', fontSize: 13, color: '#8b949e', marginBottom: 4 },
  input: { width: '100%', padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, color: '#c9d1d9', fontSize: 14, boxSizing: 'border-box' as const },
  select: { padding: '8px 12px', background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, color: '#c9d1d9', fontSize: 14 },
  row: { display: 'flex', gap: 16, marginBottom: 16 },
  col: { flex: 1 },
  btn: { padding: '10px 24px', background: '#238636', color: '#fff', border: 'none', borderRadius: 6, fontSize: 15, fontWeight: 600, cursor: 'pointer' },
  btnDisabled: { padding: '10px 24px', background: '#21262d', color: '#484f58', border: '1px solid #30363d', borderRadius: 6, fontSize: 15, cursor: 'not-allowed' },
  progress: { background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: 12, maxHeight: 300, overflowY: 'auto' as const, fontSize: 13, fontFamily: 'monospace' },
  badge: { display: 'inline-block', padding: '2px 8px', borderRadius: 12, fontSize: 12, fontWeight: 600 },
  sourceCard: { background: '#0d1117', border: '1px solid #30363d', borderRadius: 6, padding: 12, marginBottom: 8 },
}

const statusColors: Record<string, string> = {
  pending: '#d29922',
  running: '#58a6ff',
  completed: '#3fb950',
  failed: '#f85149',
}

export default function App() {
  const [form, setForm] = useState({
    topic: 'Democracy in Hungary',
    language: 'English',
    tone: 'serious',
    duration_seconds: 60,
    num_perspectives: 3,
    orientation: 'landscape',
    resolution: '720p',
    character_gender: 'male',
    character_age: '40',
    character_description: '',
    search_sources: ['web'],
    generate_captions: true,
    background_music_path: '',
    music_volume: 0.12,
  })

  const [activeJob, setActiveJob] = useState<Job | null>(null)
  const [progressLog, setProgressLog] = useState<ProgressEntry[]>([])
  const [metadata, setMetadata] = useState<any>(null)
  const [submitting, setSubmitting] = useState(false)

  const update = (key: string, value: any) => setForm(f => ({ ...f, [key]: value }))

  const submit = async () => {
    setSubmitting(true)
    setProgressLog([])
    setMetadata(null)
    try {
      const resp = await fetch(`${API}/produce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const job: Job = await resp.json()
      setActiveJob(job)
    } catch (e: any) {
      alert(`Error: ${e.message}`)
    }
    setSubmitting(false)
  }

  // Poll job status
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed') return

    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`${API}/jobs/${activeJob.job_id}`)
        const job: Job = await resp.json()
        setActiveJob(job)

        const progResp = await fetch(`${API}/jobs/${activeJob.job_id}/progress`)
        const prog = await progResp.json()
        setProgressLog(prog.progress_log || [])

        if (job.status === 'completed') {
          const metaResp = await fetch(`${API}/jobs/${activeJob.job_id}/metadata`)
          const meta = await metaResp.json()
          setMetadata(meta)
        }
      } catch {}
    }, 3000)

    return () => clearInterval(interval)
  }, [activeJob])

  return (
    <div style={STYLES.body}>
      <div style={STYLES.container}>
        <h1 style={STYLES.h1}>Video Production Agent</h1>
        <p style={STYLES.subtitle}>Generate professional AI videos with research, sources, and captions</p>

        {/* Config Form */}
        <div style={STYLES.card}>
          <div style={STYLES.row}>
            <div style={{ flex: 2 }}>
              <label style={STYLES.label}>Topic / Prompt</label>
              <input style={STYLES.input} value={form.topic} onChange={e => update('topic', e.target.value)} placeholder="e.g. Democracy in Hungary" />
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Language</label>
              <select style={STYLES.select} value={form.language} onChange={e => update('language', e.target.value)}>
                <option>English</option>
                <option>Hungarian</option>
                <option>German</option>
              </select>
            </div>
          </div>

          <div style={STYLES.row}>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Style / Tone</label>
              <select style={STYLES.select} value={form.tone} onChange={e => update('tone', e.target.value)}>
                <option value="serious">Serious</option>
                <option value="casual">Casual</option>
                <option value="funny">Funny</option>
                <option value="dramatic">Dramatic</option>
              </select>
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Duration (seconds)</label>
              <input style={STYLES.input} type="number" value={form.duration_seconds} onChange={e => update('duration_seconds', parseInt(e.target.value) || 60)} />
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Perspectives</label>
              <input style={STYLES.input} type="number" value={form.num_perspectives} min={1} max={6} onChange={e => update('num_perspectives', parseInt(e.target.value) || 3)} />
            </div>
          </div>

          <div style={STYLES.row}>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Orientation</label>
              <select style={STYLES.select} value={form.orientation} onChange={e => update('orientation', e.target.value)}>
                <option value="landscape">Landscape (16:9)</option>
                <option value="portrait">Portrait (9:16)</option>
              </select>
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Resolution</label>
              <select style={STYLES.select} value={form.resolution} onChange={e => update('resolution', e.target.value)}>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Character</label>
              <select style={STYLES.select} value={form.character_gender} onChange={e => update('character_gender', e.target.value)}>
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </div>
          </div>

          <div style={STYLES.row}>
            <div style={{ flex: 2 }}>
              <label style={STYLES.label}>Custom Character Description (optional)</label>
              <input style={STYLES.input} value={form.character_description} onChange={e => update('character_description', e.target.value)} placeholder="Leave empty for default" />
            </div>
          </div>

          <div style={STYLES.row}>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Sources</label>
              <div style={{ display: 'flex', gap: 12 }}>
                {['web', 'knowledge_base', 'wikipedia'].map(s => (
                  <label key={s} style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <input type="checkbox" checked={form.search_sources.includes(s)} onChange={e => {
                      const next = e.target.checked ? [...form.search_sources, s] : form.search_sources.filter(x => x !== s)
                      update('search_sources', next)
                    }} />
                    {s.replace('_', ' ')}
                  </label>
                ))}
              </div>
            </div>
            <div style={STYLES.col}>
              <label style={STYLES.label}>Captions</label>
              <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 4 }}>
                <input type="checkbox" checked={form.generate_captions} onChange={e => update('generate_captions', e.target.checked)} />
                Generate subtitles
              </label>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <button style={submitting || (activeJob?.status === 'running') ? STYLES.btnDisabled : STYLES.btn}
              disabled={submitting || activeJob?.status === 'running'}
              onClick={submit}>
              {submitting ? 'Submitting...' : activeJob?.status === 'running' ? 'Producing...' : 'Produce Video'}
            </button>
          </div>
        </div>

        {/* Progress */}
        {activeJob && (
          <div style={STYLES.card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 16 }}>Production: {activeJob.job_id}</h3>
              <span style={{ ...STYLES.badge, background: statusColors[activeJob.status] || '#484f58', color: '#fff' }}>
                {activeJob.status}
              </span>
            </div>

            {activeJob.status === 'running' && (
              <p style={{ color: '#58a6ff', fontSize: 13 }}>
                Step: <strong>{activeJob.step}</strong> — {activeJob.message}
              </p>
            )}

            {progressLog.length > 0 && (
              <div style={STYLES.progress}>
                {progressLog.map((entry, i) => (
                  <div key={i} style={{ marginBottom: 4 }}>
                    <span style={{ color: '#58a6ff' }}>[{entry.step}]</span> {entry.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Results */}
        {activeJob?.status === 'completed' && activeJob.result && (
          <div style={STYLES.card}>
            <h3 style={{ margin: '0 0 16px', fontSize: 16, color: '#3fb950' }}>Production Complete</h3>

            <div style={STYLES.row}>
              <div style={STYLES.col}>
                <label style={STYLES.label}>Duration</label>
                <p style={{ margin: 0 }}>{Math.floor(activeJob.result.duration_seconds / 60)}:{String(Math.floor(activeJob.result.duration_seconds % 60)).padStart(2, '0')}</p>
              </div>
              <div style={STYLES.col}>
                <label style={STYLES.label}>Video (no captions)</label>
                <a href={`${API}/jobs/${activeJob.job_id}/video`} target="_blank" style={{ color: '#58a6ff' }}>Download</a>
              </div>
              <div style={STYLES.col}>
                <label style={STYLES.label}>Video (captioned)</label>
                <a href={`${API}/jobs/${activeJob.job_id}/video?captioned=true`} target="_blank" style={{ color: '#58a6ff' }}>Download</a>
              </div>
            </div>

            {/* Sources */}
            {activeJob.result.sources.length > 0 && (
              <>
                <h4 style={{ fontSize: 14, color: '#8b949e', marginTop: 16 }}>Sources ({activeJob.result.sources.length})</h4>
                {activeJob.result.sources.map((src) => (
                  <div key={src.index} style={STYLES.sourceCard}>
                    <strong style={{ color: '#58a6ff' }}>Source {src.index}:</strong> {src.title}
                    {src.url && <span style={{ color: '#8b949e', marginLeft: 8, fontSize: 12 }}>— {src.url}</span>}
                    <br />
                    <span style={{ fontSize: 12, color: '#484f58' }}>Type: {src.type}</span>
                  </div>
                ))}
              </>
            )}

            {/* Timestamps */}
            {metadata?.timestamps && (
              <>
                <h4 style={{ fontSize: 14, color: '#8b949e', marginTop: 16 }}>Timestamp Log</h4>
                <div style={STYLES.progress}>
                  {metadata.timestamps.map((ts: any, i: number) => (
                    <div key={i} style={{ marginBottom: 8 }}>
                      <span style={{ color: '#3fb950' }}>{ts.start}–{ts.end}</span>
                      {' '}<span>{ts.text}</span>
                      {ts.source && (
                        <div style={{ color: '#d29922', fontSize: 12, marginLeft: 16 }}>
                          Source {ts.source.index}: {ts.source.title} (shown at {ts.source.shown_at})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Raw metadata */}
            <details style={{ marginTop: 16 }}>
              <summary style={{ cursor: 'pointer', color: '#8b949e', fontSize: 13 }}>Raw Metadata JSON</summary>
              <pre style={{ ...STYLES.progress, marginTop: 8, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(metadata, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  )
}
