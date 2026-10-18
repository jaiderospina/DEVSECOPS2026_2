import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import PermissionsWindow from './PermissionsWindow'

createRoot(document.getElementById('root')).render(
  <StrictMode><PermissionsWindow /></StrictMode>,
)
