import axios from "axios"
import { client } from "../client/client.gen"
import { allowLocalHttp, defaultServiceUrl } from "../platform/runtime"

let token: string | undefined

export function serviceUrl() {
  return localStorage.getItem("safelab.service") || defaultServiceUrl()
}

export function configureService(value: string) {
  const url = new URL(value)
  if (url.username || url.password || url.search || url.hash || !["http:", "https:"].includes(url.protocol)) {
    throw new Error("请输入不含账号、密码或查询参数的服务地址")
  }
  if (url.protocol !== "https:" && !(allowLocalHttp && ["localhost", "127.0.0.1", "10.0.2.2"].includes(url.hostname))) {
    throw new Error("请使用 HTTPS 服务地址；本机 HTTP 仅供调试版本使用")
  }
  const valueNormalized = url.toString().replace(/\/$/, "")
  localStorage.setItem("safelab.service", valueNormalized)
  client.setConfig({ baseURL: valueNormalized, auth: () => token })
}

export function setToken(value?: string) {
  token = value // Session credentials stay in memory; reload requires login.
  client.setConfig({ auth: () => token })
}

export function message(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === "string") return detail
    if (error.response?.status === 422) return "输入格式不正确，请检查后重试"
    if (!error.response) return "无法连接服务，请检查服务地址和网络后重试"
    return `请求未完成（${error.response.status}），请重试`
  }
  return error instanceof Error ? error.message : "操作未完成，请重试"
}
