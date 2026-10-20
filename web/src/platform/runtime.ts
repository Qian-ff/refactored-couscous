// F owns platform-specific behavior; secrets and authorization stay in the shared backend.
export const allowLocalHttp = import.meta.env.DEV || import.meta.env.MODE === 'debug'
export function defaultServiceUrl() {
  if (!allowLocalHttp) return ''
  return /Android/i.test(navigator.userAgent) ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000'
}
