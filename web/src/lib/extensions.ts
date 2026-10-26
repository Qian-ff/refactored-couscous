import type { ComponentType, ReactNode } from "react"
import type { UserPublic, TeacherLessonPreview } from "../client"
import type { SessionSnapshot, WorkRole } from "./api"
import type { ContentRef } from "./lesson-protocol"

/** A-owned integration protocol. D implements the router and supplies these parameters. */
export type PageProps = Readonly<{
  user: UserPublic
  session: SessionSnapshot
  params: Readonly<Record<string, string | undefined>>
  navigate: (path: string, options?: { replace?: boolean }) => void
  platform: PlatformBridge
}>
export type PageRegistration = Readonly<{
  id: string
  path: string
  title: string
  workRoles: readonly WorkRole[]
  component: ComponentType<PageProps>
  navGroup?: "courses" | "learning" | "content" | "assistant" | "administration"
}>
export type LessonEditorProps = PageProps & {
  renderPreview: (preview: TeacherLessonPreview) => ReactNode
}
export type PermissionState = "granted" | "denied" | "unavailable" | "prompt"
export type RecordedAudio = Readonly<{
  blob: Blob
  format: "wav-pcm16"
  sampleRate: 16000
  channels: 1
  durationMs: number
}>
/** Implemented adapters arrive in C/D/A/F; declarations do not imply native recording works. */
export type PlatformBridge = Readonly<{
  kind: "web" | "windows" | "android"
  microphonePermission: () => Promise<PermissionState>
  startRecording: () => Promise<void>
  stopRecording: () => Promise<RecordedAudio>
  cancelRecording: () => Promise<void>
  speak: (text: string, language: "zh-CN") => Promise<void>
  stopSpeaking: () => void
  openCitation: (reference: ContentRef) => Promise<void>
  downloadMaterial: (materialId: string, versionId: string) => Promise<void>
}>
