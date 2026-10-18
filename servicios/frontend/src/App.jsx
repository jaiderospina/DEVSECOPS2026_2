// =========================================================

import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import usePermissionWindow from './usePermissionWindow'
import PermissionCards from './PermissionCards'
import BulkUserImport from './BulkUserImport'
import AuditReport from './AuditReport'

const API_URL = (
  import.meta.env.VITE_API_URL?.trim().replace(/\/$/, '') ||
  `${window.location.protocol}//${window.location.hostname}:8003`
)

const configuredInactivity = Number(
  import.meta.env.VITE_SESSION_INACTIVITY_MINUTES || 5
)
const SESSION_INACTIVITY_MINUTES = Number.isFinite(configuredInactivity) && configuredInactivity > 0
  ? Math.min(configuredInactivity, 5) : 5

const SESSION_INACTIVITY_MS =
  SESSION_INACTIVITY_MINUTES * 60 * 1000

const ROLES_LIDER = [
  'LIDER_FACTURACION',
  'LIDER_LOGISTICA',
  'LIDER_GESTION_HUMANA',
]

const textoError = (datos, fallback) => {
  if (typeof datos?.detail === 'string') return datos.detail
  if (Array.isArray(datos?.detail)) {
    return datos.detail.map((item) => item.msg).filter(Boolean).join(' · ') || fallback
  }
  return fallback
}

function App() {
  // =========================================================
  // SESIÓN Y AUTENTICACIÓN
  // =========================================================
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token, setToken] = useState(
    sessionStorage.getItem('iam_access_token') || ''
  )
  const [usuario, setUsuario] = useState(null)
  const idleDeadline = useRef(0)
  const [companias, setCompanias] = useState([])
  const [vistaActual, setVistaActual] = useState('panel')
  const [cargando, setCargando] = useState(false)
  const [verificandoSesion, setVerificandoSesion] = useState(Boolean(token))
  const [error, setError] = useState('')

  // =========================================================
  // DATOS ADMINISTRATIVOS
  // =========================================================
  const [usuariosAdministrables, setUsuariosAdministrables] = useState([])
  const [asignaciones, setAsignaciones] = useState([])
  const [sesiones, setSesiones] = useState([])
  const [cargandoVista, setCargandoVista] = useState(false)
  const [mensajeVista, setMensajeVista] = useState('')
  const [errorVista, setErrorVista] = useState('')

  // =========================================================
  // FORMULARIOS
  // =========================================================
  const [mostrarCambioPassword, setMostrarCambioPassword] = useState(false)
  const [cambioPassword, setCambioPassword] = useState({
    password_actual: '',
    password_nuevo: '',
    confirmar_password: '',
  })

  const [mostrarNuevaCompania, setMostrarNuevaCompania] = useState(false)
  const [nuevaCompania, setNuevaCompania] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
  })

  // =========================================================
  // EDICIÓN ADMINISTRATIVA
  // =========================================================
  // Los formularios de edición solo manejan datos básicos.
  // Estado, rol, MFA, contraseña y alcance de compañías se
  // mantienen en flujos separados con autorización específica.
  const [mostrarEditarCompania, setMostrarEditarCompania] = useState(false)
  const [companiaEditar, setCompaniaEditar] = useState(null)
  const [edicionCompania, setEdicionCompania] = useState({
    codigo: '',
    nombre: '',
    descripcion: '',
  })

  const [mostrarEditarUsuario, setMostrarEditarUsuario] = useState(false)
  const [usuarioEditar, setUsuarioEditar] = useState(null)
  const [edicionUsuario, setEdicionUsuario] = useState({
    id_externo: '',
    nombre: '',
    email: '',
  })

  const [mostrarNuevaIdentidad, setMostrarNuevaIdentidad] = useState(false)
  const [nuevaIdentidad, setNuevaIdentidad] = useState({
    id_externo: '',
    nombre: '',
    email: '',
    rol: 'LIDER_FACTURACION',
    compania_id: '',
  })

  // =========================================================
  // ADMIN_TI: CREACIÓN DE ADMIN_SOPORTE
  // =========================================================
  // Este formulario es independiente de la creación de líderes.
  // El rol no es seleccionable desde la interfaz: siempre se
  // envía ADMIN_SOPORTE y el backend vuelve a validar el RBAC.
  //
  // SEGURIDAD:
  // - ADMIN_TI no define ni recibe la contraseña temporal.
  // - La contraseña temporal se genera exclusivamente en backend.
  // - El backend almacena únicamente el hash Argon2.
  // - La contraseña temporal se envía al correo registrado.
  // =========================================================
  const [mostrarNuevoAdminSoporte, setMostrarNuevoAdminSoporte] =
    useState(false)

  const [nuevoAdminSoporte, setNuevoAdminSoporte] = useState({
    id_externo: '',
    nombre: '',
    email: '',
    compania_id: '',
  })

  const [mostrarAsignacion, setMostrarAsignacion] = useState(false)


  // =========================================================
  // MFA / AUTHENTICATOR
  // =========================================================
  // El QR se mantiene únicamente como Blob URL en memoria.
  // No se almacena el secreto TOTP, la URI otpauth ni el QR en
  // localStorage/sessionStorage.
  const [mfaEnrolamientoIniciado, setMfaEnrolamientoIniciado] =
    useState(false)
  const [mfaQrUrl, setMfaQrUrl] = useState('')
  const [mfaCodigo, setMfaCodigo] = useState('')
  const [mfaProcesando, setMfaProcesando] = useState(false)
  const [mfaActivo, setMfaActivo] = useState(false)

  // =========================================================
  // MFA / AUTHENTICATOR - SEGUNDO FACTOR DEL LOGIN
  // =========================================================
  // El desafío se conserva únicamente en memoria de React.
  // No se guarda en localStorage ni sessionStorage y se elimina
  // al cancelar, completar o reiniciar el flujo de autenticación.
  // =========================================================
  const [mfaLoginPendiente, setMfaLoginPendiente] = useState(false)
  const [mfaLoginDesafio, setMfaLoginDesafio] = useState('')
  const [mfaLoginCodigo, setMfaLoginCodigo] = useState('')
  const [mfaLoginProcesando, setMfaLoginProcesando] = useState(false)

  // =========================================================
  // MFA OBLIGATORIO - ENROLAMIENTO PREVIO A LA SESIÓN
  // =========================================================
  // Para usuarios que aún no tienen MFA activo. El desafío y el
  // QR permanecen solo en memoria; no se crea JWT hasta confirmar
  // correctamente el primer código TOTP.
  const [mfaObligatorioPendiente, setMfaObligatorioPendiente] = useState(false)
  const [mfaObligatorioDesafio, setMfaObligatorioDesafio] = useState('')
  const [mfaObligatorioQrUrl, setMfaObligatorioQrUrl] = useState('')
  const [mfaObligatorioCodigo, setMfaObligatorioCodigo] = useState('')
  const [mfaObligatorioProcesando, setMfaObligatorioProcesando] = useState(false)

    // =========================================================
  // MODAL: RESTABLECER ACCESO
  // =========================================================
  // Guarda únicamente la identidad seleccionada.
  //
  // SEGURIDAD:
  // - No almacena contraseñas.
  // - No recibe la contraseña temporal.
  // - La contraseña temporal será generada exclusivamente
  //   por el backend y enviada al correo registrado.
  // =========================================================

  const [mostrarRestablecerAcceso, setMostrarRestablecerAcceso] =
    useState(false)

  const [usuarioRestablecer, setUsuarioRestablecer] =
    useState(null)

  const [restableciendoAcceso, setRestableciendoAcceso] =
    useState(false)

  // =========================================================
  // MODAL: RESTABLECER MFA - ADMIN_TI / ADMIN_SOPORTE
  // =========================================================
  // Guarda únicamente la identidad seleccionada.
  // El administrador nunca recibe el secreto TOTP, QR ni códigos.
  const [mostrarRestablecerMfa, setMostrarRestablecerMfa] = useState(false)
  const [usuarioRestablecerMfa, setUsuarioRestablecerMfa] = useState(null)
  const [restableciendoMfa, setRestableciendoMfa] = useState(false)

  // Modal consolidado ADMIN_TI -> ADMIN_SOPORTE.
  // Solo guarda IDs de compañías; nunca maneja credenciales ni secretos.
  const [adminAsignacion, setAdminAsignacion] = useState(null)
  const [companiasSeleccionadas, setCompaniasSeleccionadas] = useState([])

  const roles = usuario?.roles || []
  const esAdminTI = roles.includes('ADMIN_TI')
  const esAdminSoporte = roles.includes('ADMIN_SOPORTE')
  const rolLider = ROLES_LIDER.find((rol) => roles.includes(rol)) || null
  const esLider = Boolean(rolLider)

  // =========================================================
  // CIERRE LOCAL CENTRALIZADO
  // =========================================================
  // Se utiliza cuando el backend informa que la sesión dejó de
  // ser válida (revocación, expiración absoluta o inactividad).
  //
  // IMPORTANTE:
  // - No modifica ninguna contraseña.
  // - No modifica requiere_cambio_password.
  // - No intenta conservar un JWT inválido.
  // =========================================================
  const limpiarSesionLocal = (mensaje = '') => {
    idleDeadline.current = 0
    sessionStorage.removeItem('iam_access_token')
    setToken('')
    setUsuario(null)
    setCompanias([])
    setUsuariosAdministrables([])
    setAsignaciones([])
    setSesiones([])
    setVistaActual('panel')
    setMostrarCambioPassword(false)
    setMostrarNuevoAdminSoporte(false)
    setNuevoAdminSoporte({
      id_externo: '',
      nombre: '',
      email: '',
      compania_id: '',
    })
    setMostrarEditarCompania(false)
    setCompaniaEditar(null)
    setEdicionCompania({
      codigo: '',
      nombre: '',
      descripcion: '',
    })
    setMostrarEditarUsuario(false)
    setUsuarioEditar(null)
    setEdicionUsuario({
      id_externo: '',
      nombre: '',
      email: '',
    })
    setMostrarRestablecerMfa(false)
    setUsuarioRestablecerMfa(null)
    setRestableciendoMfa(false)
    setMfaEnrolamientoIniciado(false)
    setMfaCodigo('')
    setMfaProcesando(false)
    setMfaActivo(false)
    setMfaLoginPendiente(false)
    setMfaLoginDesafio('')
    setMfaLoginCodigo('')
    setMfaLoginProcesando(false)
    setMfaObligatorioPendiente(false)
    setMfaObligatorioDesafio('')
    setMfaObligatorioCodigo('')
    setMfaObligatorioProcesando(false)
    limpiarQrMfaObligatorio()
    limpiarQrMfa()
    setCambioPassword({
      password_actual: '',
      password_nuevo: '',
      confirmar_password: '',
    })
    setMensajeVista('')
    setErrorVista('')
    if (mensaje) setError(mensaje)
  }

  const abrirGrillaPermisos = usePermissionWindow({ token, usuario,
    idleDeadline, onExpired: limpiarSesionLocal, onError: setErrorVista })

  // =========================================================
  // LIMPIEZA DEL QR MFA
  // =========================================================
  // Revoca la URL temporal del Blob para evitar conservar el
  // material visual del enrolamiento más tiempo del necesario.
  const limpiarQrMfa = () => {
    setMfaQrUrl((urlActual) => {
      if (urlActual) {
        URL.revokeObjectURL(urlActual)
      }
      return ''
    })
  }

  const limpiarQrMfaObligatorio = () => {
    setMfaObligatorioQrUrl((urlActual) => {
      if (urlActual) {
        URL.revokeObjectURL(urlActual)
      }
      return ''
    })
  }

  // =========================================================
  // FETCH CENTRALIZADO
  // =========================================================
  const apiFetch = async (ruta, opciones = {}, accessToken = token) => {
    const headers = {
      ...(opciones.body ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...opciones.headers,
    }

    const respuesta = await fetch(`${API_URL}${ruta}`, {
      ...opciones,
      headers,
    })

    let datos = {}
    try {
      datos = await respuesta.json()
    } catch {
      datos = {}
    }

    if (!respuesta.ok) {
      const mensaje = textoError(
        datos,
        `La operación no pudo completarse (${respuesta.status}).`
      )

      if (respuesta.status === 401 && accessToken) {
        limpiarSesionLocal(mensaje)
      }

      throw new Error(mensaje)
    }

    return datos
  }

  // =========================================================
  // CARGA DE CONTEXTO
  // =========================================================
  const cargarContexto = async (accessToken = token) => {
    // =========================================================
    // CARGAR CONTEXTO SEGURO DEL USUARIO
    // =========================================================
    // /auth/me debe consultarse primero porque determina si la
    // sesión se encuentra restringida por cambio obligatorio
    // de contraseña.
    //
    // SEGURIDAD:
    // - El backend continúa siendo la fuente de verdad.
    // - React no decide si el usuario puede omitir el cambio.
    // - No se consultan recursos funcionales mientras la
    //   contraseña temporal siga activa.
    // =========================================================

    const datosUsuario = await apiFetch('/auth/me', {}, accessToken)

    // Guardamos inmediatamente el contexto del usuario.
    // Esto permite que la condición de renderizado de cambio
    // obligatorio pueda activarse sin depender de /companias.
    setUsuario(datosUsuario)

    // Si /auth/me expone el estado seguro del segundo factor,
    // sincronizamos la interfaz con la fuente de verdad del backend.
    if (typeof datosUsuario?.mfa_activo === 'boolean') {
      setMfaActivo(datosUsuario.mfa_activo)
    }

    // =========================================================
    // SESIÓN RESTRINGIDA POR CONTRASEÑA TEMPORAL
    // =========================================================
    // Cuando requiere_cambio_password = true, el usuario ya está
    // autenticado pero todavía no debe acceder a las funciones
    // normales del portal.
    //
    // En este estado NO consultamos:
    // - /companias
    // - /usuarios
    // - asignaciones
    // - sesiones administrativas
    //
    // La interfaz mostrará exclusivamente el formulario de cambio
    // obligatorio de contraseña y el backend seguirá bloqueando
    // cualquier endpoint funcional no autorizado para este estado.
    // =========================================================

    if (datosUsuario?.requiere_cambio_password === true) {
      setCompanias([])
      return datosUsuario
    }

    // =========================================================
    // CONTEXTO FUNCIONAL NORMAL
    // =========================================================
    // Solo se carga después de que el usuario ya posee una
    // contraseña definitiva.
    // =========================================================

    const rolesContexto = datosUsuario?.roles || []
    const esAdministradorContexto =
      rolesContexto.includes('ADMIN_TI') ||
      rolesContexto.includes('ADMIN_SOPORTE')

    let companiasContexto = []

    // Los administradores consultan sus compañías autorizadas.
    // Los líderes NO consultan /companias; su compañía llega de
    // forma controlada mediante /auth/me.
    if (esAdministradorContexto) {
      const datosCompanias = await apiFetch('/companias', {}, accessToken)
      companiasContexto = datosCompanias.companias || []
    }

    setCompanias(companiasContexto)

    return datosUsuario
  }

  const cargarUsuarios = async () => {
    const datos = await apiFetch('/usuarios')
    setUsuariosAdministrables(datos.usuarios || [])
  }

  const cargarAsignaciones = async () => {
    if (!esAdminTI) {
      setAsignaciones([])
      return
    }
    const datos = await apiFetch('/companias/asignaciones')
    setAsignaciones(datos.asignaciones || [])
  }

  const cargarSesiones = async () => {
    const datos = await apiFetch('/auth/sesiones')
    setSesiones(datos.sesiones || [])
  }

  // =========================================================
  // RESTAURAR SESIÓN
  // =========================================================
  useEffect(() => {
    const restaurar = async () => {
      if (!token) {
        setVerificandoSesion(false)
        return
      }

      try {
        await cargarContexto(token)
      } catch {
        sessionStorage.removeItem('iam_access_token')
        setToken('')
        setUsuario(null)
        setCompanias([])
        setError('La sesión expiró. Inicie sesión nuevamente.')
      } finally {
        setVerificandoSesion(false)
      }
    }

    restaurar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // =========================================================
  // LOGIN / LOGOUT
  // =========================================================
  const iniciarSesion = async (event) => {
    event.preventDefault()
    setCargando(true)
    setError('')
    setErrorVista('')
    setMensajeVista('')

    // Un nuevo intento invalida cualquier desafío que hubiera quedado
    // solamente en memoria de un intento anterior.
    setMfaLoginPendiente(false)
    setMfaLoginDesafio('')
    setMfaLoginCodigo('')
    setMfaObligatorioPendiente(false)
    setMfaObligatorioDesafio('')
    setMfaObligatorioCodigo('')
    limpiarQrMfaObligatorio()

    try {
      const datos = await apiFetch(
        '/auth/login',
        {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        },
        ''
      )

      // =====================================================
      // LOGIN CON MFA ACTIVO
      // =====================================================
      // Después de validar correo + contraseña, el backend NO
      // entrega access_token cuando la cuenta tiene MFA activo.
      // Entrega únicamente un desafío temporal de un solo uso.
      //
      // SEGURIDAD:
      // - no almacenamos el desafío en Web Storage;
      // - no llamamos /auth/me todavía;
      // - no creamos una sesión local;
      // - eliminamos la contraseña de React inmediatamente.
      // =====================================================
      if (datos?.mfa_requerido === true) {
        if (
          typeof datos?.desafio_mfa !== 'string' ||
          datos.desafio_mfa.length < 20
        ) {
          throw new Error(
            'El servidor solicitó MFA, pero no entregó un desafío válido.'
          )
        }

        // La contraseña ya fue validada por el backend. Se elimina
        // inmediatamente del estado de React y nunca se conserva para
        // completar el segundo factor o el enrolamiento.
        setPassword('')

        if (datos?.mfa_enrolamiento_requerido === true) {
          // Usuario sin MFA: no existe JWT ni sesión definitiva.
          // Conservamos únicamente el desafío opaco en memoria.
          setMfaLoginPendiente(false)
          setMfaLoginDesafio('')
          setMfaLoginCodigo('')
          setMfaObligatorioDesafio(datos.desafio_mfa)
          setMfaObligatorioCodigo('')
          setMfaObligatorioPendiente(true)
          return
        }

        // Usuario con MFA ya activo: solicitar código TOTP normal.
        setMfaObligatorioPendiente(false)
        setMfaObligatorioDesafio('')
        limpiarQrMfaObligatorio()
        setMfaLoginDesafio(datos.desafio_mfa)
        setMfaLoginCodigo('')
        setMfaLoginPendiente(true)
        return
      }

      // =====================================================
      // LOGIN SIN MFA
      // =====================================================
      // Mantiene compatibilidad con las cuentas que todavía no
      // tienen segundo factor activo.
      // =====================================================
      if (typeof datos?.access_token !== 'string' || !datos.access_token) {
        throw new Error('El servidor no entregó una sesión válida.')
      }

      sessionStorage.setItem('iam_access_token', datos.access_token)
      setToken(datos.access_token)
      await cargarContexto(datos.access_token)
      setPassword('')
      setVistaActual('panel')
    } catch (err) {
      setError(err.message)
    } finally {
      setCargando(false)
    }
  }

  // =========================================================
  // MFA / AUTHENTICATOR - VERIFICAR SEGUNDO FACTOR DEL LOGIN
  // =========================================================
  const verificarMfaLogin = async (event) => {
    event.preventDefault()

    const codigo = mfaLoginCodigo.trim()

    if (!/^\d{6}$/.test(codigo)) {
      setError('Ingrese un código Authenticator de 6 dígitos.')
      return
    }

    if (!mfaLoginDesafio) {
      setError(
        'El desafío MFA ya no está disponible. Inicie sesión nuevamente.'
      )
      setMfaLoginPendiente(false)
      setMfaLoginCodigo('')
      return
    }

    try {
      setMfaLoginProcesando(true)
      setError('')

      const datos = await apiFetch(
        '/auth/mfa/verificar-login',
        {
          method: 'POST',
          body: JSON.stringify({
            desafio: mfaLoginDesafio,
            codigo,
          }),
        },
        ''
      )

      if (typeof datos?.access_token !== 'string' || !datos.access_token) {
        throw new Error(
          'El segundo factor fue procesado, pero no se recibió una sesión válida.'
        )
      }

      // El desafío ya fue consumido por el backend. Lo eliminamos de
      // memoria antes de continuar con el contexto autenticado.
      setMfaLoginDesafio('')
      setMfaLoginCodigo('')
      setMfaLoginPendiente(false)

      sessionStorage.setItem('iam_access_token', datos.access_token)
      setToken(datos.access_token)

      // Haber completado este flujo confirma MFA para esta sesión.
      // Si /auth/me expone mfa_activo, cargarContexto lo sincronizará.
      setMfaActivo(true)

      await cargarContexto(datos.access_token)
      setVistaActual('panel')
} catch (err) {
  // =====================================================
  // CONTROL DEL LÍMITE DE INTENTOS MFA
  // =====================================================
  // Los intentos restantes son controlados exclusivamente
  // por el backend.
  //
  // Cuando se alcanza el máximo permitido, el backend
  // responde con HTTP 423 y consume el desafío MFA.
  //
  // En ese caso:
  // - eliminamos el desafío de la memoria de React;
  // - eliminamos cualquier código TOTP escrito;
  // - abandonamos la pantalla del segundo factor;
  // - limpiamos la contraseña;
  // - regresamos al formulario de inicio de sesión.
  //
  // No se almacena ni reutiliza ningún código MFA.
  // =====================================================

  const mensajeError = err?.message || 'No fue posible verificar el código.'

  if (
    mensajeError === 'Desafío MFA bloqueado por máximo de intentos'
  ) {
    setMfaLoginDesafio('')
    setMfaLoginCodigo('')
    setMfaLoginPendiente(false)
    setPassword('')

    setError(
      'Se alcanzó el número máximo de intentos de autenticación. Inicie sesión nuevamente.'
    )

    return
  }

  // Un código incorrecto que todavía no alcanzó el límite
  // conserva el desafío para permitir el siguiente intento.
  setMfaLoginCodigo('')
  setError(mensajeError)
} finally {

      setMfaLoginProcesando(false)
    }
  }

  const cancelarMfaLogin = () => {
    setMfaLoginPendiente(false)
    setMfaLoginDesafio('')
    setMfaLoginCodigo('')
    setMfaLoginProcesando(false)
    setPassword('')
    setError('')
  }


  // =========================================================
  // MFA OBLIGATORIO - ENROLAMIENTO PREVIO AL PRIMER ACCESO
  // =========================================================
  const iniciarMfaObligatorio = async () => {
    if (!mfaObligatorioDesafio) {
      setError('El desafío de enrolamiento expiró. Inicie sesión nuevamente.')
      setMfaObligatorioPendiente(false)
      return
    }

    try {
      setMfaObligatorioProcesando(true)
      setError('')

      // Este endpoint devuelve PNG. No se utiliza apiFetch porque
      // apiFetch interpreta las respuestas como JSON.
      const respuesta = await fetch(
        `${API_URL}/auth/mfa/enrolamiento-obligatorio`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
          body: JSON.stringify({ desafio: mfaObligatorioDesafio }),
        }
      )

      if (!respuesta.ok) {
        let datos = {}
        try {
          datos = await respuesta.json()
        } catch {
          datos = {}
        }
        throw new Error(
          textoError(
            datos,
            `No fue posible iniciar el enrolamiento MFA (${respuesta.status}).`
          )
        )
      }

      const blob = await respuesta.blob()
      if (!blob.type.startsWith('image/png') || blob.size === 0) {
        throw new Error('El servidor no devolvió un código QR válido.')
      }

      limpiarQrMfaObligatorio()
      setMfaObligatorioQrUrl(URL.createObjectURL(blob))
      setMfaObligatorioCodigo('')
    } catch (err) {
      setError(err?.message || 'No fue posible iniciar el enrolamiento MFA.')
    } finally {
      setMfaObligatorioProcesando(false)
    }
  }

  const activarMfaObligatorio = async (event) => {
    event.preventDefault()

    const codigo = mfaObligatorioCodigo.trim()
    if (!/^\d{6}$/.test(codigo)) {
      setError('Ingrese un código Authenticator de 6 dígitos.')
      return
    }

    if (!mfaObligatorioDesafio) {
      setError('El desafío de enrolamiento expiró. Inicie sesión nuevamente.')
      setMfaObligatorioPendiente(false)
      return
    }

    try {
      setMfaObligatorioProcesando(true)
      setError('')

      const datos = await apiFetch(
        '/auth/mfa/activar-obligatorio',
        {
          method: 'POST',
          body: JSON.stringify({
            desafio: mfaObligatorioDesafio,
            codigo,
          }),
        },
        ''
      )

      if (typeof datos?.access_token !== 'string' || !datos.access_token) {
        throw new Error(
          'MFA fue procesado, pero el servidor no entregó una sesión válida.'
        )
      }

      // El enrolamiento ya fue confirmado y el desafío fue consumido.
      limpiarQrMfaObligatorio()
      setMfaObligatorioDesafio('')
      setMfaObligatorioCodigo('')
      setMfaObligatorioPendiente(false)
      setMfaActivo(true)

      sessionStorage.setItem('iam_access_token', datos.access_token)
      setToken(datos.access_token)
      await cargarContexto(datos.access_token)
      setVistaActual('panel')
    } catch (err) {
      const mensajeError =
        err?.message || 'No fue posible confirmar el código Authenticator.'

      if (
        mensajeError === 'Desafío MFA bloqueado por máximo de intentos' ||
        mensajeError === 'Desafío MFA no válido o expirado'
      ) {
        limpiarQrMfaObligatorio()
        setMfaObligatorioDesafio('')
        setMfaObligatorioCodigo('')
        setMfaObligatorioPendiente(false)
        setPassword('')
        setError(
          mensajeError === 'Desafío MFA bloqueado por máximo de intentos'
            ? 'Se alcanzó el número máximo de intentos de autenticación. Inicie sesión nuevamente.'
            : 'El enrolamiento MFA expiró. Inicie sesión nuevamente.'
        )
        return
      }

      // Si el código fue incorrecto pero aún quedan intentos, conservamos
      // el desafío y el QR para que el usuario pueda volver a intentarlo.
      setMfaObligatorioCodigo('')
      setError(mensajeError)
    } finally {
      setMfaObligatorioProcesando(false)
    }
  }

  const cancelarMfaObligatorio = () => {
    limpiarQrMfaObligatorio()
    setMfaObligatorioPendiente(false)
    setMfaObligatorioDesafio('')
    setMfaObligatorioCodigo('')
    setMfaObligatorioProcesando(false)
    setPassword('')
    setError('')
  }

  const cerrarSesion = async () => {
    const sessionToken = token
    limpiarSesionLocal()
    setError('')
    try {
      if (sessionToken) {
        await fetch(API_URL + '/auth/logout', { method: 'POST',
          headers: { Authorization: 'Bearer ' + sessionToken },
          credentials: 'omit', redirect: 'error', signal: AbortSignal.timeout(5000) })
      }
    } catch {
      // El cierre local se realiza incluso si la sesión ya expiró.
    }
  }

  // =========================================================
  // EXPIRACIÓN LOCAL POR INACTIVIDAD
  // =========================================================
  // El backend continúa siendo la autoridad mediante
  // sesiones.ultima_actividad. Este temporizador mejora la UX:
  // si no existe interacción durante 5 minutos, la interfaz
  // cierra la sesión sin esperar a que el usuario haga otra
  // petición.
  //
  // No enviamos peticiones periódicas al backend porque eso
  // renovaría artificialmente ultima_actividad.
  // =========================================================
  useEffect(() => {
    if (!token || !usuario) return undefined

    let temporizador = null

    let ended = false
    const expirarSesionLocal = () => {
      if (ended) return
      ended = true
      limpiarSesionLocal(
        `La sesión expiró por ${SESSION_INACTIVITY_MINUTES} minutos de inactividad. ` +
        'Inicie sesión nuevamente.'
      )
      // La limpieza no depende de la red. Esta petición no actualiza el estado React.
      fetch(API_URL + '/auth/logout', { method: 'POST',
        headers: { Authorization: 'Bearer ' + token }, credentials: 'omit',
        redirect: 'error', signal: AbortSignal.timeout(5000) }).catch(() => {})
    }

    const comprobarVencimiento = () => {
      if (!ended && Date.now() >= idleDeadline.current) expirarSesionLocal()
    }

    const reiniciarTemporizador = () => {
      if (ended) return
      // Una interacción al volver de suspensión no debe revivir una sesión vencida.
      if (Date.now() >= idleDeadline.current) { expirarSesionLocal(); return }
      idleDeadline.current = Date.now() + SESSION_INACTIVITY_MS
      if (temporizador) window.clearTimeout(temporizador)
      temporizador = window.setTimeout(
        expirarSesionLocal,
        SESSION_INACTIVITY_MS
      )
    }

    const eventosActividad = [
      'mousedown',
      'keydown',
      'touchstart',
      'scroll',
      'iam-permissions-activity',
    ]

    eventosActividad.forEach((evento) =>
      window.addEventListener(evento, reiniciarTemporizador, { passive: true })
    )

    idleDeadline.current = Date.now() + SESSION_INACTIVITY_MS
    reiniciarTemporizador()
    window.addEventListener('focus', comprobarVencimiento)
    window.addEventListener('iam-session-check', comprobarVencimiento)
    document.addEventListener('visibilitychange', comprobarVencimiento)

    return () => {
      ended = true
      if (temporizador) window.clearTimeout(temporizador)
      window.removeEventListener('focus', comprobarVencimiento)
      window.removeEventListener('iam-session-check', comprobarVencimiento)
      document.removeEventListener('visibilitychange', comprobarVencimiento)
      eventosActividad.forEach((evento) =>
        window.removeEventListener(evento, reiniciarTemporizador)
      )
    }
    // El temporizador se reinicia al cambiar de identidad/sesión.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, usuario?.id])

  // =========================================================
  // NAVEGACIÓN SEGÚN ROL
  // =========================================================
  const abrirVista = async (vista) => {
    setVistaActual(vista)
    setMensajeVista('')
    setErrorVista('')

    try {
      setCargandoVista(true)

      if (vista === 'soporte') {
        await Promise.all([cargarUsuarios(), cargarContexto(), cargarAsignaciones()])
      }

      if (vista === 'identidades') {
        await cargarUsuarios()
      }

      if (vista === 'companias') {
        await cargarContexto()
      }

      if (vista === 'asignaciones') {
        await Promise.all([
          cargarUsuarios(),
          cargarContexto(),
          cargarAsignaciones(),
        ])
      }

      if (vista === 'sesiones') {
        await cargarSesiones()
      }
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // CAMBIAR MI CONTRASEÑA
  // =========================================================
  const cambiarMiPassword = async (event) => {
    event.preventDefault()
    setErrorVista('')
    setMensajeVista('')

    // =====================================================
    // VALIDACIÓN VISUAL PREVIA DE LA POLÍTICA
    // =====================================================
    // Evita enviar al backend una contraseña que claramente no
    // cumple la política. El backend conserva la validación
    // autoritativa y vuelve a comprobar estos requisitos.
    // =====================================================
    const passwordNuevaFormulario = cambioPassword.password_nuevo || ''

    const passwordFormularioCumplePolitica =
      passwordNuevaFormulario.length >= 12 &&
      /[0-9]/.test(passwordNuevaFormulario) &&
      /[A-Za-z]/.test(passwordNuevaFormulario) &&
      /[^A-Za-z0-9]/.test(passwordNuevaFormulario)

    if (!passwordFormularioCumplePolitica) {
      setErrorVista(
        'La contraseña no es segura. Asegúrate de cumplir con lo siguiente: ' +
        'Mínimo 12 caracteres. Al menos un número (0-9). ' +
        'Incluir al menos una letra (a, b, c...). ' +
        'Al menos un carácter especial (!, @, #, $, %, etc.).'
      )
      return
    }

    if (cambioPassword.password_nuevo !== cambioPassword.confirmar_password) {
      setErrorVista('La confirmación de la nueva contraseña no coincide.')
      return
    }

    try {
      setCargandoVista(true)
      // =====================================================
      // CONSTRUIR SOLICITUD SEGÚN EL TIPO DE CAMBIO
      // =====================================================
      // El cambio obligatorio ocurre después de que el backend
      // ya autenticó al usuario y creó una sesión restringida.
      // En ese caso no reenviamos la contraseña utilizada
      // durante el login.
      //
      // Para un cambio voluntario desde "Mi perfil" sí enviamos
      // la contraseña actual. El backend vuelve a comprobar el
      // estado real de requiere_cambio_password y conserva la
      // autoridad sobre qué modalidad está permitida.
      // =====================================================

      const cambioObligatorio =
        usuario?.requiere_cambio_password === true

      const cuerpoPassword = cambioObligatorio
        ? {
            password_nuevo: cambioPassword.password_nuevo,
          }
        : {
            password_actual: cambioPassword.password_actual,
            password_nuevo: cambioPassword.password_nuevo,
          }

      await apiFetch('/auth/password', {
        method: 'PUT',
        body: JSON.stringify(cuerpoPassword),
      })


      setCambioPassword({
        password_actual: '',
        password_nuevo: '',
        confirmar_password: '',
      })
// =====================================================
// ACTUALIZAR CONTEXTO DESPUÉS DEL CAMBIO DE CONTRASEÑA
// =====================================================
// El backend establece requiere_cambio_password = false.
// Consultamos nuevamente /auth/me para obtener el estado
// real de la credencial antes de habilitar el portal.
// =====================================================

const usuarioActualizado = await cargarContexto()

setMostrarCambioPassword(false)

if (usuarioActualizado?.requiere_cambio_password === false) {
  setMensajeVista('Contraseña actualizada correctamente.')
}
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ADMIN_TI: CREAR USUARIO ADMIN_SOPORTE
  // =========================================================
  // El ADMIN_SOPORTE se crea inicialmente SIN compañía.
  // ADMIN_TI delega después su alcance mediante la gestión de
  // asignaciones. Esto permite mantener compañías sin asignar
  // y administradores sin alcance cuando sea necesario.
  //
  // SEGURIDAD:
  // - no se solicita ni genera una contraseña en React;
  // - la contraseña temporal se genera exclusivamente en backend;
  // - la API no devuelve la contraseña ni el hash;
  // - el backend vuelve a validar rol y ausencia de compañía.
  // =========================================================
  const crearAdminSoporte = async (event) => {
    event.preventDefault()

    if (!esAdminTI) {
      setErrorVista(
        'Esta operación está disponible únicamente para ADMIN_TI.'
      )
      return
    }

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch('/usuarios/identidad', {
        method: 'POST',
        body: JSON.stringify({
          id_externo: nuevoAdminSoporte.id_externo.trim(),
          nombre: nuevoAdminSoporte.nombre.trim(),
          email: nuevoAdminSoporte.email.trim(),
          rol: 'ADMIN_SOPORTE',
          compania_id: null,
        }),
      })

      setNuevoAdminSoporte({
        id_externo: '',
        nombre: '',
        email: '',
        compania_id: '',
      })
      setMostrarNuevoAdminSoporte(false)

      await Promise.all([
        cargarUsuarios(),
        cargarAsignaciones(),
        cargarContexto(),
      ])

      setMensajeVista(
        'ADMIN_SOPORTE creado correctamente y sin compañía asignada. ' +
        'La contraseña temporal fue enviada al correo registrado.'
      )
    } catch (err) {
      setErrorVista(
        err?.message || 'No fue posible crear el usuario ADMIN_SOPORTE.'
      )
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ADMIN_TI: ESTADO Y RECUPERACIÓN DE ADMIN_SOPORTE
  // =========================================================
  const cambiarEstadoUsuario = async (usuarioObjetivo) => {
    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/usuarios/${usuarioObjetivo.id}/estado`, {
        method: 'PATCH',
        body: JSON.stringify({ activo: !usuarioObjetivo.activo }),
      })

      await cargarUsuarios()
      setMensajeVista(
        usuarioObjetivo.activo
          ? 'Usuario deshabilitado correctamente.'
          : 'Usuario habilitado correctamente.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ABRIR MODAL: RESTABLECER ACCESO
  // =========================================================
  // Esta función únicamente selecciona la identidad.
  // No genera, recibe ni almacena ninguna contraseña.
  // =========================================================

  const restablecerAcceso = (usuarioObjetivo) => {
    setErrorVista('')
    setMensajeVista('')

    setUsuarioRestablecer(usuarioObjetivo)
    setMostrarRestablecerAcceso(true)
  }

  // =========================================================
  // CERRAR MODAL: RESTABLECER ACCESO
  // =========================================================

  const cerrarRestablecerAcceso = () => {
    if (restableciendoAcceso) return

    setMostrarRestablecerAcceso(false)
    setUsuarioRestablecer(null)
  }

  // =========================================================
  // CONFIRMAR RESTABLECIMIENTO DE ACCESO
  // =========================================================
  // SEGURIDAD:
  // - El frontend no genera la contraseña temporal.
  // - El administrador no introduce ninguna contraseña.
  // - No se envía ninguna contraseña en el body.
  // - El backend genera la credencial temporal.
  // - El backend almacena únicamente el hash Argon2.
  // - La contraseña temporal se envía al correo registrado.
  // - La autorización ADMIN_TI / ADMIN_SOPORTE y el alcance
  //   por compañía vuelven a validarse en el backend.
  // =========================================================

  const confirmarRestablecerAcceso = async () => {
    if (!usuarioRestablecer?.id) {
      setErrorVista(
        'No se seleccionó una identidad válida.'
      )
      return
    }

    try {
      setRestableciendoAcceso(true)
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(
        `/auth/credenciales/${usuarioRestablecer.id}/reset-password`,
        {
          method: 'PUT',
        }
      )

      // Cerramos y limpiamos inmediatamente la identidad
      // seleccionada. Ninguna credencial queda en React.
      setMostrarRestablecerAcceso(false)
      setUsuarioRestablecer(null)

      setMensajeVista(
        'Acceso restablecido correctamente. ' +
        'La contraseña temporal fue enviada al correo ' +
        'registrado y las sesiones anteriores fueron revocadas.'
      )

      // Refresca la información administrativa después
      // del restablecimiento.
      await cargarUsuarios()

    } catch (err) {
      setErrorVista(err.message)

    } finally {
      setRestableciendoAcceso(false)
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ADMINISTRACIÓN: RESTABLECER MFA DE UN USUARIO AUTORIZADO
  // =========================================================
  // El frontend solo solicita la operación administrativa.
  // La autorización real, el alcance multitenant, la revocación
  // de sesiones/desafíos y la eliminación del vínculo TOTP se
  // validan y ejecutan en el backend.
  //
  // IMPORTANTE:
  // - No se genera ni se muestra un QR al administrador.
  // - No se reciben ni almacenan secretos/códigos TOTP.
  // - El usuario vinculará un QR nuevo en su próximo login.
  // =========================================================
  const abrirRestablecerMfa = (usuarioObjetivo) => {
    if (!esAdminTI && !esAdminSoporte) {
      setErrorVista('No tiene permisos para restablecer MFA.')
      return
    }

    setErrorVista('')
    setMensajeVista('')
    setUsuarioRestablecerMfa(usuarioObjetivo)
    setMostrarRestablecerMfa(true)
  }

  const cerrarRestablecerMfa = () => {
    if (restableciendoMfa) return

    setMostrarRestablecerMfa(false)
    setUsuarioRestablecerMfa(null)
  }

  const confirmarRestablecerMfa = async () => {
    if (!esAdminTI && !esAdminSoporte) {
      setErrorVista('No tiene permisos para restablecer MFA.')
      return
    }

    if (!usuarioRestablecerMfa?.id) {
      setErrorVista('No se seleccionó una identidad válida.')
      return
    }

    try {
      setRestableciendoMfa(true)
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      const datos = await apiFetch(
        `/auth/usuarios/${usuarioRestablecerMfa.id}/mfa/restablecer`,
        { method: 'POST' }
      )

      setMostrarRestablecerMfa(false)
      setUsuarioRestablecerMfa(null)

      await cargarUsuarios()

      setMensajeVista(
        datos?.mensaje ||
          'MFA restablecido correctamente. El usuario deberá vincular Authenticator en su próximo inicio de sesión.'
      )
    } catch (err) {
      // El modal permanece abierto para que el administrador vea
      // el error sin perder el contexto de la identidad seleccionada.
      setErrorVista(err?.message || 'No fue posible restablecer MFA.')
    } finally {
      setRestableciendoMfa(false)
      setCargandoVista(false)
    }
  }


  // =========================================================
  // ADMIN_TI: COMPAÑÍAS
  // =========================================================
  const crearCompania = async (event) => {
    event.preventDefault()

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch('/companias', {
        method: 'POST',
        body: JSON.stringify({
          codigo: nuevaCompania.codigo.trim(),
          nombre: nuevaCompania.nombre.trim(),
          descripcion: nuevaCompania.descripcion.trim() || null,
        }),
      })

      setNuevaCompania({ codigo: '', nombre: '', descripcion: '' })
      setMostrarNuevaCompania(false)
      await cargarContexto()
      setMensajeVista('Compañía creada correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  const abrirEditarCompania = (compania) => {
    if (!esAdminTI) return

    setErrorVista('')
    setMensajeVista('')
    setCompaniaEditar(compania)
    setEdicionCompania({
      codigo: compania.codigo || '',
      nombre: compania.nombre || '',
      descripcion: compania.descripcion || '',
    })
    setMostrarEditarCompania(true)
  }

  const guardarEdicionCompania = async (event) => {
    event.preventDefault()
    if (!companiaEditar || !esAdminTI) return

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/companias/${companiaEditar.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          codigo: edicionCompania.codigo.trim(),
          nombre: edicionCompania.nombre.trim(),
          descripcion: edicionCompania.descripcion.trim() || null,
        }),
      })

      setMostrarEditarCompania(false)
      setCompaniaEditar(null)
      setEdicionCompania({ codigo: '', nombre: '', descripcion: '' })

      await Promise.all([cargarContexto(), cargarAsignaciones()])
      setMensajeVista('Datos de la compañía actualizados correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  const cambiarEstadoCompania = async (compania) => {
    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/companias/${compania.id}/estado`, {
        method: 'PATCH',
        body: JSON.stringify({ activo: !compania.activo }),
      })

      await cargarContexto()
      if (esAdminTI) await cargarAsignaciones()
      setMensajeVista(
        compania.activo
          ? 'Compañía deshabilitada correctamente.'
          : 'Compañía habilitada correctamente.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // EDICIÓN DE USUARIOS ADMINISTRABLES
  // =========================================================
  // ADMIN_TI puede editar ADMIN_SOPORTE.
  // ADMIN_SOPORTE puede editar líderes de su alcance.
  // El backend aplica nuevamente RBAC y multitenancy.
  const abrirEditarUsuario = (usuarioObjetivo) => {
    setErrorVista('')
    setMensajeVista('')
    setUsuarioEditar(usuarioObjetivo)
    setEdicionUsuario({
      id_externo: usuarioObjetivo.id_externo || '',
      nombre: usuarioObjetivo.nombre || '',
      email: usuarioObjetivo.email || '',
    })
    setMostrarEditarUsuario(true)
  }

  const guardarEdicionUsuario = async (event) => {
    event.preventDefault()
    if (!usuarioEditar) return

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/usuarios/${usuarioEditar.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          id_externo: edicionUsuario.id_externo.trim(),
          nombre: edicionUsuario.nombre.trim(),
          email: edicionUsuario.email.trim(),
        }),
      })

      setMostrarEditarUsuario(false)
      setUsuarioEditar(null)
      setEdicionUsuario({ id_externo: '', nombre: '', email: '' })

      await cargarUsuarios()
      if (esAdminTI) await cargarAsignaciones()

      setMensajeVista(
        'Datos del usuario actualizados correctamente. ' +
        'Sus sesiones activas fueron revocadas por seguridad.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ADMIN_TI: ASIGNACIONES CONSOLIDADAS
  // =========================================================
  const abrirAsignacionUsuario = (admin) => {
    const actuales = asignaciones
      .filter((item) => Number(item.usuario_id) === Number(admin.id))
      .map((item) => Number(item.compania_id))

    setAdminAsignacion(admin)
    setCompaniasSeleccionadas(actuales)
    setMostrarAsignacion(true)
  }

  const alternarCompaniaSeleccionada = (companiaId) => {
    const id = Number(companiaId)
    setCompaniasSeleccionadas((prev) =>
      prev.includes(id)
        ? prev.filter((item) => item !== id)
        : [...prev, id]
    )
  }

  const guardarAsignacionesUsuario = async (event) => {
    event.preventDefault()
    if (!adminAsignacion) return

    const actuales = asignaciones
      .filter((item) => Number(item.usuario_id) === Number(adminAsignacion.id))
      .map((item) => Number(item.compania_id))

    const deseadas = companiasSeleccionadas.map(Number)
    const agregar = deseadas.filter((id) => !actuales.includes(id))
    const retirar = actuales.filter((id) => !deseadas.includes(id))

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      // Se sincroniza el alcance usando exclusivamente los endpoints RBAC
      // del backend. Primero retiramos relaciones que ya no se desean y
      // después agregamos las nuevas. Un conjunto vacío es válido.
      for (const companiaId of retirar) {
        await apiFetch(
          `/companias/asignaciones/${adminAsignacion.id}/${companiaId}`,
          { method: 'DELETE' }
        )
      }

      for (const companiaId of agregar) {
        await apiFetch('/companias/asignaciones', {
          method: 'POST',
          body: JSON.stringify({
            usuario_id: Number(adminAsignacion.id),
            compania_id: companiaId,
          }),
        })
      }

      setMostrarAsignacion(false)
      setAdminAsignacion(null)
      setCompaniasSeleccionadas([])
      await Promise.all([cargarUsuarios(), cargarAsignaciones(), cargarContexto()])
      setMensajeVista('Asignaciones actualizadas correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  const eliminarAsignacion = async (asignacion) => {
    const confirmado = window.confirm(
      `¿Retirar ${asignacion.compania_nombre} del alcance de ${asignacion.usuario_nombre}?`
    )
    if (!confirmado) return

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')
      await apiFetch(
        `/companias/asignaciones/${asignacion.usuario_id}/${asignacion.compania_id}`,
        { method: 'DELETE' }
      )
      await Promise.all([cargarUsuarios(), cargarAsignaciones()])
      setMensajeVista('Compañía desasignada correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // ADMIN_SOPORTE: IDENTIDADES DE COMPAÑÍAS ASIGNADAS
  // =========================================================
  const crearIdentidad = async (event) => {
    event.preventDefault()

    if (!nuevaIdentidad.compania_id) {
      setErrorVista('Seleccione una compañía asignada.')
      return
    }

    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch('/usuarios/identidad', {
        method: 'POST',
        body: JSON.stringify({
          id_externo: nuevaIdentidad.id_externo.trim(),
          nombre: nuevaIdentidad.nombre.trim(),
          email: nuevaIdentidad.email.trim(),
          rol: nuevaIdentidad.rol,
          compania_id: Number(nuevaIdentidad.compania_id),
        }),
      })

      setNuevaIdentidad({
        id_externo: '',
        nombre: '',
        email: '',
        rol: 'LIDER_FACTURACION',
        compania_id: companias.length === 1 ? String(companias[0].id) : '',
      })
      setMostrarNuevaIdentidad(false)
      await cargarUsuarios()
      setMensajeVista(
        'Identidad creada. La contraseña temporal fue enviada al correo registrado.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  const cambiarRolIdentidad = async (identidad, nuevoRol) => {
    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/usuarios/${identidad.id}/rol`, {
        method: 'PATCH',
        body: JSON.stringify({ rol: nuevoRol }),
      })

      await cargarUsuarios()
      setMensajeVista('Rol actualizado correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // MFA / AUTHENTICATOR
  // =========================================================
  const iniciarEnrolamientoMfa = async () => {
    if (!token) {
      setErrorVista('La sesión no es válida. Inicie sesión nuevamente.')
      return
    }

    try {
      setMfaProcesando(true)
      setErrorVista('')
      setMensajeVista('')

      // El endpoint devuelve image/png, por lo que no utilizamos
      // apiFetch(), que está diseñado para respuestas JSON.
      const respuesta = await fetch(`${API_URL}/auth/mfa/enrolamiento`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: 'no-store',
      })

      if (!respuesta.ok) {
        let datos = {}
        try {
          datos = await respuesta.json()
        } catch {
          datos = {}
        }

        const mensaje = textoError(
          datos,
          `No fue posible iniciar el enrolamiento MFA (${respuesta.status}).`
        )

        if (respuesta.status === 401) {
          limpiarSesionLocal(mensaje)
        }

        throw new Error(mensaje)
      }

      const blob = await respuesta.blob()

      if (!blob.type.startsWith('image/png') || blob.size === 0) {
        throw new Error('El servidor no devolvió un QR PNG válido.')
      }

      // Liberamos cualquier QR anterior antes de crear uno nuevo.
      limpiarQrMfa()

      const nuevaUrl = URL.createObjectURL(blob)
      setMfaQrUrl(nuevaUrl)
      setMfaEnrolamientoIniciado(true)
      setMfaCodigo('')
      setMensajeVista(
        'Escanee el código QR con su aplicación Authenticator y luego ingrese el código de 6 dígitos.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setMfaProcesando(false)
    }
  }

  const activarMfa = async (event) => {
    event.preventDefault()

    const codigo = mfaCodigo.trim()

    if (!/^\d{6}$/.test(codigo)) {
      setErrorVista('Ingrese un código Authenticator de 6 dígitos.')
      return
    }

    try {
      setMfaProcesando(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch('/auth/mfa/activar', {
        method: 'POST',
        body: JSON.stringify({
          codigo,
        }),
      })

      setMfaActivo(true)
      setMfaEnrolamientoIniciado(false)
      setMfaCodigo('')
      limpiarQrMfa()

      setMensajeVista(
        'MFA fue activado correctamente. La aplicación Authenticator ya está vinculada a su cuenta.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setMfaProcesando(false)
    }
  }

  // Nunca dejamos una URL Blob del QR viva después de desmontar
  // el componente.
  useEffect(() => {
    return () => {
      if (mfaQrUrl) {
        URL.revokeObjectURL(mfaQrUrl)
      }
    }
  }, [mfaQrUrl])

  useEffect(() => {
    return () => {
      if (mfaObligatorioQrUrl) {
        URL.revokeObjectURL(mfaObligatorioQrUrl)
      }
    }
  }, [mfaObligatorioQrUrl])

  // =========================================================
  // SESIONES
  // =========================================================
  const revocarSesion = async (sesionId) => {
    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      await apiFetch(`/auth/sesiones/${sesionId}/revocar`, {
        method: 'POST',
      })

      await cargarSesiones()
      setMensajeVista('Sesión revocada correctamente.')
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  const limpiarSesionesExpiradas = async () => {
    try {
      setCargandoVista(true)
      setErrorVista('')
      setMensajeVista('')

      const datos = await apiFetch('/auth/sesiones/expiradas', {
        method: 'DELETE',
      })

      await cargarSesiones()
      setMensajeVista(
        datos.mensaje || 'Limpieza de sesiones expiradas completada.'
      )
    } catch (err) {
      setErrorVista(err.message)
    } finally {
      setCargandoVista(false)
    }
  }

  // =========================================================
  // DATOS DERIVADOS PARA ASIGNACIONES
  // =========================================================
  const asignacionesPorCompania = useMemo(() => {
    const mapa = new Map()
    asignaciones.forEach((item) => {
      const lista = mapa.get(item.compania_id) || []
      lista.push(item)
      mapa.set(item.compania_id, lista)
    })
    return mapa
  }, [asignaciones])

  const companiasActivas = companias.filter((compania) => compania.activo)

  // =========================================================
  // AVISO PREVENTIVO DE EXPIRACIÓN DE CONTRASEÑA
  // =========================================================
  // El cálculo autoritativo proviene de /auth/me. React solo
  // presenta el dato seguro calculado por el backend.
  // =========================================================
  const mostrarAvisoPassword =
    usuario?.mostrar_aviso_password === true &&
    usuario?.requiere_cambio_password === false

  const diasPassword = usuario?.dias_para_expirar_password

  const textoAvisoPassword =
    diasPassword === 1
      ? 'Su contraseña vence en 1 día. Recomendamos cambiarla antes de su vencimiento.'
      : `Su contraseña vence en ${diasPassword} días. Recomendamos cambiarla antes de su vencimiento.`

  // =========================================================
  // PANTALLA DE CARGA
  // =========================================================
  if (verificandoSesion) {
    return (
      <div className="app">
        <main className="login-page">
          <section className="login-panel">
            <div className="login-card">
              <span className="eyebrow">IAM SECURE PLATFORM</span>
              <h2>Validando sesión...</h2>
              <p>Comprobando el contexto de seguridad.</p>
            </div>
          </section>
        </main>
      </div>
    )
  }

    // =========================================================
  // MFA OBLIGATORIO - PANTALLA DE PRIMER ENROLAMIENTO
  // =========================================================
  // Tiene prioridad antes de cualquier portal. En este punto no
  // existe access_token: el usuario solo puede generar el QR y
  // confirmar el primer TOTP.
  if (mfaObligatorioPendiente && !token) {
    return (
      <div className="app">
        <main className="login-page">
          <section className="brand-panel">
            <div className="brand-content">
              <div className="logo-mark">IAM</div>
              <h1>IAM Secure</h1>
              <p className="brand-subtitle">
                Plataforma de Gestión de Identidades y Accesos
              </p>

              <div className="security-message">
                <span className="shield">✓</span>
                <div>
                  <strong>MFA obligatorio</strong>
                  <p>
                    Configure Authenticator antes de acceder por primera vez
                    a la plataforma.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="login-panel">
            <div className="login-card">
              <div className="login-heading">
                <span className="eyebrow">CONFIGURACIÓN DE SEGURIDAD</span>
                <h2>Vincular Authenticator</h2>
                <p>
                  Escanee el código QR con su aplicación Authenticator y
                  confirme el código de 6 dígitos.
                </p>
              </div>

              {!mfaObligatorioQrUrl ? (
                <>
                  {error && (
                    <div className="error-message" role="alert">
                      {error}
                    </div>
                  )}

                  <button
                    type="button"
                    className="login-button"
                    onClick={iniciarMfaObligatorio}
                    disabled={mfaObligatorioProcesando}
                  >
                    {mfaObligatorioProcesando
                      ? 'Generando código QR...'
                      : 'Configurar Authenticator'}
                  </button>

                  <button
                    type="button"
                    className="secondary-action-button"
                    onClick={cancelarMfaObligatorio}
                    disabled={mfaObligatorioProcesando}
                  >
                    Cancelar
                  </button>
                </>
              ) : (
                <form className="login-form" onSubmit={activarMfaObligatorio}>
                  <div className="mfa-required-qr-container">
                    <img
                      src={mfaObligatorioQrUrl}
                      alt="Código QR para vincular Authenticator"
                      className="mfa-required-qr-image"
                    />
                  </div>

                  <div className="login-security-note">
                    Escanee este QR desde Authenticator. Después ingrese el
                    código actual de 6 dígitos para finalizar la configuración.
                  </div>

                  <label htmlFor="mfa-obligatorio-codigo">
                    Código Authenticator
                  </label>
                  <input
                    id="mfa-obligatorio-codigo"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    pattern="[0-9]{6}"
                    value={mfaObligatorioCodigo}
                    onChange={(event) =>
                      setMfaObligatorioCodigo(
                        event.target.value.replace(/\D/g, '').slice(0, 6)
                      )
                    }
                    placeholder="000000"
                    autoFocus
                    required
                  />

                  {error && (
                    <div className="error-message" role="alert">
                      {error}
                    </div>
                  )}

                  <button
                    className="login-button"
                    type="submit"
                    disabled={
                      mfaObligatorioProcesando ||
                      mfaObligatorioCodigo.length !== 6
                    }
                  >
                    {mfaObligatorioProcesando
                      ? 'Verificando...'
                      : 'Activar MFA y continuar'}
                  </button>

                  <button
                    type="button"
                    className="secondary-action-button"
                    onClick={cancelarMfaObligatorio}
                    disabled={mfaObligatorioProcesando}
                  >
                    Cancelar
                  </button>
                </form>
              )}

              <p className="login-footer">
                IAM Secure no habilitará una sesión hasta completar
                correctamente este segundo factor.
              </p>
            </div>
          </section>
        </main>
      </div>
    )
  }

  // =========================================================
  // MFA / AUTHENTICATOR - PANTALLA DE SEGUNDO FACTOR
  // =========================================================
  // Tiene prioridad sobre el login normal mientras exista un
  // desafío pendiente. No existe access_token ni sesión local
  // definitiva hasta que el backend valide el código TOTP.
  // =========================================================
  if (mfaLoginPendiente && !token) {
    return (
      <div className="app">
        <main className="login-page">
          <section className="brand-panel">
            <div className="brand-content">
              <div className="logo-mark">IAM</div>
              <h1>IAM Secure</h1>
              <p className="brand-subtitle">
                Plataforma de Gestión de Identidades y Accesos
              </p>

              <div className="security-message">
                <span className="shield">✓</span>
                <div>
                  <strong>Verificación en dos pasos</strong>
                  <p>
                    Complete el segundo factor antes de acceder a la plataforma.
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="login-panel">
            <div className="login-card">
              <div className="login-heading">
                <span className="eyebrow">AUTENTICACIÓN MULTIFACTOR</span>
                <h2>Verificar Authenticator</h2>
                <p>
                  Ingrese el código de 6 dígitos generado por su aplicación
                  Authenticator.
                </p>
              </div>

              <form className="login-form" onSubmit={verificarMfaLogin}>
                <label htmlFor="mfa-login-codigo">
                  Código Authenticator
                </label>
                <input
                  id="mfa-login-codigo"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  pattern="[0-9]{6}"
                  value={mfaLoginCodigo}
                  onChange={(event) =>
                    setMfaLoginCodigo(
                      event.target.value.replace(/\D/g, '').slice(0, 6)
                    )
                  }
                  placeholder="000000"
                  autoFocus
                  required
                />

                {error && (
                  <div className="error-message" role="alert">
                    {error}
                  </div>
                )}

                <button
                  className="login-button"
                  type="submit"
                  disabled={
                    mfaLoginProcesando || mfaLoginCodigo.length !== 6
                  }
                >
                  {mfaLoginProcesando
                    ? 'Verificando...'
                    : 'Verificar y continuar'}
                </button>

                <button
                  type="button"
                  className="secondary-action-button"
                  onClick={cancelarMfaLogin}
                  disabled={mfaLoginProcesando}
                >
                  Cancelar
                </button>
              </form>

              <p className="login-footer">
                El acceso se habilita únicamente después de validar ambos
                factores.
              </p>
            </div>
          </section>
        </main>
      </div>
    )
  }

  // =========================================================
  // CAMBIO OBLIGATORIO DE CONTRASEÑA
  // =========================================================
  // Esta pantalla tiene prioridad sobre cualquier portal
  // autenticado de IAM Secure.
  //
  // Se muestra cuando /auth/me informa:
  //
  //     requiere_cambio_password === true
  //
  // Esto ocurre, por ejemplo, después de que un administrador
  // restablece el acceso y el usuario inicia sesión utilizando
  // una contraseña temporal.
  //
  // SEGURIDAD:
  // - No se permite acceder al portal mientras la credencial
  //   temporal continúe activa.
  // - No se almacena ninguna contraseña adicionalmente.
  // - La contraseña utilizada durante el login no se conserva
  //   ni se vuelve a solicitar en esta pantalla obligatoria.
  // - El cambio se procesa mediante PUT /auth/password.
  // - Después del cambio se consulta nuevamente /auth/me.
  // - El backend continúa siendo la fuente de verdad.
  // - El usuario conserva la opción de cerrar su sesión.
  //
  // IMPORTANTE:
  // Esta condición debe permanecer ANTES de los portales de
  // líderes y administradores para impedir que el flujo pueda
  // omitirse desde la interfaz.
  // =========================================================

  // =========================================================
  // INDICADOR VISUAL DE SEGURIDAD DE CONTRASEÑA
  // =========================================================
  // Control visual; el backend continúa siendo la autoridad.
  // Debe coincidir con validar_password_seguro():
  // 12 caracteres + número + letra + carácter especial.
  // =========================================================
  const passwordNueva = cambioPassword.password_nuevo || ''

  const passwordCumplePolitica =
    passwordNueva.length >= 12 &&
    /[0-9]/.test(passwordNueva) &&
    /[A-Za-z]/.test(passwordNueva) &&
    /[^A-Za-z0-9]/.test(passwordNueva)

  if (
    token &&
    usuario &&
    usuario.requiere_cambio_password === true
  ) {
    return (
      <div className="app">
        <main className="login-page">
          <section className="login-panel">
            <div className="login-card">

              <span className="eyebrow">
                IAM SECURE PLATFORM
              </span>

              <h2>
                Cambio de contraseña obligatorio
              </h2>

              <p>
                Su credencial requiere una actualización de seguridad.
                Debe establecer una nueva contraseña antes de acceder
                a las funciones de la plataforma.
              </p>

              {/* Requisitos visibles para que el usuario conozca la política
                  antes de comenzar a escribir la nueva contraseña. */}
              <div className="login-security-note">
                <strong>Requisitos para la nueva contraseña:</strong>{' '}
                mínimo 12 caracteres, al menos un número (0-9), al menos una
                letra (a, b, c...) y al menos un carácter especial
                (!, @, #, $, %, etc.).
              </div>

              {errorVista && (
                <div className="error-message">
                  {errorVista}
                </div>
              )}

              {mensajeVista && (
                <div className="success-message">
                  {mensajeVista}
                </div>
              )}

              <form
                className="login-form"
                onSubmit={cambiarMiPassword}
              >


                <label>
                  Nueva contraseña

                  <div className="password-security-field">
                    <input
                      type="password"
                      value={cambioPassword.password_nuevo}
                      onChange={(event) =>
                        setCambioPassword({
                          ...cambioPassword,
                          password_nuevo: event.target.value,
                        })
                      }
                      autoComplete="new-password"
                      required
                    />

                    {/* El indicador permanece oculto mientras el campo esté vacío.
                        Se muestra únicamente cuando el usuario comienza a escribir. */}
                    {passwordNueva.length > 0 && (
                      <div
                        className={
                          passwordCumplePolitica
                            ? 'password-security-status password-security-status--safe'
                            : 'password-security-status password-security-status--unsafe'
                        }
                        role="status"
                        aria-live="polite"
                      >
                        <span
                          className="password-security-light"
                          aria-hidden="true"
                        />
                        <span>
                          {passwordCumplePolitica
                            ? 'Contraseña Segura'
                            : 'Contraseña Insegura'}
                        </span>
                      </div>
                    )}
                  </div>
                </label>

                <label>
                  Confirmar nueva contraseña
                  <input
                    type="password"
                    value={cambioPassword.confirmar_password}
                    onChange={(event) =>
                      setCambioPassword({
                        ...cambioPassword,
                        confirmar_password: event.target.value,
                      })
                    }
                    autoComplete="new-password"
                    required
                  />
                </label>

                <button
                  type="submit"
                  className="login-button"
                  disabled={cargandoVista}
                >
                  {cargandoVista
                    ? 'Actualizando contraseña...'
                    : 'Establecer nueva contraseña'}
                </button>

                <button
                  type="button"
                  className="secondary-action-button"
                  onClick={cerrarSesion}
                  disabled={cargandoVista}
                >
                  Cerrar sesión
                </button>
              </form>



            </div>
          </section>
        </main>
      </div>
    )
  }

  // =========================================================
  // PORTAL ORGANIZACIONAL PARA LÍDERES
  // =========================================================
  // Los elementos del área son únicamente ambientación visual.
  // Las funciones reales disponibles para el líder son:
  // - cambio de su propia contraseña;
  // - cierre de su propia sesión.
  //
  // La compañía proviene de /auth/me y no de /companias.
  // =========================================================
  if (token && usuario && esLider) {
    const compania = usuario.compania
    const codigoCompania = (compania?.codigo || 'SIN-COMPANIA').toUpperCase()

    const configuracionRol = {
      LIDER_FACTURACION: {
        area: 'Facturación',
        icono: '▤',
        descripcion: 'Entorno de seguimiento y gestión financiera.',
        accesorios: [
          ['Facturas pendientes por aprobación', 'Documentos en proceso de revisión', '▤'],
          ['Facturas pendientes por pagar', 'Compromisos de pago del período', '$'],
          ['Declaración de impuestos', 'Calendario y obligaciones tributarias', '%'],
        ],
      },
      LIDER_LOGISTICA: {
        area: 'Logística',
        icono: '▣',
        descripcion: 'Entorno de coordinación logística y operaciones.',
        accesorios: [
          ['Despachos', 'Seguimiento visual de despachos pendientes', '→'],
          ['Entregas', 'Programación visual de entregas', '✓'],
          ['Inventario y movimientos', 'Referencia visual de existencias y movimientos', '▦'],
        ],
      },
      LIDER_GESTION_HUMANA: {
        area: 'Gestión Humana',
        icono: '◉',
        descripcion: 'Entorno de acompañamiento y gestión del talento.',
        accesorios: [
          ['Colaboradores', 'Referencia visual del equipo de trabajo', '◎'],
          ['Novedades de personal', 'Ambientación de novedades organizacionales', '◇'],
          ['Vacaciones y permisos', 'Referencia visual de solicitudes del personal', '□'],
        ],
      },
    }

    const configuracion = configuracionRol[rolLider]

    return (
      <div className={`leader-portal company-${codigoCompania.toLowerCase()}`}>
        <header className="leader-topbar">
          <div className="leader-brand">
            <div className="logo-mark">IAM</div>
            <div>
              <strong>IAM Secure</strong>
              <span>Acceso organizacional seguro</span>
            </div>
          </div>

          <button
            type="button"
            className="leader-logout"
            onClick={cerrarSesion}
          >
            Cerrar sesión
          </button>
        </header>

        <main className="leader-main">
          <section className="leader-hero">
            <div>
              <span className="leader-company-tag">{codigoCompania}</span>
              <p className="leader-welcome">Bienvenido, {usuario.nombre}</p>
              <h1>
                Plataforma de {configuracion.area}{' '}
                <span>{codigoCompania}</span>
              </h1>
              <p>{configuracion.descripcion}</p>
            </div>

            <div className="leader-area-icon" aria-hidden="true">
              {configuracion.icono}
            </div>
          </section>

          {mostrarAvisoPassword && (
            <section className="identity-message-card password-warning" role="status">
              <span className="eyebrow">SEGURIDAD DE LA CONTRASEÑA</span>
              <p>{textoAvisoPassword}</p>
              <button
                type="button"
                className="primary-action-button"
                onClick={() => setMostrarCambioPassword(true)}
              >
                Cambiar contraseña ahora
              </button>
            </section>
          )}

          <section className="leader-profile-grid">
            <article className="leader-profile-card">
              <span>Usuario</span>
              <strong>{usuario.nombre}</strong>
              <small>{usuario.id_externo || `ID #${usuario.id}`}</small>
            </article>

            <article className="leader-profile-card">
              <span>Cargo / Rol</span>
              <strong>{rolLider.replaceAll('_', ' ')}</strong>
              <small>Acceso organizacional</small>
            </article>

            <article className="leader-profile-card">
              <span>Compañía</span>
              <strong>{compania?.nombre || 'Sin compañía asociada'}</strong>
              <small>{compania?.codigo || 'Contexto no disponible'}</small>
            </article>

            <article className="leader-profile-card">
              <span>Estado</span>
              <strong>{usuario.activo ? 'Activo' : 'Inactivo'}</strong>
              <small>Estado de la identidad</small>
            </article>
          </section>

          <section className="leader-section">
            <div className="leader-section-heading">
              <div>
                <span className="eyebrow">ÁREA DE {configuracion.area.toUpperCase()}</span>
                <h2>Panel de referencia</h2>
                <p>
                  Estos elementos ambientan la plataforma del área y no ejecutan
                  procesos de negocio.
                </p>
              </div>
            </div>

            <PermissionCards token={token} onExpired={limpiarSesionLocal} />
          </section>

          <section className="leader-account-card">
            <div>
              <span className="eyebrow">SEGURIDAD DE LA CUENTA</span>
              <h2>Mi cuenta</h2>
              <p>
                Gestione su contraseña y configure un segundo factor de
                autenticación para reforzar la seguridad de su cuenta.
              </p>
            </div>

            <button
              type="button"
              className="primary-action-button"
              onClick={() => setMostrarCambioPassword(true)}
            >
              Cambiar mi contraseña
            </button>
          </section>

          {/* =====================================================
              MFA / AUTHENTICATOR PARA PORTAL DE LÍDER
              =====================================================
              SEGURIDAD:
              - Reutiliza el mismo flujo MFA del perfil administrativo.
              - El secreto TOTP no se muestra ni se almacena en el frontend.
              - El backend entrega únicamente el QR PNG de enrolamiento.
              - La Blob URL del QR se mantiene temporalmente en memoria.
              ===================================================== */}
          <section className="leader-account-card">
            <div className="mfa-account-content">
              <div
                className="mfa-account-heading"
              >
                <div>
                  <span className="eyebrow">AUTENTICACIÓN MULTIFACTOR</span>
                  <h2>Authenticator</h2>
                  <p>
                    Proteja su cuenta con un segundo factor basado en TOTP.
                  </p>
                </div>

                <div
                  className="mfa-account-actions"
                >
                  <span
                    className={mfaActivo ? 'mfa-status mfa-status--active' : 'mfa-status mfa-status--inactive'}
                  >
                    {mfaActivo ? 'MFA activo' : 'MFA no activado'}
                  </span>

                  {!mfaActivo && !mfaEnrolamientoIniciado && (
                    <button
                      type="button"
                      className="primary-action-button"
                      onClick={iniciarEnrolamientoMfa}
                      disabled={mfaProcesando}
                    >
                      {mfaProcesando
                        ? 'Preparando...'
                        : 'Configurar Authenticator'}
                    </button>
                  )}
                </div>
              </div>

              {mfaEnrolamientoIniciado && !mfaActivo && (
                <div
                  className="mfa-enrollment-grid mfa-enrollment-grid--leader"
                >
                  <div
                    className="mfa-enrollment-qr-container"
                  >
                    {mfaQrUrl && (
                      <img
                        src={mfaQrUrl}
                        alt="Código QR para configurar Authenticator"
                        width="256"
                        height="256"
                        className="mfa-enrollment-qr-image"
                      />
                    )}
                  </div>

                  <div>
                    <h3>Configure su Authenticator</h3>
                    <ol className="mfa-enrollment-instructions">
                      <li>
                        Abra Microsoft Authenticator, Google Authenticator u
                        otra aplicación compatible con TOTP.
                      </li>
                      <li>Escanee el código QR mostrado.</li>
                      <li>
                        Introduzca el código temporal de 6 dígitos para
                        confirmar el enrolamiento.
                      </li>
                    </ol>

                    <form
                      onSubmit={activarMfa}
                      className="mfa-enrollment-form"
                    >
                      <div className="form-field">
                        <label htmlFor="lider-mfa-codigo">
                          Código Authenticator
                        </label>
                        <input
                          id="lider-mfa-codigo"
                          type="text"
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          maxLength={6}
                          pattern="[0-9]{6}"
                          value={mfaCodigo}
                          onChange={(event) =>
                            setMfaCodigo(
                              event.target.value.replace(/\D/g, '').slice(0, 6)
                            )
                          }
                          placeholder="123456"
                          required
                        />
                      </div>

                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={mfaProcesando || mfaCodigo.length !== 6}
                      >
                        {mfaProcesando ? 'Validando...' : 'Activar MFA'}
                      </button>

                      <button
                        type="button"
                        className="secondary-action-button"
                        disabled={mfaProcesando}
                        onClick={() => {
                          limpiarQrMfa()
                          setMfaEnrolamientoIniciado(false)
                          setMfaCodigo('')
                          setMensajeVista('')
                          setErrorVista('')
                        }}
                      >
                        Cancelar
                      </button>
                    </form>
                  </div>
                </div>
              )}
            </div>
          </section>

          {mensajeVista && (
            <section className="identity-message-card">
              <span className="eyebrow">OPERACIÓN COMPLETADA</span>
              <p>{mensajeVista}</p>
            </section>
          )}

          {errorVista && (
            <section className="identity-message-card error">
              <span className="eyebrow">ERROR</span>
              <p>{errorVista}</p>
            </section>
          )}

          {mostrarCambioPassword && (
            <div className="modal-overlay" role="presentation">
              <section
                className="identity-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="lider-cambio-password-titulo"
              >
                <div className="identity-modal-header">
                  <div>
                    <span className="eyebrow">SEGURIDAD DE LA CUENTA</span>
                    <h2 id="lider-cambio-password-titulo">
                      Cambiar mi contraseña
                    </h2>
                  </div>
                  <button
                    type="button"
                    className="modal-close-button"
                    onClick={() => {
                      setMostrarCambioPassword(false)
                      setErrorVista('')
                      setMensajeVista('')
                      setCambioPassword({
                        password_actual: '',
                        password_nuevo: '',
                        confirmar_password: '',
                      })
                    }}
                  >
                    ×
                  </button>
                </div>

                {/* Los errores del cambio voluntario se muestran dentro del modal.
                    Así el usuario recibe la retroalimentación sin tener que cerrarlo. */}
                {errorVista && (
                  <div className="error-message" role="alert">
                    {errorVista}
                  </div>
                )}

                <form className="identity-form" onSubmit={cambiarMiPassword}>
                  <div className="identity-form-grid">
                    {/* En el cambio voluntario se conserva la contraseña actual.
                        El backend debe verificarla antes de autorizar el cambio. */}
                    <div className="form-field form-field-full">
                      <label htmlFor="lider-password-actual">Contraseña actual</label>
                      <input
                        id="lider-password-actual"
                        type="password"
                        value={cambioPassword.password_actual}
                        onChange={(event) =>
                          setCambioPassword((prev) => ({
                            ...prev,
                            password_actual: event.target.value,
                          }))
                        }
                        autoComplete="current-password"
                        required
                      />
                    </div>

                    {/* La política se muestra antes de la nueva contraseña para
                        mantener la misma experiencia del cambio obligatorio. */}
                    <div className="form-field form-field-full login-security-note">
                      <strong>Requisitos para la nueva contraseña:</strong>{' '}
                      mínimo 12 caracteres, al menos un número (0-9), al menos una
                      letra (a, b, c...) y al menos un carácter especial
                      (!, @, #, $, %, etc.).
                    </div>

                    <div className="form-field">
                      <label htmlFor="lider-password-nuevo">Nueva contraseña</label>

                      <div className="password-security-field">
                        <input
                          id="lider-password-nuevo"
                          type="password"
                          value={cambioPassword.password_nuevo}
                          onChange={(event) =>
                            setCambioPassword((prev) => ({
                              ...prev,
                              password_nuevo: event.target.value,
                            }))
                          }
                          autoComplete="new-password"
                          required
                        />

                        {/* El semáforo permanece oculto con el campo vacío.
                            Al escribir, refleja visualmente la política central. */}
                        {passwordNueva.length > 0 && (
                          <div
                            className={
                              passwordCumplePolitica
                                ? 'password-security-status password-security-status--safe'
                                : 'password-security-status password-security-status--unsafe'
                            }
                            role="status"
                            aria-live="polite"
                          >
                            <span
                              className="password-security-light"
                              aria-hidden="true"
                            />
                            <span>
                              {passwordCumplePolitica
                                ? 'Contraseña Segura'
                                : 'Contraseña Insegura'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="form-field">
                      <label htmlFor="lider-password-confirmar">
                        Confirmar contraseña
                      </label>
                      <input
                        id="lider-password-confirmar"
                        type="password"
                        value={cambioPassword.confirmar_password}
                        onChange={(event) =>
                          setCambioPassword((prev) => ({
                            ...prev,
                            confirmar_password: event.target.value,
                          }))
                        }
                        autoComplete="new-password"
                        required
                      />
                    </div>
                  </div>

                  <div className="identity-modal-actions">
                    <button
                      type="button"
                      className="secondary-action-button"
                      onClick={() => {
                      setMostrarCambioPassword(false)
                      setErrorVista('')
                      setMensajeVista('')
                      setCambioPassword({
                        password_actual: '',
                        password_nuevo: '',
                        confirmar_password: '',
                      })
                    }}
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      className="primary-action-button"
                      disabled={cargandoVista}
                    >
                      {cargandoVista ? 'Procesando...' : 'Cambiar contraseña'}
                    </button>
                  </div>
                </form>
              </section>
            </div>
          )}
        </main>
      </div>
    )
  }

  // =========================================================
  // APLICACIÓN AUTENTICADA
  // =========================================================
  if (token && usuario) {
    return (
      <div className="app">
        <div className="dashboard-layout">
          <aside className="sidebar">
            <div className="sidebar-brand">
              <div className="logo-mark">IAM</div>
              <div>
                <strong>IAM Secure</strong>
                <span>Identity Platform</span>
              </div>
            </div>

            <nav className="sidebar-nav">
              <button
                type="button"
                className={vistaActual === 'panel' ? 'active' : ''}
                onClick={() => abrirVista('panel')}
              >
                Panel principal
              </button>

              {esAdminTI && (
                <>
                  <button
                    type="button"
                    className={vistaActual === 'soporte' ? 'active' : ''}
                    onClick={() => abrirVista('soporte')}
                  >
                    Administradores de soporte
                  </button>

                  <button type="button" className={vistaActual === 'auditoria' ? 'active' : ''}
                    onClick={() => { setVistaActual('auditoria'); setMensajeVista(''); setErrorVista('') }}>
                    Informe de auditoría
                  </button>

                  <button
                    type="button"
                    className={vistaActual === 'companias' ? 'active' : ''}
                    onClick={() => abrirVista('companias')}
                  >
                    Compañías
                  </button>
                </>
              )}

              {esAdminSoporte && (
                <>
                  <button
                    type="button"
                    className={vistaActual === 'identidades' ? 'active' : ''}
                    onClick={() => abrirVista('identidades')}
                  >
                    Identidades
                  </button>

                  <button
                    type="button"
                    className={vistaActual === 'companias' ? 'active' : ''}
                    onClick={() => abrirVista('companias')}
                  >
                    Compañías asignadas
                  </button>
                </>
              )}

              {esAdminSoporte && (
                <button type="button" className={vistaActual === 'cargas' ? 'active' : ''}
                  onClick={() => { setVistaActual('cargas'); setMensajeVista(''); setErrorVista('') }}>
                  Carga masiva
                </button>
              )}

              {esAdminSoporte && (
                <button type="button" onClick={abrirGrillaPermisos}>
                  Grilla de permisos
                </button>
              )}

              <button
                type="button"
                className={vistaActual === 'roles' ? 'active' : ''}
                onClick={() => abrirVista('roles')}
              >
                Roles y permisos
              </button>

              <button
                type="button"
                className={vistaActual === 'sesiones' ? 'active' : ''}
                onClick={() => abrirVista('sesiones')}
              >
                Sesiones
              </button>

              <button
                type="button"
                className={vistaActual === 'perfil' ? 'active' : ''}
                onClick={() => abrirVista('perfil')}
              >
                Mi perfil
              </button>
            </nav>

            <button
              type="button"
              className="logout-button"
              onClick={cerrarSesion}
            >
              Cerrar sesión
            </button>
          </aside>

          <main className="dashboard-main">
            <header className="dashboard-header">
              <div>
                <span className="eyebrow">IAM SECURE PLATFORM</span>
                <h1>
                  {vistaActual === 'panel' && 'Panel principal'}
                  {vistaActual === 'soporte' && 'Administradores de soporte'}
                  {vistaActual === 'companias' &&
                    (esAdminTI ? 'Compañías' : 'Compañías asignadas')}
                  {vistaActual === 'identidades' && 'Identidades'}
                  {vistaActual === 'cargas' && 'Carga masiva'}
                  {vistaActual === 'auditoria' && 'Informe de auditoría'}
                  {vistaActual === 'roles' && 'Roles y permisos'}
                  {vistaActual === 'sesiones' && 'Sesiones'}
                  {vistaActual === 'perfil' && 'Mi perfil'}
                </h1>
                <p>
                  {esAdminTI
                    ? 'Administración de plataforma bajo el principio de mínimo privilegio.'
                    : 'Gestión limitada a las compañías e identidades expresamente asignadas.'}
                </p>
              </div>

              <div className="user-badge">
                <div className="user-avatar">
                  {usuario.nombre?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div>
                  <strong>{usuario.nombre}</strong>
                  <span>{roles.join(', ')}</span>
                </div>
              </div>
            </header>

            {mostrarAvisoPassword && (
              <section className="identity-message-card password-warning" role="status">
                <span className="eyebrow">SEGURIDAD DE LA CONTRASEÑA</span>
                <p>{textoAvisoPassword}</p>
                <button
                  type="button"
                  className="primary-action-button"
                  onClick={() => setMostrarCambioPassword(true)}
                >
                  Cambiar contraseña ahora
                </button>
              </section>
            )}

            {mensajeVista && (
              <section className="identity-message-card">
                <span className="eyebrow">OPERACIÓN COMPLETADA</span>
                <p>{mensajeVista}</p>
              </section>
            )}

            {errorVista && (
              <section className="identity-message-card error">
                <span className="eyebrow">ERROR</span>
                <p>{errorVista}</p>
              </section>
            )}

            {cargandoVista && (
              <section className="identity-message-card">
                <span className="eyebrow">PROCESANDO</span>
                <p>Espere mientras se completa la operación.</p>
              </section>
            )}

            {/* =================================================
                PANEL PRINCIPAL
                ================================================= */}
            {vistaActual === 'panel' && (
              <>
                <section className="summary-grid">
                  <article className="summary-card">
                    <span className="summary-label">Estado</span>
                    <strong>{usuario.activo ? 'Activo' : 'Inactivo'}</strong>
                    <p>Estado actual de su cuenta.</p>
                  </article>

                  <article className="summary-card">
                    <span className="summary-label">Rol</span>
                    <strong>{roles.join(', ')}</strong>
                    <p>Nivel de acceso efectivo.</p>
                  </article>

                  <article className="summary-card">
                    <span className="summary-label">
                      {esAdminTI ? 'Compañías inscritas' : 'Compañías asignadas'}
                    </span>
                    <strong>{companias.length}</strong>
                    <p>
                      {esAdminTI
                        ? 'Compañías registradas en la plataforma.'
                        : 'Ámbitos autorizados para su gestión.'}
                    </p>
                  </article>
                </section>

                <section className="company-section">
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">SEGURIDAD DE LA CUENTA</span>
                      <h2>Mi contraseña</h2>
                      <p>
                        Puede cambiar su propia contraseña sin acceder a
                        credenciales de otros usuarios.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="primary-action-button"
                      onClick={() => setMostrarCambioPassword(true)}
                    >
                      Cambiar mi contraseña
                    </button>
                  </div>
                </section>

                <section className="company-section">
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">MULTITENANCY</span>
                      <h2>
                        {esAdminTI
                          ? 'Compañías inscritas'
                          : 'Compañías asignadas'}
                      </h2>
                    </div>
                  </div>

                  <div className="company-grid">
                    {companias.length === 0 ? (
                      <div className="empty-card">
                        No existen compañías disponibles para este usuario.
                      </div>
                    ) : (
                      companias.map((compania) => (
                        <article className="company-card" key={compania.id}>
                          <div className="company-code">{compania.codigo}</div>
                          <h3>{compania.nombre}</h3>
                          <p>{compania.descripcion || 'Sin descripción.'}</p>
                          <div className="company-status">
                            <span className="status-dot"></span>
                            {compania.activo ? 'Activa' : 'Inactiva'}
                          </div>
                        </article>
                      ))
                    )}
                  </div>
                </section>
              </>
            )}

            {/* =================================================
                ADMIN_TI: ADMINISTRADORES, COMPAÑÍAS Y ASIGNACIONES
                ================================================= */}
            {vistaActual === 'soporte' && esAdminTI && (
              <section className="admin-support-page">
                <div className="admin-page-intro">
                  <div>
                    <span className="eyebrow">PLATFORM ADMINISTRATION</span>
                    <h2>Administradores de soporte</h2>
                    <p>
                      Gestione las cuentas ADMIN_SOPORTE y el alcance de compañías
                      delegado a cada administrador. ADMIN_TI no accede a las
                      identidades internas de las compañías.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="primary-action-button"
                    disabled={cargandoVista}
                    onClick={() => {
                      setErrorVista('')
                      setMensajeVista('')
                      setNuevoAdminSoporte({
                        id_externo: '',
                        nombre: '',
                        email: '',
                        compania_id: '',
                      })
                      setMostrarNuevoAdminSoporte(true)
                    }}
                  >
                    + Nuevo ADMIN_SOPORTE
                  </button>
                </div>

                <div className="admin-kpi-grid">
                  <article className="admin-kpi-card">
                    <span>Administradores de soporte</span>
                    <strong>{usuariosAdministrables.length}</strong>
                    <p>Usuarios con rol ADMIN_SOPORTE.</p>
                  </article>
                  <article className="admin-kpi-card">
                    <span>Compañías inscritas</span>
                    <strong>{companias.length}</strong>
                    <p>Total registradas en la plataforma.</p>
                  </article>
                  <article className="admin-kpi-card">
                    <span>Compañías asignadas</span>
                    <strong>{new Set(asignaciones.map((item) => item.compania_id)).size}</strong>
                    <p>Con al menos un ADMIN_SOPORTE autorizado.</p>
                  </article>
                  <article className="admin-kpi-card">
                    <span>Compañías sin asignar</span>
                    <strong>
                      {companias.filter(
                        (compania) =>
                          !(asignacionesPorCompania.get(compania.id) || []).length
                      ).length}
                    </strong>
                    <p>Disponibles para delegar su administración.</p>
                  </article>
                </div>

                <div className="admin-section-card">
                  <div className="admin-section-heading">
                    <div>
                      <h3>Administradores de soporte</h3>
                      <p>Estado de cuenta y compañías autorizadas.</p>
                    </div>
                  </div>

                  {usuariosAdministrables.length === 0 ? (
                    <div className="empty-card">No existen usuarios ADMIN_SOPORTE.</div>
                  ) : (
                    <div className="identity-table-container">
                      <table className="identity-table admin-table">
                        <thead>
                          <tr>
                            <th>Administrador</th>
                            <th>Estado</th>
                            <th>Compañías asignadas</th>
                            <th>Acciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {usuariosAdministrables.map((item) => {
                            const asignadasAdmin = asignaciones.filter(
                              (asignacion) =>
                                Number(asignacion.usuario_id) === Number(item.id)
                            )
                            return (
                              <tr key={item.id}>
                                <td>
                                  <div className="identity-user">
                                    <div className="identity-avatar">
                                      {item.nombre?.charAt(0)?.toUpperCase() || 'S'}
                                    </div>
                                    <div>
                                      <strong>{item.nombre}</strong>
                                      <span>{item.id_externo || `ID #${item.id}`}</span>
                                    </div>
                                  </div>
                                </td>
                                <td>
                                  <span className={item.activo ? 'identity-status active' : 'identity-status inactive'}>
                                    <span className="status-dot"></span>
                                    {item.activo ? 'Activo' : 'Inactivo'}
                                  </span>
                                </td>
                                <td>
                                  <div className="assignment-cell">
                                    <strong>{asignadasAdmin.length} compañías</strong>
                                    <span>
                                      {asignadasAdmin.length
                                        ? asignadasAdmin.map((a) => a.compania_codigo).join(', ')
                                        : 'Sin asignar'}
                                    </span>
                                  </div>
                                </td>
                                <td>
                                  <div className="identity-actions">
                                    <button
                                      type="button"
                                      className="table-action-button"
                                      onClick={() => abrirEditarUsuario(item)}
                                      disabled={cargandoVista}
                                    >
                                      Editar
                                    </button>
                                    <button
                                      type="button"
                                      className="table-action-button"
                                      onClick={() => abrirAsignacionUsuario(item)}
                                      disabled={cargandoVista || !item.activo}
                                    >
                                      Gestionar compañías
                                    </button>
                                    {item.activo && (
                                      <button
                                        type="button"
                                        className="table-action-button"
                                        onClick={() => restablecerAcceso(item)}
                                        disabled={cargandoVista}
                                      >
                                        Restablecer acceso
                                      </button>
                                    )}
                                    {item.activo && esAdminTI && (
                                      <button
                                        type="button"
                                        className="table-action-button"
                                        onClick={() => abrirRestablecerMfa(item)}
                                        disabled={cargandoVista}
                                      >
                                        Restablecer MFA
                                      </button>
                                    )}
                                    <button
                                      type="button"
                                      className={`table-action-button ${item.activo ? 'danger' : 'success'}`}
                                      onClick={() => cambiarEstadoUsuario(item)}
                                      disabled={cargandoVista}
                                    >
                                      {item.activo ? 'Deshabilitar' : 'Habilitar'}
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <div className="admin-section-card">
                  <div className="admin-section-heading admin-section-heading-actions">
                    <div>
                      <h3>Compañías inscritas</h3>
                      <p>
                        Consulte el estado de las compañías y los administradores
                        que tienen alcance delegado.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="primary-action-button"
                      onClick={() => setMostrarNuevaCompania(true)}
                    >
                      + Nueva compañía
                    </button>
                  </div>

                  <div className="identity-table-container">
                    <table className="identity-table admin-table">
                      <thead>
                        <tr>
                          <th>Compañía</th>
                          <th>Estado</th>
                          <th>Administradores asignados</th>
                          <th>Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {companias.map((compania) => {
                          const asignadas = asignacionesPorCompania.get(compania.id) || []
                          return (
                            <tr key={compania.id}>
                              <td>
                                <div className="identity-user">
                                  <div className="identity-avatar">{compania.codigo?.charAt(0) || 'C'}</div>
                                  <div>
                                    <strong>{compania.nombre}</strong>
                                    <span>{compania.codigo}</span>
                                  </div>
                                </div>
                              </td>
                              <td>
                                <span className={compania.activo ? 'identity-status active' : 'identity-status inactive'}>
                                  <span className="status-dot"></span>
                                  {compania.activo ? 'Activa' : 'Inactiva'}
                                </span>
                              </td>
                              <td>
                                <div className="assignment-cell">
                                  <strong>{asignadas.length} administradores</strong>
                                  <span>
                                    {asignadas.length
                                      ? asignadas.map((a) => a.usuario_nombre).join(', ')
                                      : 'Sin asignar'}
                                  </span>
                                </div>
                              </td>
                              <td>
                                <div className="identity-actions">
                                  <button
                                    type="button"
                                    className="table-action-button"
                                    onClick={() => abrirEditarCompania(compania)}
                                    disabled={cargandoVista}
                                  >
                                    Editar
                                  </button>

                                  {asignadas.length > 0 && (
                                    <button
                                      type="button"
                                      className="table-action-button"
                                      onClick={() => eliminarAsignacion(asignadas[0])}
                                      disabled={cargandoVista}
                                    >
                                      Dejar sin asignar
                                    </button>
                                  )}

                                  <button
                                    type="button"
                                    className={`table-action-button ${compania.activo ? 'danger' : 'success'}`}
                                    onClick={() => cambiarEstadoCompania(compania)}
                                    disabled={cargandoVista}
                                  >
                                    {compania.activo ? 'Deshabilitar' : 'Habilitar'}
                                  </button>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="admin-info-note">
                  <strong>Asignación de compañías</strong>
                  <span>
                    Las compañías asignadas determinan el alcance de ADMIN_SOPORTE.
                    Las identidades internas continúan siendo administradas únicamente
                    por ADMIN_SOPORTE dentro de su ámbito autorizado.
                  </span>
                </div>
              </section>
            )}

            {/* =================================================
                COMPAÑÍAS
                ================================================= */}
            {vistaActual === 'companias' && (
              <section className="company-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">MULTITENANCY</span>
                    <h2>{esAdminTI ? 'Compañías de la plataforma' : 'Compañías asignadas'}</h2>
                    <p>
                      {esAdminTI
                        ? 'ADMIN_TI administra el ciclo de vida de las compañías, sin acceder a sus identidades internas.'
                        : 'Solo se muestran compañías activas asignadas por ADMIN_TI.'}
                    </p>
                  </div>
                  {esAdminTI && (
                    <button type="button" className="primary-action-button" onClick={() => setMostrarNuevaCompania(true)}>
                      + Nueva compañía
                    </button>
                  )}
                </div>
                <div className="company-grid">
                  {companias.length === 0 ? (
                    <div className="empty-card">No existen compañías.</div>
                  ) : companias.map((compania) => (
                    <article className="company-card" key={compania.id}>
                      <div className="company-code">{compania.codigo}</div>
                      <h3>{compania.nombre}</h3>
                      <p>{compania.descripcion || 'Sin descripción.'}</p>
                      <div className="company-status"><span className="status-dot"></span>{compania.activo ? 'Activa' : 'Inactiva'}</div>
                      {esAdminTI && (
                        <div className="identity-actions">
                          <button
                            type="button"
                            className="table-action-button"
                            onClick={() => abrirEditarCompania(compania)}
                            disabled={cargandoVista}
                          >
                            Editar
                          </button>
                          <button type="button" className="table-action-button" onClick={() => cambiarEstadoCompania(compania)} disabled={cargandoVista}>
                            {compania.activo ? 'Deshabilitar' : 'Habilitar'}
                          </button>
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            )}

            {/* =================================================
                ADMIN_SOPORTE: IDENTIDADES
                ================================================= */}
            {vistaActual === 'cargas' && esAdminSoporte && (
              <BulkUserImport apiUrl={API_URL} token={token} companias={companias}
                onExpired={limpiarSesionLocal} />
            )}

            {vistaActual === 'auditoria' && esAdminTI && (
              <AuditReport token={token} onExpired={limpiarSesionLocal} />
            )}

            {vistaActual === 'identidades' && esAdminSoporte && (
              <section className="identities-section">
                <div className="identities-heading">
                  <div>
                    <span className="eyebrow">IDENTITY MANAGEMENT</span>
                    <h2>Identidades administrables</h2>
                    <p>
                      Solo aparecen líderes pertenecientes a compañías activas
                      asignadas a este ADMIN_SOPORTE.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="primary-action-button"
                    onClick={() => {
                      setNuevaIdentidad({
                        id_externo: '',
                        nombre: '',
                        email: '',
                        rol: 'LIDER_FACTURACION',
                        compania_id:
                          companias.length === 1
                            ? String(companias[0].id)
                            : '',
                      })
                      setMostrarNuevaIdentidad(true)
                    }}
                  >
                    + Nueva identidad
                  </button>
                </div>

                {usuariosAdministrables.length === 0 ? (
                  <div className="empty-card">
                    No existen identidades administrables en sus compañías
                    asignadas.
                  </div>
                ) : (
                  <div className="identity-table-container">
                    <table className="identity-table">
                      <thead>
                        <tr>
                          <th>Identidad</th>
                          <th>Compañía</th>
                          <th>Rol</th>
                          <th>Estado</th>
                          <th>Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {usuariosAdministrables.map((item) => (
                          <tr key={`${item.id}-${item.compania_id}`}>
                            <td>
                              <div className="identity-user">
                                <div className="identity-avatar">
                                  {item.nombre?.charAt(0)?.toUpperCase() || 'U'}
                                </div>
                                <div>
                                  <strong>{item.nombre}</strong>
                                  <span>{item.id_externo || `ID #${item.id}`}</span>
                                </div>
                              </div>
                            </td>
                            <td>
                              {item.compania_codigo} — {item.compania_nombre}
                            </td>
                            <td>
                              <select
                                value={item.rol}
                                onChange={(event) =>
                                  cambiarRolIdentidad(item, event.target.value)
                                }
                                disabled={cargandoVista}
                              >
                                {ROLES_LIDER.map((rol) => (
                                  <option key={rol} value={rol}>
                                    {rol}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>
                              <span
                                className={
                                  item.activo
                                    ? 'identity-status active'
                                    : 'identity-status inactive'
                                }
                              >
                                <span className="status-dot"></span>
                                {item.activo ? 'Activo' : 'Inactivo'}
                              </span>
                            </td>
                            <td>
                              <div className="identity-actions">
                                <button
                                  type="button"
                                  className="table-action-button"
                                  onClick={() => abrirEditarUsuario(item)}
                                  disabled={cargandoVista}
                                >
                                  Editar
                                </button>

                                <button
                                  type="button"
                                  className="table-action-button"
                                  onClick={() => cambiarEstadoUsuario(item)}
                                  disabled={cargandoVista}
                                >
                                  {item.activo ? 'Deshabilitar' : 'Habilitar'}
                                </button>

                                {item.activo && (
                                  <button
                                    type="button"
                                    className="table-action-button"
                                    onClick={() => restablecerAcceso(item)}
                                    disabled={cargandoVista}
                                  >
                                    Restablecer acceso
                                  </button>
                                )}

                                {item.activo && esAdminSoporte && (
                                  <button
                                    type="button"
                                    className="table-action-button"
                                    onClick={() => abrirRestablecerMfa(item)}
                                    disabled={cargandoVista}
                                  >
                                    Restablecer MFA
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            )}

            {/* =================================================
                ROLES Y PERMISOS
                ================================================= */}
            {vistaActual === 'roles' && (
              <section className="company-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">RBAC</span>
                    <h2>Roles y permisos</h2>
                    <p>Resumen del alcance administrativo aplicado.</p>
                  </div>
                </div>

                <div className="company-grid">
                  {esAdminTI && (
                    <article className="company-card">
                      <div className="company-code">ADMIN_TI</div>
                      <h3>Administración de plataforma</h3>
                      <p>
                        Gestiona ADMIN_SOPORTE, compañías y asignaciones. No
                        administra identidades internas de las compañías.
                      </p>
                    </article>
                  )}

                  {esAdminSoporte && (
                    <article className="company-card">
                      <div className="company-code">ADMIN_SOPORTE</div>
                      <h3>Administración delegada</h3>
                      <p>
                        Gestiona únicamente líderes de las compañías activas
                        que ADMIN_TI le haya asignado.
                      </p>
                    </article>
                  )}
                </div>
              </section>
            )}

            {/* =================================================
                SESIONES
                ================================================= */}
            {vistaActual === 'sesiones' && (
              <section className="identities-section">
                <div className="identities-heading">
                  <div>
                    <span className="eyebrow">SESSION MANAGEMENT</span>
                    <h2>Mis sesiones</h2>
                    <p>
                      Consulte y revoque las sesiones asociadas a su cuenta.
                    </p>
                  </div>

                  {esAdminTI && (
                    <button
                      type="button"
                      className="secondary-action-button"
                      onClick={limpiarSesionesExpiradas}
                      disabled={cargandoVista}
                    >
                      Limpiar expiradas
                    </button>
                  )}
                </div>

                <div className="identity-table-container">
                  <table className="identity-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Creación</th>
                        <th>Expiración</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sesiones.length === 0 ? (
                        <tr>
                          <td colSpan="5">No existen sesiones para mostrar.</td>
                        </tr>
                      ) : (
                        sesiones.map((sesion) => (
                          <tr key={sesion.id}>
                            <td>#{sesion.id}</td>
                            <td>{sesion.fecha_creacion || '—'}</td>
                            <td>{sesion.fecha_expiracion || '—'}</td>
                            <td>{sesion.revocada ? 'Revocada' : 'Activa'}</td>
                            <td>
                              {!sesion.revocada && (
                                <button
                                  type="button"
                                  className="table-action-button"
                                  onClick={() => revocarSesion(sesion.id)}
                                  disabled={cargandoVista}
                                >
                                  Revocar
                                </button>
                              )}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* =================================================
                MI PERFIL
                ================================================= */}
            {vistaActual === 'perfil' && (
              <section className="company-section">
                <div className="section-heading">
                  <div>
                    <span className="eyebrow">MI CUENTA</span>
                    <h2>{usuario.nombre}</h2>
                    <p>{usuario.email}</p>
                  </div>
                  <button
                    type="button"
                    className="primary-action-button"
                    onClick={() => setMostrarCambioPassword(true)}
                  >
                    Cambiar mi contraseña
                  </button>
                </div>

                <div className="summary-grid">
                  <article className="summary-card">
                    <span className="summary-label">Identificador</span>
                    <strong>{usuario.id_externo || usuario.id}</strong>
                  </article>
                  <article className="summary-card">
                    <span className="summary-label">Rol</span>
                    <strong>{roles.join(', ')}</strong>
                  </article>
                  <article className="summary-card">
                    <span className="summary-label">Estado</span>
                    <strong>{usuario.activo ? 'Activo' : 'Inactivo'}</strong>
                  </article>
                </div>

                {/* =================================================
                    MFA / AUTHENTICATOR
                    =================================================
                    SEGURIDAD:
                    - El secreto TOTP nunca llega al frontend.
                    - El backend entrega únicamente el QR PNG.
                    - El QR existe solo mediante una Blob URL temporal.
                    - El código de 6 dígitos se envía únicamente por HTTPS
                      cuando el usuario confirma la activación.
                    ================================================= */}
                <section
                  className="company-section mfa-profile-section"
                >
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">AUTENTICACIÓN MULTIFACTOR</span>
                      <h2>Authenticator</h2>
                      <p>
                        Proteja su cuenta con un segundo factor basado en TOTP.
                      </p>
                    </div>

                    <div
                      className="mfa-account-actions"
                    >
                      <span
                        className={mfaActivo ? 'mfa-status mfa-status--active' : 'mfa-status mfa-status--inactive'}
                      >
                        {mfaActivo ? 'MFA activo' : 'MFA no activado'}
                      </span>

                      {!mfaActivo && !mfaEnrolamientoIniciado && (
                        <button
                          type="button"
                          className="primary-action-button"
                          onClick={iniciarEnrolamientoMfa}
                          disabled={mfaProcesando}
                        >
                          {mfaProcesando
                            ? 'Preparando...'
                            : 'Configurar Authenticator'}
                        </button>
                      )}
                    </div>
                  </div>

                  {mfaEnrolamientoIniciado && !mfaActivo && (
                    <div
                      className="mfa-enrollment-grid"
                    >
                      <div
                        className="mfa-enrollment-qr-container"
                      >
                        {mfaQrUrl && (
                          <img
                            src={mfaQrUrl}
                            alt="Código QR para configurar Authenticator"
                            width="256"
                            height="256"
                            className="mfa-enrollment-qr-image"
                          />
                        )}
                      </div>

                      <div>
                        <h3>Configure su Authenticator</h3>
                        <ol className="mfa-enrollment-instructions">
                          <li>
                            Abra Microsoft Authenticator, Google Authenticator
                            u otra aplicación compatible con TOTP.
                          </li>
                          <li>Escanee el código QR mostrado.</li>
                          <li>
                            Introduzca aquí el código temporal de 6 dígitos.
                          </li>
                        </ol>

                        <form
                          onSubmit={activarMfa}
                          className="mfa-enrollment-form"
                        >
                          <div className="form-field">
                            <label htmlFor="mfa-codigo">
                              Código Authenticator
                            </label>
                            <input
                              id="mfa-codigo"
                              type="text"
                              inputMode="numeric"
                              autoComplete="one-time-code"
                              maxLength={6}
                              pattern="[0-9]{6}"
                              value={mfaCodigo}
                              onChange={(event) =>
                                setMfaCodigo(
                                  event.target.value
                                    .replace(/\D/g, '')
                                    .slice(0, 6)
                                )
                              }
                              placeholder="123456"
                              required
                            />
                          </div>

                          <button
                            type="submit"
                            className="primary-action-button"
                            disabled={mfaProcesando || mfaCodigo.length !== 6}
                          >
                            {mfaProcesando ? 'Validando...' : 'Activar MFA'}
                          </button>

                          <button
                            type="button"
                            className="secondary-action-button"
                            disabled={mfaProcesando}
                            onClick={() => {
                              limpiarQrMfa()
                              setMfaEnrolamientoIniciado(false)
                              setMfaCodigo('')
                              setMensajeVista('')
                              setErrorVista('')
                            }}
                          >
                            Cancelar
                          </button>
                        </form>
                      </div>
                    </div>
                  )}
                </section>
              </section>
            )}

            {/* =================================================
                MODAL: RESTABLECER ACCESO DE USUARIO
                =================================================
                SEGURIDAD:
                - El administrador no introduce contraseñas.
                - La contraseña temporal se genera en el backend.
                - La contraseña temporal no se muestra en pantalla.
                - Se envía únicamente al correo registrado.
                ================================================= */}
            {mostrarRestablecerAcceso && usuarioRestablecer && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="restablecer-acceso-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">
                        SEGURIDAD DE LA CUENTA
                      </span>

                      <h2 id="restablecer-acceso-titulo">
                        Restablecer acceso
                      </h2>
                    </div>

                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={cerrarRestablecerAcceso}
                      disabled={restableciendoAcceso}
                      aria-label="Cerrar"
                    >
                      ×
                    </button>
                  </div>

                  <div className="identity-form">
                    <div className="identity-message-card">
                      <span className="eyebrow">
                        RESTABLECIMIENTO DE CONTRASEÑA
                      </span>

                      <p>
                        Se generará una contraseña temporal para{' '}
                        <strong>
                          {usuarioRestablecer.nombre ||
                            usuarioRestablecer.id_externo ||
                            'la identidad seleccionada'}
                        </strong>
                        .
                      </p>

                      <p>
                        La contraseña temporal será enviada al correo
                        registrado de la identidad y no será mostrada
                        al administrador.
                      </p>

                      <p>
                        Las sesiones anteriores serán revocadas y el
                        usuario deberá cambiar la contraseña temporal
                        después de iniciar sesión.
                      </p>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={cerrarRestablecerAcceso}
                        disabled={restableciendoAcceso}
                      >
                        Cancelar
                      </button>

                      <button
                        type="button"
                        className="primary-action-button"
                        onClick={confirmarRestablecerAcceso}
                        disabled={restableciendoAcceso}
                      >
                        {restableciendoAcceso
                          ? 'Procesando...'
                          : 'Enviar contraseña temporal'}
                      </button>
                    </div>
                  </div>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: RESTABLECER MFA - ADMIN_TI / ADMIN_SOPORTE
                =================================================
                SEGURIDAD:
                - No muestra ni genera secretos TOTP.
                - No muestra ni genera el QR del usuario.
                - El backend valida RBAC y multitenancy.
                - Las sesiones y desafíos anteriores se invalidan.
                - El usuario realiza el nuevo enrolamiento en su login.
                ================================================= */}
            {mostrarRestablecerMfa && usuarioRestablecerMfa && (esAdminTI || esAdminSoporte) && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="restablecer-mfa-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">AUTENTICACIÓN MULTIFACTOR</span>
                      <h2 id="restablecer-mfa-titulo">Restablecer MFA</h2>
                    </div>

                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={cerrarRestablecerMfa}
                      disabled={restableciendoMfa}
                      aria-label="Cerrar"
                    >
                      ×
                    </button>
                  </div>

                  <div className="identity-form">
                    {errorVista && (
                      <div className="error-message" role="alert">
                        {errorVista}
                      </div>
                    )}

                    <div className="identity-message-card">
                      <span className="eyebrow">NUEVA VINCULACIÓN AUTHENTICATOR</span>

                      <p>
                        Se eliminará la vinculación MFA actual de{' '}
                        <strong>
                          {usuarioRestablecerMfa.nombre ||
                            usuarioRestablecerMfa.id_externo ||
                            'la identidad seleccionada'}
                        </strong>
                        .
                      </p>

                      <p>
                        Las sesiones activas y los desafíos MFA pendientes serán
                        invalidados. La contraseña del usuario no será modificada.
                      </p>

                      <p>
                        En el próximo inicio de sesión, el usuario deberá vincular
                        nuevamente Authenticator y será el único que verá el nuevo
                        código QR.
                      </p>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={cerrarRestablecerMfa}
                        disabled={restableciendoMfa}
                      >
                        Cancelar
                      </button>

                      <button
                        type="button"
                        className="primary-action-button"
                        onClick={confirmarRestablecerMfa}
                        disabled={restableciendoMfa}
                      >
                        {restableciendoMfa
                          ? 'Restableciendo...'
                          : 'Confirmar restablecimiento MFA'}
                      </button>
                    </div>
                  </div>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: CAMBIO DE CONTRASEÑA PROPIA
                ================================================= */}
            {mostrarCambioPassword && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="cambio-password-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">SEGURIDAD DE LA CUENTA</span>
                      <h2 id="cambio-password-titulo">
                        Cambiar mi contraseña
                      </h2>
                    </div>
                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={() => {
                        setMostrarCambioPassword(false)
                        setErrorVista('')
                        setMensajeVista('')
                        setCambioPassword({
                          password_actual: '',
                          password_nuevo: '',
                          confirmar_password: '',
                        })
                      }}
                    >
                      ×
                    </button>
                  </div>

                  {/* Cambio voluntario para portales administrativos.
                      Usa la misma política visual y validación que el portal
                      de líderes y que el cambio obligatorio de contraseña. */}
                  {errorVista && (
                    <div className="error-message" role="alert">
                      {errorVista}
                    </div>
                  )}

                  <form className="identity-form" onSubmit={cambiarMiPassword}>
                    <div className="identity-form-grid">
                      <div className="form-field form-field-full">
                        <label htmlFor="password-actual">Contraseña actual</label>
                        <input
                          id="password-actual"
                          type="password"
                          value={cambioPassword.password_actual}
                          onChange={(event) =>
                            setCambioPassword((prev) => ({
                              ...prev,
                              password_actual: event.target.value,
                            }))
                          }
                          autoComplete="current-password"
                          required
                        />
                      </div>

                      {/* Los requisitos se muestran explícitamente para que
                          todos los roles reciban la misma orientación. */}
                      <div className="form-field form-field-full login-security-note">
                        <strong>Requisitos para la nueva contraseña:</strong>{' '}
                        mínimo 12 caracteres, al menos un número (0-9), al menos una
                        letra (a, b, c...) y al menos un carácter especial
                        (!, @, #, $, %, etc.).
                      </div>

                      <div className="form-field">
                        <label htmlFor="password-nuevo">Nueva contraseña</label>

                        <div className="password-security-field">
                          <input
                            id="password-nuevo"
                            type="password"
                            value={cambioPassword.password_nuevo}
                            onChange={(event) =>
                              setCambioPassword((prev) => ({
                                ...prev,
                                password_nuevo: event.target.value,
                              }))
                            }
                            autoComplete="new-password"
                            required
                          />

                          {/* Semáforo accesible: no depende únicamente del color. */}
                          {passwordNueva.length > 0 && (
                            <div
                              className={
                                passwordCumplePolitica
                                  ? 'password-security-status password-security-status--safe'
                                  : 'password-security-status password-security-status--unsafe'
                              }
                              role="status"
                              aria-live="polite"
                            >
                              <span
                                className="password-security-light"
                                aria-hidden="true"
                              />
                              <span>
                                {passwordCumplePolitica
                                  ? 'Contraseña Segura'
                                  : 'Contraseña Insegura'}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="form-field">
                        <label htmlFor="password-confirmar">
                          Confirmar contraseña
                        </label>
                        <input
                          id="password-confirmar"
                          type="password"
                          value={cambioPassword.confirmar_password}
                          onChange={(event) =>
                            setCambioPassword((prev) => ({
                              ...prev,
                              confirmar_password: event.target.value,
                            }))
                          }
                          autoComplete="new-password"
                          required
                        />
                      </div>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={() => {
                          setMostrarCambioPassword(false)
                          setErrorVista('')
                          setMensajeVista('')
                          setCambioPassword({
                            password_actual: '',
                            password_nuevo: '',
                            confirmar_password: '',
                          })
                        }}
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={cargandoVista}
                      >
                        {cargandoVista ? 'Procesando...' : 'Cambiar contraseña'}
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: EDITAR USUARIO ADMINISTRABLE
                ================================================= */}
            {mostrarEditarUsuario &&
              usuarioEditar &&
              (esAdminTI || esAdminSoporte) && (
                <div className="modal-overlay" role="presentation">
                  <section
                    className="identity-modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="editar-usuario-titulo"
                  >
                    <div className="identity-modal-header">
                      <div>
                        <span className="eyebrow">IDENTITY MANAGEMENT</span>
                        <h2 id="editar-usuario-titulo">
                          Editar usuario
                        </h2>
                        <p>
                          Corrija únicamente los datos básicos de la identidad.
                          Rol, estado, MFA y alcance se administran por separado.
                        </p>
                      </div>

                      <button
                        type="button"
                        className="modal-close-button"
                        onClick={() => {
                          setMostrarEditarUsuario(false)
                          setUsuarioEditar(null)
                          setEdicionUsuario({
                            id_externo: '',
                            nombre: '',
                            email: '',
                          })
                        }}
                        disabled={cargandoVista}
                      >
                        ×
                      </button>
                    </div>

                    <form
                      className="identity-form"
                      onSubmit={guardarEdicionUsuario}
                    >
                      <div className="identity-form-grid">
                        <div className="form-field">
                          <label htmlFor="editar-usuario-id-externo">
                            Identificador
                          </label>
                          <input
                            id="editar-usuario-id-externo"
                            value={edicionUsuario.id_externo}
                            onChange={(event) =>
                              setEdicionUsuario((prev) => ({
                                ...prev,
                                id_externo: event.target.value,
                              }))
                            }
                            maxLength={50}
                            required
                          />
                        </div>

                        <div className="form-field">
                          <label htmlFor="editar-usuario-nombre">
                            Nombre
                          </label>
                          <input
                            id="editar-usuario-nombre"
                            value={edicionUsuario.nombre}
                            onChange={(event) =>
                              setEdicionUsuario((prev) => ({
                                ...prev,
                                nombre: event.target.value,
                              }))
                            }
                            maxLength={100}
                            required
                          />
                        </div>

                        <div className="form-field form-field-full">
                          <label htmlFor="editar-usuario-email">
                            Correo
                          </label>
                          <input
                            id="editar-usuario-email"
                            type="email"
                            value={edicionUsuario.email}
                            onChange={(event) =>
                              setEdicionUsuario((prev) => ({
                                ...prev,
                                email: event.target.value,
                              }))
                            }
                            autoComplete="off"
                            required
                          />
                        </div>
                      </div>

                      <div className="login-security-note">
                        Por seguridad, una corrección de datos revoca las
                        sesiones activas del usuario modificado. El backend
                        vuelve a validar RBAC y alcance multitenant.
                      </div>

                      <div className="identity-modal-actions">
                        <button
                          type="button"
                          className="secondary-action-button"
                          onClick={() => {
                            setMostrarEditarUsuario(false)
                            setUsuarioEditar(null)
                            setEdicionUsuario({
                              id_externo: '',
                              nombre: '',
                              email: '',
                            })
                          }}
                          disabled={cargandoVista}
                        >
                          Cancelar
                        </button>

                        <button
                          type="submit"
                          className="primary-action-button"
                          disabled={cargandoVista}
                        >
                          {cargandoVista ? 'Guardando...' : 'Guardar cambios'}
                        </button>
                      </div>
                    </form>
                  </section>
                </div>
              )}

            {/* =================================================
                MODAL: EDITAR COMPAÑÍA
                ================================================= */}
            {mostrarEditarCompania && esAdminTI && companiaEditar && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="editar-compania-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">MULTITENANCY</span>
                      <h2 id="editar-compania-titulo">
                        Editar compañía
                      </h2>
                      <p>
                        Corrija código, nombre o descripción. El estado y las
                        asignaciones se administran de forma independiente.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={() => {
                        setMostrarEditarCompania(false)
                        setCompaniaEditar(null)
                        setEdicionCompania({
                          codigo: '',
                          nombre: '',
                          descripcion: '',
                        })
                      }}
                      disabled={cargandoVista}
                    >
                      ×
                    </button>
                  </div>

                  <form
                    className="identity-form"
                    onSubmit={guardarEdicionCompania}
                  >
                    <div className="identity-form-grid">
                      <div className="form-field">
                        <label htmlFor="editar-compania-codigo">
                          Código
                        </label>
                        <input
                          id="editar-compania-codigo"
                          value={edicionCompania.codigo}
                          onChange={(event) =>
                            setEdicionCompania((prev) => ({
                              ...prev,
                              codigo: event.target.value,
                            }))
                          }
                          maxLength={50}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="editar-compania-nombre">
                          Nombre
                        </label>
                        <input
                          id="editar-compania-nombre"
                          value={edicionCompania.nombre}
                          onChange={(event) =>
                            setEdicionCompania((prev) => ({
                              ...prev,
                              nombre: event.target.value,
                            }))
                          }
                          maxLength={150}
                          required
                        />
                      </div>

                      <div className="form-field form-field-full">
                        <label htmlFor="editar-compania-descripcion">
                          Descripción
                        </label>
                        <textarea
                          id="editar-compania-descripcion"
                          value={edicionCompania.descripcion}
                          onChange={(event) =>
                            setEdicionCompania((prev) => ({
                              ...prev,
                              descripcion: event.target.value,
                            }))
                          }
                          maxLength={500}
                          rows={4}
                        />
                      </div>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={() => {
                          setMostrarEditarCompania(false)
                          setCompaniaEditar(null)
                          setEdicionCompania({
                            codigo: '',
                            nombre: '',
                            descripcion: '',
                          })
                        }}
                        disabled={cargandoVista}
                      >
                        Cancelar
                      </button>

                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={cargandoVista}
                      >
                        {cargandoVista ? 'Guardando...' : 'Guardar cambios'}
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: NUEVA COMPAÑÍA
                ================================================= */}
            {mostrarNuevaCompania && esAdminTI && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="nueva-compania-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">MULTITENANCY</span>
                      <h2 id="nueva-compania-titulo">Nueva compañía</h2>
                    </div>
                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={() => setMostrarNuevaCompania(false)}
                    >
                      ×
                    </button>
                  </div>

                  <form className="identity-form" onSubmit={crearCompania}>
                    <div className="identity-form-grid">
                      <div className="form-field">
                        <label htmlFor="compania-codigo">Código</label>
                        <input
                          id="compania-codigo"
                          value={nuevaCompania.codigo}
                          onChange={(event) =>
                            setNuevaCompania((prev) => ({
                              ...prev,
                              codigo: event.target.value,
                            }))
                          }
                          maxLength={50}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="compania-nombre">Nombre</label>
                        <input
                          id="compania-nombre"
                          value={nuevaCompania.nombre}
                          onChange={(event) =>
                            setNuevaCompania((prev) => ({
                              ...prev,
                              nombre: event.target.value,
                            }))
                          }
                          maxLength={150}
                          required
                        />
                      </div>

                      <div className="form-field form-field-full">
                        <label htmlFor="compania-descripcion">Descripción</label>
                        <textarea
                          id="compania-descripcion"
                          value={nuevaCompania.descripcion}
                          onChange={(event) =>
                            setNuevaCompania((prev) => ({
                              ...prev,
                              descripcion: event.target.value,
                            }))
                          }
                          maxLength={500}
                        />
                      </div>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={() => setMostrarNuevaCompania(false)}
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={cargandoVista}
                      >
                        Crear compañía
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: CREAR ADMIN_SOPORTE - SOLO ADMIN_TI
                =================================================
                El rol se mantiene fijo en ADMIN_SOPORTE.
                La contraseña temporal nunca se genera ni se muestra
                en el frontend; el backend la envía al correo registrado.
                ================================================= */}
            {mostrarNuevoAdminSoporte && esAdminTI && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="nuevo-admin-soporte-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">PLATFORM ADMINISTRATION</span>
                      <h2 id="nuevo-admin-soporte-titulo">
                        Nuevo ADMIN_SOPORTE
                      </h2>
                      <p>
                        Cree una cuenta administrativa delegada. La cuenta
                        quedará inicialmente sin compañía y el alcance podrá
                        asignarse posteriormente. La contraseña temporal será
                        generada por el backend y enviada al correo registrado.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={() => {
                        setMostrarNuevoAdminSoporte(false)
                        setNuevoAdminSoporte({
                          id_externo: '',
                          nombre: '',
                          email: '',
                          compania_id: '',
                        })
                      }}
                      disabled={cargandoVista}
                    >
                      ×
                    </button>
                  </div>

                  <form
                    className="identity-form"
                    onSubmit={crearAdminSoporte}
                  >
                    <div className="identity-form-grid">
                      <div className="form-field">
                        <label htmlFor="admin-soporte-id-externo">
                          Identificador
                        </label>
                        <input
                          id="admin-soporte-id-externo"
                          value={nuevoAdminSoporte.id_externo}
                          onChange={(event) =>
                            setNuevoAdminSoporte((prev) => ({
                              ...prev,
                              id_externo: event.target.value,
                            }))
                          }
                          maxLength={50}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="admin-soporte-nombre">
                          Nombre
                        </label>
                        <input
                          id="admin-soporte-nombre"
                          value={nuevoAdminSoporte.nombre}
                          onChange={(event) =>
                            setNuevoAdminSoporte((prev) => ({
                              ...prev,
                              nombre: event.target.value,
                            }))
                          }
                          maxLength={100}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="admin-soporte-email">
                          Correo
                        </label>
                        <input
                          id="admin-soporte-email"
                          type="email"
                          value={nuevoAdminSoporte.email}
                          onChange={(event) =>
                            setNuevoAdminSoporte((prev) => ({
                              ...prev,
                              email: event.target.value,
                            }))
                          }
                          autoComplete="off"
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="admin-soporte-rol">
                          Rol
                        </label>
                        <input
                          id="admin-soporte-rol"
                          value="ADMIN_SOPORTE"
                          readOnly
                          aria-readonly="true"
                        />
                      </div>

                    </div>

                    <div className="login-security-note">
                      El nuevo ADMIN_SOPORTE recibirá una contraseña temporal
                      por correo y deberá cambiarla antes de acceder a las
                      funciones normales de la plataforma. La cuenta puede
                      permanecer sin compañía hasta que ADMIN_TI delegue un alcance.
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={() => {
                          setMostrarNuevoAdminSoporte(false)
                          setNuevoAdminSoporte({
                            id_externo: '',
                            nombre: '',
                            email: '',
                            compania_id: '',
                          })
                        }}
                        disabled={cargandoVista}
                      >
                        Cancelar
                      </button>

                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={cargandoVista}
                      >
                        {cargandoVista
                          ? 'Creando...'
                          : 'Crear ADMIN_SOPORTE'}
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: ASIGNAR COMPAÑÍAS A ADMIN_SOPORTE
                ================================================= */}
            {mostrarAsignacion && esAdminTI && adminAsignacion && (
              <div className="modal-overlay" role="presentation">
                <section className="identity-modal assignment-modal" role="dialog" aria-modal="true" aria-labelledby="asignacion-titulo">
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">LEAST PRIVILEGE</span>
                      <h2 id="asignacion-titulo">Asignar compañías a {adminAsignacion.nombre}</h2>
                      <p>
                        Seleccione las compañías que este administrador podrá gestionar.
                        Puede dejar todas sin seleccionar para mantenerlo sin alcance.
                      </p>
                    </div>
                    <button type="button" className="modal-close-button" onClick={() => { setMostrarAsignacion(false); setAdminAsignacion(null); setCompaniasSeleccionadas([]) }}>×</button>
                  </div>

                  <form className="identity-form" onSubmit={guardarAsignacionesUsuario}>
                    <div className="company-check-list">
                      {companiasActivas.length === 0 ? (
                        <div className="empty-card">No existen compañías activas disponibles.</div>
                      ) : companiasActivas.map((compania) => {
                        const checked = companiasSeleccionadas.includes(Number(compania.id))
                        return (
                          <label className={`company-check-option ${checked ? 'selected' : ''}`} key={compania.id}>
                            <input type="checkbox" checked={checked} onChange={() => alternarCompaniaSeleccionada(compania.id)} />
                            <span className="company-check-avatar">{compania.codigo?.charAt(0) || 'C'}</span>
                            <span className="company-check-copy">
                              <strong>{compania.nombre}</strong>
                              <small>{compania.descripcion || compania.codigo}</small>
                            </span>
                          </label>
                        )
                      })}
                    </div>

                    <div className="identity-modal-actions">
                      <button type="button" className="secondary-action-button" onClick={() => { setMostrarAsignacion(false); setAdminAsignacion(null); setCompaniasSeleccionadas([]) }}>Cancelar</button>
                      <button type="submit" className="primary-action-button" disabled={cargandoVista}>Guardar alcance</button>
                    </div>
                  </form>
                </section>
              </div>
            )}

            {/* =================================================
                MODAL: NUEVA IDENTIDAD ORGANIZACIONAL
                ================================================= */}
            {mostrarNuevaIdentidad && esAdminSoporte && (
              <div className="modal-overlay" role="presentation">
                <section
                  className="identity-modal"
                  role="dialog"
                  aria-modal="true"
                  aria-labelledby="nueva-identidad-titulo"
                >
                  <div className="identity-modal-header">
                    <div>
                      <span className="eyebrow">IDENTITY MANAGEMENT</span>
                      <h2 id="nueva-identidad-titulo">Nueva identidad</h2>
                      <p>
                        La contraseña temporal será generada por el backend y
                        enviada al correo registrado.
                      </p>
                    </div>
                    <button
                      type="button"
                      className="modal-close-button"
                      onClick={() => setMostrarNuevaIdentidad(false)}
                    >
                      ×
                    </button>
                  </div>

                  <form className="identity-form" onSubmit={crearIdentidad}>
                    <div className="identity-form-grid">
                      <div className="form-field">
                        <label htmlFor="identidad-id-externo">
                          Identificador
                        </label>
                        <input
                          id="identidad-id-externo"
                          value={nuevaIdentidad.id_externo}
                          onChange={(event) =>
                            setNuevaIdentidad((prev) => ({
                              ...prev,
                              id_externo: event.target.value,
                            }))
                          }
                          maxLength={50}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="identidad-nombre">Nombre</label>
                        <input
                          id="identidad-nombre"
                          value={nuevaIdentidad.nombre}
                          onChange={(event) =>
                            setNuevaIdentidad((prev) => ({
                              ...prev,
                              nombre: event.target.value,
                            }))
                          }
                          maxLength={100}
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="identidad-email">Correo</label>
                        <input
                          id="identidad-email"
                          type="email"
                          value={nuevaIdentidad.email}
                          onChange={(event) =>
                            setNuevaIdentidad((prev) => ({
                              ...prev,
                              email: event.target.value,
                            }))
                          }
                          required
                        />
                      </div>

                      <div className="form-field">
                        <label htmlFor="identidad-rol">Rol</label>
                        <select
                          id="identidad-rol"
                          value={nuevaIdentidad.rol}
                          onChange={(event) =>
                            setNuevaIdentidad((prev) => ({
                              ...prev,
                              rol: event.target.value,
                            }))
                          }
                        >
                          {ROLES_LIDER.map((rol) => (
                            <option key={rol} value={rol}>
                              {rol}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="form-field form-field-full">
                        <label htmlFor="identidad-compania">Compañía</label>
                        <select
                          id="identidad-compania"
                          value={nuevaIdentidad.compania_id}
                          onChange={(event) =>
                            setNuevaIdentidad((prev) => ({
                              ...prev,
                              compania_id: event.target.value,
                            }))
                          }
                          required
                        >
                          {companias.length !== 1 && (
                            <option value="">Seleccione una compañía</option>
                          )}
                          {companias.map((compania) => (
                            <option key={compania.id} value={compania.id}>
                              {compania.codigo} — {compania.nombre}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="identity-modal-actions">
                      <button
                        type="button"
                        className="secondary-action-button"
                        onClick={() => setMostrarNuevaIdentidad(false)}
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="primary-action-button"
                        disabled={cargandoVista}
                      >
                        Crear identidad
                      </button>
                    </div>
                  </form>
                </section>
              </div>
            )}
          </main>
        </div>
      </div>
    )
  }

  // =========================================================
  // LOGIN
  // =========================================================
  return (
    <div className="app">
      <main className="login-page">
        <section className="brand-panel">
          <div className="brand-content">
            <div className="logo-mark">IAM</div>
            <h1>IAM Secure</h1>
            <p className="brand-subtitle">
              Plataforma de Gestión de Identidades y Accesos
            </p>

            <div className="security-message">
              <span className="shield">✓</span>
              <div>
                <strong>Acceso seguro</strong>
                <p>
                  Gestión centralizada con RBAC, mínimo privilegio y aislamiento
                  multitenant.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="login-panel">
          <div className="login-card">
            <div className="login-heading">
              <span className="eyebrow">IAM SECURE PLATFORM</span>
              <h2>Iniciar sesión</h2>
              <p>Ingrese sus credenciales para acceder a la plataforma.</p>
            </div>

            <form className="login-form" onSubmit={iniciarSesion}>
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="usuario@empresa.com"
                autoComplete="username"
                required
              />

              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Ingrese su contraseña"
                autoComplete="current-password"
                required
              />

              {error && (
                <div className="error-message" role="alert">
                  {error}
                </div>
              )}

              <button
                className="login-button"
                type="submit"
                disabled={cargando}
              >
                {cargando ? 'Validando...' : 'Iniciar sesión'}
              </button>
            </form>

            <p className="login-footer">
              Acceso exclusivo para usuarios autorizados.
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App


// =========================================================
