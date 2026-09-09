import React from 'react'
import ReactDOM from 'react-dom/client'

// Leaflet's stylesheet must load before any map renders.
import 'leaflet/dist/leaflet.css'
import './index.css'

import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
