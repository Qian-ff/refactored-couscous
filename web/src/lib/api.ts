import axios, { AxiosHeaders, CanceledError, type InternalAxiosRequestConfig } from "axios"
import { AuthService, type UserPublic } from "../client"
import { client } from "../client/client.gen"
import { allowLocalHttp, defaultServiceUrl } from "../platform/runtime"

export type WorkRole = "student" | "teacher" | "administrator"
export type SessionReason = "login" | "identity" | "logout" | "unauthorized" | "service"
export type SessionSnapshot = Readonly<{
  generation: number
  phase: "anonymous" | "ready" | "switching" | "closing"
  workRole?: WorkRole
  user?: UserPublic
  reason: SessionReason
}>

const generationHeader = "X-LabConnect-Client-Generation"
const transport = axios.create()
const pending = new Set<AbortController>()
const listeners = new Set<(snapshot: SessionSnapshot) => void>()
let token: string | undefined
let pendingRole: WorkRole | undefined
let snapshot: SessionSnapshot = Object.freeze({ generation: 0, phase: "anonymous", reason: "login" })
type GuardedConfig = InternalAxiosRequestConfig & { sessionGeneration?: number; sessionController?: AbortController }

function configureClient() {
  client.setConfig({ axios: transport, baseURL: serviceUrl(), auth: () => token,
    headers: { [generationHeader]: String(snapshot.generation) } })
}

function publish(value: Omit<SessionSnapshot, "generation">) {
  if (value.phase !== "switching") pendingRole = undefined
  snapshot = Object.freeze({ ...value, generation: snapshot.generation })
  configureClient()
  for (const listener of listeners) listener(snapshot)
}

function advance(value: Omit<SessionSnapshot, "generation">) {
  snapshot = Object.freeze({ ...value, generation: snapshot.generation + 1 })
  for (const controller of pending) controller.abort()
  pending.clear()
  publish(value)
}

function settle(config?: GuardedConfig) {
  if (config?.sessionController) pending.delete(config.sessionController)
  if (config && config.sessionGeneration !== snapshot.generation) {
    throw new CanceledError("会话已改变，请使用当前身份重新操作")
  }
}

transport.interceptors.request.use((original) => {
  const config = original as GuardedConfig
  const generation = Number(config.headers.get(generationHeader))
  config.headers.delete(generationHeader) // Local metadata never leaves the client.
  if (generation !== snapshot.generation) throw new CanceledError("旧会话请求已取消")
  if (snapshot.phase === "switching" && (!config.url?.endsWith("/auth/me") || config.headers.get("X-Work-Role") !== pendingRole)) {
    throw new CanceledError("身份正在确认，请稍候")
  }
  if (snapshot.phase === "closing" && !config.url?.endsWith("/auth/logout")) throw new CanceledError("正在退出登录")
  config.sessionGeneration = generation
  const controller = new AbortController()
  config.sessionController = controller
  pending.add(controller)
  if (config.signal?.aborted) controller.abort()
  config.signal?.addEventListener?.("abort", () => controller.abort(), { once: true })
  config.signal = controller.signal
  if (!config.headers.has("X-Work-Role") && snapshot.workRole) config.headers.set("X-Work-Role", snapshot.workRole)
  return config
})
transport.interceptors.response.use((response) => {
  settle(response.config)
  return response
}, (error: unknown) => {
  if (axios.isAxiosError(error)) {
    settle(error.config)
    if (error.response?.status === 401) {
      token = undefined
      advance({ phase: "anonymous", reason: "unauthorized" })
    }
  }
  return Promise.reject(error)
})

export function serviceUrl() {
  const configured = localStorage.getItem("safelab.service") || defaultServiceUrl()
  if (configured) return configured
  // Public production web shares the HTTPS gateway with its API. Packaged clients still select a service.
  const localHost = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname)
  return window.location.protocol === "https:" && !localHost ? window.location.origin : ""
}

export function configureService(value: string) {
  const url = new URL(value)
  if (url.username || url.password || url.search || url.hash || !["http:", "https:"].includes(url.protocol)) {
    throw new Error("请输入不含账号、密码或查询参数的服务地址")
  }
  if (url.protocol !== "https:" && !(allowLocalHttp && ["localhost", "127.0.0.1", "10.0.2.2"].includes(url.hostname))) {
    throw new Error("请使用 HTTPS 服务地址；本机 HTTP 仅供调试版本使用")
  }
  const normalized = url.toString().replace(/\/$/, "")
  const changed = normalized !== serviceUrl().replace(/\/$/, "")
  localStorage.setItem("safelab.service", normalized)
  if (changed) {
    token = undefined
    advance({ phase: "anonymous", reason: "service" })
  } else configureClient()
}

export function setToken(value?: string) {
  token = value // Session credentials stay in memory; reload requires login.
  advance({ phase: value ? "ready" : "anonymous", reason: value ? "login" : "logout" })
}

export function sessionSnapshot() { return snapshot }
export function subscribeSession(listener: (value: SessionSnapshot) => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

/** D uses this after login. The server confirms the default work identity. */
export async function confirmSession() {
  const generation = snapshot.generation
  const { data } = await AuthService.me()
  if (generation !== snapshot.generation) throw new CanceledError("登录状态已改变")
  publish({ phase: "ready", reason: "login", user: data, workRole: data.active_work_role ?? undefined })
  return data
}

/** Clear page state while switching; mount the new page only after confirmation. */
export async function switchWorkRole(role: WorkRole) {
  if (!token) throw new Error("请先登录")
  pendingRole = role
  advance({ phase: "switching", reason: "identity" })
  const generation = snapshot.generation
  try {
    const { data } = await AuthService.me({ headers: new AxiosHeaders({ "X-Work-Role": role }) })
    if (generation !== snapshot.generation) throw new CanceledError("身份确认已过期")
    if (data.active_work_role !== role) throw new Error("服务端未确认所选身份")
    publish({ phase: "ready", reason: "identity", user: data, workRole: role })
    return data
  } catch (error) {
    if (generation === snapshot.generation) {
      token = undefined
      advance({ phase: "anonymous", reason: "unauthorized" })
    }
    throw error
  }
}

export async function logoutSession() {
  advance({ phase: "closing", reason: "logout", workRole: snapshot.workRole })
  const generation = snapshot.generation
  try { await AuthService.logout() }
  finally {
    if (generation === snapshot.generation) {
      token = undefined
      advance({ phase: "anonymous", reason: "logout" })
    }
  }
}

export const isStaleRequest = axios.isCancel

export function message(error: unknown) {
  if (axios.isCancel(error)) return "会话或请求已改变，请重试当前操作"
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (error.response?.status === 422) return "输入格式不正确，请检查后重试"
    if (!error.response) return "无法连接服务，请检查服务地址和网络后重试"
    return `请求未完成（${error.response.status}），请重试`
  }
  return error instanceof Error ? error.message : "操作未完成，请重试"
}

configureClient()
