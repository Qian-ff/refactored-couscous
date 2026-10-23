import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { isStaleRequest, message, sessionSnapshot, subscribeSession } from "../../lib/api"

export function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T>(), [error, setError] = useState(""), [loading, setLoading] = useState(true), [revision, setRevision] = useState(0)
  const [status, setStatus] = useState<number>()
  useEffect(() => {
    const controller = new AbortController(), generation = sessionSnapshot().generation
    const unsubscribe = subscribeSession(s => { if (s.generation !== generation) controller.abort() })
    setData(undefined); setError(""); setStatus(undefined); setLoading(true)
    load(controller.signal).then(value => { if (!controller.signal.aborted && generation === sessionSnapshot().generation) setData(value) })
      .catch(reason => { if (!controller.signal.aborted && !isStaleRequest(reason)) { setError(message(reason)); setStatus(axios.isAxiosError(reason) ? reason.response?.status : undefined) } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { controller.abort(); unsubscribe() }
  }, [load, revision])
  return { data, error, status, loading, reload: () => setRevision(x => x + 1) }
}
/** Retain keys only for uncertain transport failures; payloads never leave memory. */
export function useCommand() {
  const [pending, setPending] = useState(false), [error, setError] = useState("")
  const busy = useRef(false), uncertain = useRef<{ signature: string; key: string } | undefined>(undefined)
  async function run<T>(signature: string, action: (key: string) => Promise<T>): Promise<T | undefined> {
    if (busy.current) return
    busy.current = true; setPending(true); setError("")
    const generation = sessionSnapshot().generation
    const key = uncertain.current?.signature === signature ? uncertain.current.key : crypto.randomUUID()
    uncertain.current = { signature, key }
    try {
      const result = await action(key)
      if (generation !== sessionSnapshot().generation) return
      uncertain.current = undefined
      return result
    } catch (reason) {
      if (axios.isAxiosError(reason) && reason.response && reason.response.status >= 400 && reason.response.status < 500) uncertain.current = undefined
      if (generation === sessionSnapshot().generation && !isStaleRequest(reason)) setError(message(reason))
    } finally { busy.current = false; if (generation === sessionSnapshot().generation) setPending(false) }
  }
  return { run, pending, error, clear: () => setError("") }
}
