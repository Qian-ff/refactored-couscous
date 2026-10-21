import { useSyncExternalStore } from "react"
import { HashRouter } from "react-router"
import { sessionSnapshot, subscribeSession } from "./lib/api"
import { AccountEntry, PasswordPage } from "./components/labconnect/AccountEntry"
import { ApplicationShell } from "./routes/ApplicationShell"

export default function App() {
  const session = useSyncExternalStore(subscribeSession, sessionSnapshot)
  return <HashRouter>{session.phase === "ready" && session.user
    ? session.user.must_change_password
      ? <PasswordPage key={session.generation} forced />
      : <ApplicationShell key={session.generation} session={session} />
    : <AccountEntry key={session.generation} phase={session.phase} />}</HashRouter>
}
