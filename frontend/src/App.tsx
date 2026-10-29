import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid,
} from 'recharts'

const API = ''
const TOKEN_KEY = 'jwt_token'

interface Alert {
  id: number
  transaction_id: string
  amount: number
  merchant_category: string
  merchant_name: string
  cardholder_id: string
  hour_of_day: number
  fraud_probability: number
  rule_flags: string[]
  risk_level: string
  ai_explanation: string | null
  created_at: string
}

interface Stats {
  total_alerts: number
  alerts_last_hour: number
  avg_fraud_prob: number
  total_flagged_amount: number
  high_risk_count: number
}

function riskClass(level: string) {
  if (level === 'HIGH') return 'high'
  if (level === 'MEDIUM') return 'medium'
  return 'low'
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  return `${Math.floor(m / 60)}h ago`
}

function StatCard({ label, value, sub, variant }: { label: string; value: string | number; sub?: string; variant: string }) {
  return (
    <div className={`stat-card ${variant}`}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--text)', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{sub}</div>}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} style={{ color: p.color || 'var(--accent)' }}>{p.name}: <b>{p.value}</b></div>
      ))}
    </div>
  )
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loginUser, setLoginUser] = useState('admin')
  const [loginPass, setLoginPass] = useState('admin123')
  const [loginErr, setLoginErr] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  const [alerts, setAlerts] = useState<Alert[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [hourly, setHourly] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [selected, setSelected] = useState<Alert | null>(null)
  const [explaining, setExplaining] = useState(false)
  const [liveCount, setLiveCount] = useState(0)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const authHeaders = useCallback(() => ({ Authorization: `Bearer ${token}` }), [token])

  const loadData = useCallback(async () => {
    if (!token) return
    try {
      const [alertsRes, statsRes, hourlyRes, catRes] = await Promise.all([
        axios.get(`${API}/api/alerts?limit=100`, { headers: authHeaders() }),
        axios.get(`${API}/api/stats`, { headers: authHeaders() }),
        axios.get('http://localhost:8006/analytics/hourly'),
        axios.get('http://localhost:8006/analytics/categories'),
      ])
      setAlerts(alertsRes.data)
      setStats(statsRes.data)
      setHourly(hourlyRes.data)
      setCategories(catRes.data)
      setLastUpdate(new Date())
    } catch {
      setToken(null)
      localStorage.removeItem(TOKEN_KEY)
    }
  }, [token, authHeaders])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 3000)
    return () => clearInterval(interval)
  }, [loadData])

  useEffect(() => {
    if (!token) return
    const ws = new WebSocket('ws://localhost:8006/ws/alerts')
    wsRef.current = ws
    ws.onmessage = (e) => {
      const alert: Alert = JSON.parse(e.data)
      setAlerts(prev => [alert, ...prev].slice(0, 200))
      setLiveCount(c => c + 1)
      setLastUpdate(new Date())
    }
    return () => ws.close()
  }, [token])

  const login = async () => {
    setLoginLoading(true)
    setLoginErr('')
    try {
      const res = await axios.post(`${API}/api/auth/login`, { username: loginUser, password: loginPass })
      localStorage.setItem(TOKEN_KEY, res.data.access_token)
      setToken(res.data.access_token)
    } catch {
      setLoginErr('Invalid credentials')
    } finally {
      setLoginLoading(false)
    }
  }

  const fetchExplanation = async (alert: Alert) => {
    if (alert.ai_explanation) return
    setExplaining(true)
    try {
      const res = await axios.get(`${API}/api/alerts/${alert.id}/explanation`, { headers: authHeaders() })
      setSelected(prev => prev ? { ...prev, ai_explanation: res.data.explanation } : prev)
      setAlerts(prev => prev.map(a => a.id === alert.id ? { ...a, ai_explanation: res.data.explanation } : a))
    } catch {}
    setExplaining(false)
  }

  const selectAlert = (a: Alert) => {
    setSelected(a)
    fetchExplanation(a)
  }

  if (!token) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
        <div style={{ width: 380 }}>
          {/* Logo area */}
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ width: 48, height: 48, borderRadius: 14, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: 22 }}>⚡</div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)' }}>Transaction Monitor</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>Real-time fraud detection platform</p>
          </div>

          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 32 }}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>Username</label>
              <input value={loginUser} onChange={e => setLoginUser(e.target.value)}
                placeholder="admin"
                style={{ width: '100%', padding: '10px 14px', background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 8, color: 'var(--text)', fontSize: 14, outline: 'none' }}
                onKeyDown={e => e.key === 'Enter' && login()} />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>Password</label>
              <input value={loginPass} onChange={e => setLoginPass(e.target.value)}
                type="password" placeholder="••••••••"
                style={{ width: '100%', padding: '10px 14px', background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 8, color: 'var(--text)', fontSize: 14, outline: 'none' }}
                onKeyDown={e => e.key === 'Enter' && login()} />
            </div>
            {loginErr && <div style={{ background: 'var(--danger-glow)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8, padding: '8px 12px', color: 'var(--danger)', fontSize: 13, marginBottom: 16 }}>{loginErr}</div>}
            <button onClick={login} disabled={loginLoading}
              style={{ width: '100%', padding: '11px', background: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14, fontWeight: 600, opacity: loginLoading ? 0.7 : 1 }}>
              {loginLoading ? 'Signing in…' : 'Sign In'}
            </button>
            <p style={{ textAlign: 'center', color: 'var(--text-dim)', fontSize: 12, marginTop: 16 }}>demo · admin / admin123</p>
          </div>
        </div>
      </div>
    )
  }

  const highCount = alerts.filter(a => a.risk_level === 'HIGH').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--bg)' }}>

      {/* Top nav */}
      <nav style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: '0 24px', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky', top: 0, zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 32, height: 32, borderRadius: 9, background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>⚡</div>
          <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)' }}>TxMonitor</span>
          <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>/</span>
          <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Fraud Dashboard</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
            <span className="live-dot" />
            <span style={{ color: 'var(--success)', fontWeight: 500 }}>LIVE</span>
            {liveCount > 0 && <span style={{ color: 'var(--text-muted)' }}>+{liveCount} alerts</span>}
          </div>
          {lastUpdate && <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>Updated {timeAgo(lastUpdate.toISOString())}</span>}
          <button onClick={() => { setToken(null); localStorage.removeItem(TOKEN_KEY) }}
            style={{ padding: '5px 14px', background: 'var(--surface3)', border: '1px solid var(--border2)', borderRadius: 6, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>
            Sign out
          </button>
        </div>
      </nav>

      <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20, flex: 1 }}>

        {/* Stats row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
          <StatCard label="Total Alerts" value={stats?.total_alerts ?? '—'} sub="all time" variant="blue" />
          <StatCard label="Last Hour" value={stats?.alerts_last_hour ?? '—'} sub="recent activity" variant="amber" />
          <StatCard label="High Risk" value={highCount} sub={`${alerts.length} total loaded`} variant="red" />
          <StatCard label="Avg Fraud Prob" value={stats ? `${(stats.avg_fraud_prob * 100).toFixed(1)}%` : '—'} sub="ML model score" variant="purple" />
          <StatCard label="Flagged Amount" value={stats ? `$${(stats.total_flagged_amount / 1000).toFixed(1)}k` : '—'} sub="USD at risk" variant="green" />
        </div>

        {/* Main content: alerts + detail */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

          {/* Alert Feed */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Live Alert Feed</span>
              <span style={{ background: 'var(--surface3)', border: '1px solid var(--border2)', borderRadius: 20, padding: '2px 10px', fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{alerts.length}</span>
            </div>
            <div style={{ overflowY: 'auto', maxHeight: 380 }}>
              {alerts.length === 0 ? (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-dim)' }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>🔍</div>
                  <div>No alerts yet — run the simulation</div>
                  <code style={{ fontSize: 11, color: 'var(--accent)', marginTop: 8, display: 'block' }}>python simulation/send_transactions.py</code>
                </div>
              ) : alerts.map(a => (
                <div key={a.id}
                  className={`alert-row ${riskClass(a.risk_level)} ${selected?.id === a.id ? 'active' : ''}`}
                  onClick={() => selectAlert(a)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <div>
                      <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>{a.transaction_id.slice(0, 14)}…</span>
                      <span style={{ color: 'var(--text-dim)', fontSize: 11, marginLeft: 8 }}>{timeAgo(a.created_at)}</span>
                    </div>
                    <span className={`badge badge-${riskClass(a.risk_level)}`}>{a.risk_level}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: 15 }}>${a.amount?.toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{a.merchant_name}</span>
                    <span style={{ marginLeft: 'auto', color: a.fraud_probability > 0.7 ? 'var(--danger)' : 'var(--warning)', fontSize: 12, fontWeight: 600 }}>
                      {(a.fraud_probability * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                    {a.merchant_category} · {a.hour_of_day}:00h · {a.rule_flags?.length ?? 0} rule{a.rule_flags?.length !== 1 ? 's' : ''} fired
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Detail Panel */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Alert Detail</span>
              {selected && <span className={`badge badge-${riskClass(selected.risk_level)}`}>{selected.risk_level}</span>}
            </div>
            <div style={{ overflowY: 'auto', maxHeight: 380 }}>
              {!selected ? (
                <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-dim)' }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>👆</div>
                  <div>Select an alert to see details</div>
                </div>
              ) : (
                <div style={{ padding: 16 }}>
                  {/* Amount + ID */}
                  <div style={{ background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 10, padding: 16, marginBottom: 14 }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
                      ${selected.amount?.toLocaleString('en', { minimumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{selected.merchant_name} · {selected.merchant_category}</div>
                    <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
                      <span>🕐 {selected.hour_of_day}:00h</span>
                      <span>👤 {selected.cardholder_id}</span>
                      <span style={{ color: selected.fraud_probability > 0.7 ? 'var(--danger)' : 'var(--warning)' }}>
                        🤖 {(selected.fraud_probability * 100).toFixed(1)}% fraud
                      </span>
                    </div>
                  </div>

                  {/* Rule flags */}
                  {selected.rule_flags?.length > 0 && (
                    <div style={{ marginBottom: 14 }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Triggered Rules</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                        {selected.rule_flags.map(f => <span key={f} className="rule-tag">⚠ {f}</span>)}
                      </div>
                    </div>
                  )}

                  {/* AI Explanation */}
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>AI Explanation</div>
                    <div style={{ background: 'var(--surface2)', border: '1px solid var(--border2)', borderRadius: 10, padding: 14, fontSize: 13, lineHeight: 1.7 }}>
                      {explaining ? (
                        <span style={{ color: 'var(--text-muted)' }}>⏳ Generating explanation…</span>
                      ) : selected.ai_explanation ? (
                        <span style={{ color: 'var(--text)' }}>{selected.ai_explanation}</span>
                      ) : (
                        <span style={{ color: 'var(--text-dim)' }}>No ANTHROPIC_API_KEY set — add it to .env to enable AI explanations</span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Charts row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

          {/* Hourly */}
          <div className="card">
            <div className="card-header"><span className="card-title">Alerts by Hour of Day</span></div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={180}>
                <AreaChart data={hourly} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <defs>
                    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="hour_of_day" stroke="var(--text-dim)" fontSize={10} tickLine={false} />
                  <YAxis stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="alert_count" name="Alerts" stroke="#3b82f6" strokeWidth={2} fill="url(#areaGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Categories */}
          <div className="card">
            <div className="card-header"><span className="card-title">Top Alert Categories</span></div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={categories} layout="vertical" margin={{ top: 4, right: 4, bottom: 0, left: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis dataKey="merchant_category" type="category" stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="alert_count" name="Alerts" fill="#ef4444" radius={[0, 4, 4, 0]} maxBarSize={18} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
