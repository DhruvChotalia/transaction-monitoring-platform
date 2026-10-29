import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
} from 'recharts'

const API = ''  // nginx proxies /api/* to api-gateway

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

const TOKEN_KEY = 'jwt_token'

function riskColor(level: string) {
  if (level === 'HIGH') return '#f75555'
  if (level === 'MEDIUM') return '#f7c355'
  return '#55c49a'
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loginUser, setLoginUser] = useState('admin')
  const [loginPass, setLoginPass] = useState('admin123')
  const [loginErr, setLoginErr] = useState('')

  const [alerts, setAlerts] = useState<Alert[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [hourly, setHourly] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [selected, setSelected] = useState<Alert | null>(null)
  const [explaining, setExplaining] = useState(false)
  const [liveCount, setLiveCount] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  )

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
    } catch {
      setToken(null)
      localStorage.removeItem(TOKEN_KEY)
    }
  }, [token, authHeaders])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 10000)
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
    }
    return () => ws.close()
  }, [token])

  const login = async () => {
    try {
      const res = await axios.post(`${API}/api/auth/login`, { username: loginUser, password: loginPass })
      localStorage.setItem(TOKEN_KEY, res.data.access_token)
      setToken(res.data.access_token)
      setLoginErr('')
    } catch {
      setLoginErr('Invalid credentials')
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

  if (!token) {
    return (
      <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ background: 'var(--surface)', padding: 40, borderRadius: 'var(--radius)', border: '1px solid var(--border)', width: 360 }}>
          <h2 style={{ marginBottom: 24, color: 'var(--accent)' }}>Transaction Monitor</h2>
          <input value={loginUser} onChange={e => setLoginUser(e.target.value)}
            placeholder="Username" style={inputStyle} />
          <input value={loginPass} onChange={e => setLoginPass(e.target.value)}
            type="password" placeholder="Password" style={inputStyle} />
          {loginErr && <p style={{ color: 'var(--danger)', marginBottom: 12 }}>{loginErr}</p>}
          <button onClick={login} style={btnStyle}>Sign In</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: 'auto auto 1fr', gap: 16, padding: 20, minHeight: '100vh' }}>

      {/* Header */}
      <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 20, color: 'var(--accent)' }}>Transaction Monitoring Platform</h1>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <span style={{ color: 'var(--success)', fontSize: 12 }}>● LIVE +{liveCount} alerts</span>
          <button onClick={() => { setToken(null); localStorage.removeItem(TOKEN_KEY) }} style={{ ...btnStyle, padding: '6px 14px', fontSize: 12 }}>Logout</button>
        </div>
      </div>

      {/* Stats */}
      <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 12 }}>
        {stats && [
          { label: 'Total Alerts', value: stats.total_alerts, color: 'var(--text)' },
          { label: 'Last Hour', value: stats.alerts_last_hour, color: 'var(--warning)' },
          { label: 'High Risk', value: stats.high_risk_count, color: 'var(--danger)' },
          { label: 'Avg Fraud Prob', value: `${(Number(stats.avg_fraud_prob) * 100).toFixed(1)}%`, color: 'var(--accent)' },
          { label: 'Flagged Amount', value: `$${Number(stats.total_flagged_amount).toLocaleString()}`, color: 'var(--success)' },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, background: 'var(--surface)', borderRadius: 'var(--radius)', padding: '16px 20px', border: '1px solid var(--border)' }}>
            <div style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Alert Feed */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Live Alert Feed</h3>
        <div style={{ overflowY: 'auto', maxHeight: 420 }}>
          {alerts.map(a => (
            <div key={a.id} onClick={() => { setSelected(a); fetchExplanation(a) }}
              style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)', cursor: 'pointer', background: selected?.id === a.id ? 'var(--surface2)' : 'transparent', transition: 'background 0.15s' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>{a.transaction_id.slice(0, 12)}…</span>
                <span style={{ color: riskColor(a.risk_level), fontSize: 11, fontWeight: 700 }}>{a.risk_level}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                <span style={{ color: 'var(--warning)' }}>${a.amount?.toFixed(2)}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{a.merchant_category} · {a.hour_of_day}:00</span>
                <span style={{ color: 'var(--danger)', fontSize: 11 }}>{(a.fraud_probability * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Explanation Panel */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>AI Explanation</h3>
        {selected ? (
          <div>
            <div style={{ marginBottom: 12, padding: 12, background: 'var(--surface2)', borderRadius: 8 }}>
              <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                <span style={{ color: 'var(--warning)' }}>${selected.amount?.toFixed(2)}</span>
                <span style={{ color: riskColor(selected.risk_level) }}>{selected.risk_level}</span>
                <span style={{ color: 'var(--danger)' }}>{(selected.fraud_probability * 100).toFixed(1)}% fraud prob</span>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>{selected.merchant_name} · {selected.merchant_category}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {selected.rule_flags?.map(f => (
                  <span key={f} style={{ background: 'var(--border)', padding: '2px 8px', borderRadius: 4, fontSize: 11 }}>{f}</span>
                ))}
              </div>
            </div>
            <div style={{ lineHeight: 1.7, color: explaining ? 'var(--text-muted)' : 'var(--text)' }}>
              {explaining ? '⏳ Generating AI explanation...' : selected.ai_explanation || 'Click an alert to load explanation'}
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', marginTop: 20 }}>Select an alert from the feed to see the AI explanation.</div>
        )}
      </div>

      {/* Hourly Chart */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Alerts by Hour of Day</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={hourly}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="hour_of_day" stroke="var(--text-muted)" fontSize={11} />
            <YAxis stroke="var(--text-muted)" fontSize={11} />
            <Tooltip contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)' }} />
            <Bar dataKey="alert_count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Category Chart */}
      <div style={cardStyle}>
        <h3 style={cardTitle}>Top Alert Categories</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={categories} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" stroke="var(--text-muted)" fontSize={11} />
            <YAxis dataKey="merchant_category" type="category" stroke="var(--text-muted)" fontSize={10} width={90} />
            <Tooltip contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)' }} />
            <Bar dataKey="alert_count" fill="var(--danger)" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

    </div>
  )
}

const cardStyle: React.CSSProperties = {
  background: 'var(--surface)',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  padding: 20,
}

const cardTitle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: 'var(--text-muted)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 14,
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  padding: '10px 14px',
  background: 'var(--surface2)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  color: 'var(--text)',
  marginBottom: 12,
  fontSize: 14,
}

const btnStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  padding: '11px 14px',
  background: 'var(--accent)',
  color: '#fff',
  border: 'none',
  borderRadius: 8,
  cursor: 'pointer',
  fontSize: 14,
  fontWeight: 600,
}
