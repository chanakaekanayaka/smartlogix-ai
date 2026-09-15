// Small, consistent set of line icons used across the dashboard instead of
// emoji. Hand-rolled (no icon library dependency) to match the existing
// inline-SVG style already used in Header / QueryForm / ChatWidget.

function IconBase({ className = 'h-4 w-4', children }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export function MapPinIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12Z" />
      <circle cx="12" cy="9" r="2.5" />
    </IconBase>
  )
}

export function PackageIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M21 8 12 3 3 8v8l9 5 9-5V8Z" />
      <path d="M3 8l9 5 9-5" />
      <path d="M12 13v8" />
    </IconBase>
  )
}

export function WalletIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M3 7a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v3h-5a2.5 2.5 0 0 0 0 5h5v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" />
      <path d="M16 12h.01" />
    </IconBase>
  )
}

export function ClockIcon(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </IconBase>
  )
}

export function ArchiveIcon(props) {
  return (
    <IconBase {...props}>
      <rect x="3" y="4" width="18" height="4.5" rx="1.2" />
      <path d="M4.5 8.5V18a1.5 1.5 0 0 0 1.5 1.5h12a1.5 1.5 0 0 0 1.5-1.5V8.5" />
      <path d="M10 12.5h4" />
    </IconBase>
  )
}

export function WarehouseIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M3 10.5 12 4l9 6.5" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M9 20v-6h6v6" />
    </IconBase>
  )
}

export function TruckIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M3 7h11v9H3z" />
      <path d="M14 10h4l3 3v3h-7z" />
      <circle cx="7.5" cy="18" r="1.6" />
      <circle cx="17" cy="18" r="1.6" />
    </IconBase>
  )
}

export function CreditCardIcon(props) {
  return (
    <IconBase {...props}>
      <rect x="2.5" y="5.5" width="19" height="13" rx="2" />
      <path d="M2.5 10h19" />
      <path d="M6 14.5h4" />
    </IconBase>
  )
}

export function ReceiptIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M6 3h12v18l-2.5-1.5L13 21l-1-1.5L11 21l-2.5-1.5L6 21V3Z" />
      <path d="M8.5 8h7M8.5 12h7" />
    </IconBase>
  )
}

export function RulerIcon(props) {
  return (
    <IconBase {...props}>
      <rect x="3" y="8" width="18" height="8" rx="1.5" />
      <path d="M7 8v3M11 8v3M15 8v3" />
    </IconBase>
  )
}

export function ScaleIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 3v18" />
      <path d="M6 7h12" />
      <path d="M6 7 3 13a3 3 0 0 0 6 0L6 7Z" />
      <path d="M18 7l-3 6a3 3 0 0 0 6 0l-3-6Z" />
    </IconBase>
  )
}

export function LightbulbIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M9 18h6" />
      <path d="M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.45.9 1.15.9 1.9V16h5.2v-.2c0-.75.3-1.45.9-1.9A6 6 0 0 0 12 3Z" />
    </IconBase>
  )
}

export function MapIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4Z" />
      <path d="M9 4v14M15 6v14" />
    </IconBase>
  )
}

export function AlertTriangleIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </IconBase>
  )
}

export function InboxIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M4 12h4l1.5 3h5L16 12h4" />
      <path d="M5 12 4 5h16l-1 7" />
      <path d="M4 12v6a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-6" />
    </IconBase>
  )
}

export function ChevronRightIcon(props) {
  return (
    <IconBase {...props}>
      <path d="M9 6l6 6-6 6" />
    </IconBase>
  )
}
