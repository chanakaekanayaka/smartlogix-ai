import { useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet'
import L from 'leaflet'

// --- Coloured map pins (SVG divIcon, so no image assets to configure) -------
function makePin(color) {
  return L.divIcon({
    className: 'smartlogix-pin',
    html: `
      <svg width="30" height="42" viewBox="0 0 30 42" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 0C6.7 0 0 6.7 0 15c0 11 15 27 15 27s15-16 15-27C30 6.7 23.3 0 15 0Z" fill="${color}"/>
        <circle cx="15" cy="15" r="6" fill="#ffffff"/>
      </svg>`,
    iconSize: [30, 42],
    iconAnchor: [15, 42],
    popupAnchor: [0, -38],
  })
}

const PINS = {
  origin: makePin('#64748b'), // slate  - where the goods come from
  warehouse: makePin('#4f46e5'), // brand  - dispatch warehouse
  destination: makePin('#059669'), // green  - customer
}

const SRI_LANKA_CENTER = [7.8731, 80.7718]

/** Pan/zoom the map so every marker is comfortably in view. */
function FitToMarkers({ points }) {
  const map = useMap()
  useEffect(() => {
    // The map often mounts inside a container that is still settling its
    // layout (e.g. a chat bubble appearing); recalculate its size first.
    map.invalidateSize()
    if (points.length === 1) {
      map.setView(points[0], 9)
    } else if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points).pad(0.25))
    }
  }, [map, points])
  return null
}

/**
 * Interactive map of the shipment: warehouse -> destination (solid line),
 * plus the origin (dashed line to the warehouse) when it differs.
 *
 * @param {object} coordinates backend `coordinates` block
 *   `{ origin, destination, warehouse }` each `{ city, lat, lng, resolved }`
 */
export default function RouteMap({
  coordinates,
  heightClass = 'h-[320px] sm:h-[420px] lg:h-[460px]',
}) {
  const { origin, destination, warehouse } = coordinates || {}

  const points = useMemo(() => {
    const seen = new Set()
    const out = []
    for (const p of [warehouse, destination, origin]) {
      if (!p || typeof p.lat !== 'number' || typeof p.lng !== 'number') continue
      const key = `${p.lat.toFixed(4)},${p.lng.toFixed(4)}`
      if (seen.has(key)) continue
      seen.add(key)
      out.push([p.lat, p.lng])
    }
    return out
  }, [origin, destination, warehouse])

  const hasWarehouse = warehouse && typeof warehouse.lat === 'number'
  const hasDestination = destination && typeof destination.lat === 'number'
  const hasOrigin = origin && typeof origin.lat === 'number'

  const shipmentLeg =
    hasWarehouse && hasDestination
      ? [
          [warehouse.lat, warehouse.lng],
          [destination.lat, destination.lng],
        ]
      : null

  const transferLeg =
    hasOrigin &&
    hasWarehouse &&
    (origin.lat !== warehouse.lat || origin.lng !== warehouse.lng)
      ? [
          [origin.lat, origin.lng],
          [warehouse.lat, warehouse.lng],
        ]
      : null

  const unresolved = [
    ['origin', origin],
    ['destination', destination],
    ['warehouse', warehouse],
  ].filter(([, p]) => p && p.resolved === false && p.city)

  return (
    <div className="overflow-hidden rounded-b-2xl border-t border-slate-100">
      <MapContainer
        center={points[0] || SRI_LANKA_CENTER}
        zoom={7}
        scrollWheelZoom={false}
        className={`w-full border-b border-slate-200 ${heightClass}`}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {transferLeg && (
          <Polyline positions={transferLeg} pathOptions={{ color: '#94a3b8', weight: 3, dashArray: '6 8' }} />
        )}
        {shipmentLeg && (
          <Polyline positions={shipmentLeg} pathOptions={{ color: '#4f46e5', weight: 4 }} />
        )}

        {hasOrigin && (
          <Marker position={[origin.lat, origin.lng]} icon={PINS.origin}>
            <Popup>
              <strong>Origin</strong>
              <br />
              {origin.city || 'Unknown'}
            </Popup>
          </Marker>
        )}
        {hasWarehouse && (
          <Marker position={[warehouse.lat, warehouse.lng]} icon={PINS.warehouse}>
            <Popup>
              <strong>Dispatch warehouse</strong>
              <br />
              {warehouse.city || 'Unknown'}
            </Popup>
          </Marker>
        )}
        {hasDestination && (
          <Marker position={[destination.lat, destination.lng]} icon={PINS.destination}>
            <Popup>
              <strong>Destination</strong>
              <br />
              {destination.city || 'Unknown'}
            </Popup>
          </Marker>
        )}

        <FitToMarkers points={points} />
      </MapContainer>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 bg-slate-50/70 px-5 py-3 text-xs text-slate-500">
        <Legend color="#64748b" label="Origin" />
        <Legend color="#4f46e5" label="Warehouse" />
        <Legend color="#059669" label="Destination" />
        {unresolved.length > 0 && (
          <span className="text-amber-600">
            Approximate location for {unresolved.map(([, p]) => p.city).join(', ')}
          </span>
        )}
      </div>
    </div>
  )
}

function Legend({ color, label }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}
