function minsFromNow(isoStr) {
  if (!isoStr) return null
  const diff = (new Date(isoStr) - Date.now()) / 1000 / 60
  if (diff < 0) return 'Arr'
  if (diff < 1) return '< 1 min'
  return `${Math.round(diff)} min`
}

const LOAD_LABEL = { SEA: 'Seats available', SDA: 'Standing', LSD: 'Limited standing' }
const LOAD_CLASS = { SEA: 'load-green', SDA: 'load-yellow', LSD: 'load-red' }
const TYPE_LABEL = { SD: 'Single deck', DD: 'Double deck', BD: 'Bendy' }

function ArrivalPill({ bus, label }) {
  const mins = minsFromNow(bus?.EstimatedArrival)
  if (!mins) return null
  return (
    <div className="arrival-pill">
      <span className="arrival-label">{label}</span>
      <span className="arrival-time">{mins}</span>
      {bus?.Load && (
        <span className={`load-dot ${LOAD_CLASS[bus.Load] ?? ''}`} title={LOAD_LABEL[bus.Load]} />
      )}
    </div>
  )
}

export default function BusCard({ service }) {
  const { ServiceNo, Operator, NextBus, NextBus2, NextBus3 } = service
  const type = NextBus?.Type

  return (
    <div className="card">
      <div className="card-left">
        <span className="service-no">{ServiceNo}</span>
        <span className="operator">{Operator}</span>
        {type && <span className="bus-type">{TYPE_LABEL[type] ?? type}</span>}
      </div>
      <div className="card-right">
        <ArrivalPill bus={NextBus} label="Next" />
        <ArrivalPill bus={NextBus2} label="2nd" />
        <ArrivalPill bus={NextBus3} label="3rd" />
      </div>
    </div>
  )
}
