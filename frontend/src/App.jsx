import { useState, useEffect, useCallback } from 'react'
import BusStop from './components/BusStop'

const API_BASE = 'http://localhost:8000'

const POPULAR_STOPS = [
  { code: '83139', name: 'Sengkang Int' },
  { code: '75009', name: 'Tampines Int' },
  { code: '01012', name: 'Opp Nat Library' },
  { code: '65199', name: 'Compassvale Rd' },
]

export default function App() {
  const [input, setInput] = useState('')
  const [stopCode, setStopCode] = useState('83139')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [stale, setStale] = useState(false)

  const fetchArrivals = useCallback(async (code) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/arrivals/${code}`)
      setStale(res.headers.get('x-served-from') === 'stale-cache')
      if (!res.ok) throw new Error(`HTTP ${res.status} — check your bus stop code`)
      const json = await res.json()
      setData(json)
      setLastUpdated(new Date())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchArrivals(stopCode)
    const interval = setInterval(() => fetchArrivals(stopCode), 20000)
    return () => clearInterval(interval)
  }, [stopCode, fetchArrivals])

  const handleSearch = (e) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (trimmed) {
      setStopCode(trimmed)
      setInput('')
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <h1 className="title">🚌 LTA Bus Arrivals</h1>
          <p className="subtitle">Singapore real-time bus timings</p>
        </div>
      </header>

      <main className="main">
        <form onSubmit={handleSearch} className="search-form">
          <input
            className="search-input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Enter bus stop code (e.g. 83139)"
            maxLength={6}
          />
          <button className="search-btn" type="submit">Search</button>
        </form>

        <div className="chips">
          {POPULAR_STOPS.map(s => (
            <button
              key={s.code}
              className={`chip ${stopCode === s.code ? 'chip-active' : ''}`}
              onClick={() => setStopCode(s.code)}
            >
              {s.name}
              <span className="chip-code">{s.code}</span>
            </button>
          ))}
        </div>

        {stale && (
          <div className="banner banner-warn">
            Showing cached data — LTA upstream may be unavailable
          </div>
        )}

        {error && (
          <div className="banner banner-error">{error}</div>
        )}

        {loading && !data && (
          <div className="loading">Fetching arrivals...</div>
        )}

        {data && (
          <BusStop
            data={data}
            lastUpdated={lastUpdated}
            loading={loading}
            onRefresh={() => fetchArrivals(stopCode)}
          />
        )}
      </main>
    </div>
  )
}
