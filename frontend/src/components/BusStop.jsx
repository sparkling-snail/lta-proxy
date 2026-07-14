import BusCard from './BusCard'

export default function BusStop({ data, lastUpdated, loading, onRefresh }) {
  const services = data?.Services ?? []

  return (
    <section className="busstop">
      <div className="busstop-header">
        <div>
          <h2 className="stop-code">Stop {data.BusStopCode}</h2>
          {lastUpdated && (
            <p className="updated">
              Updated {lastUpdated.toLocaleTimeString()}
              {loading && ' · refreshing…'}
            </p>
          )}
        </div>
        <button className="refresh-btn" onClick={onRefresh} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {services.length === 0 ? (
        <p className="empty">No services found for this stop.</p>
      ) : (
        <div className="cards">
          {services.map(svc => (
            <BusCard key={svc.ServiceNo} service={svc} />
          ))}
        </div>
      )}
    </section>
  )
}
