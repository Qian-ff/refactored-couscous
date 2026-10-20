/** A0 design DTOs. No lesson HTTP endpoint exists until B/C deliver and A exports it. */
export const LESSON_SCHEMA = "labconnect.lesson/1" as const
export type ContentRef = Readonly<{ material_id: string; version_id: string; page?: number; paragraph?: string }>
export type Option = Readonly<{ id: string; label: string }>
export type Activity = Readonly<{ id: string; prompt: string; source_refs: readonly ContentRef[] }> & (
  | { kind: "choice"; selection: "single" | "multiple"; options: readonly Option[] }
  | { kind: "hotspot"; scene_id: string; regions: readonly { id: string; label: string; x: number; y: number; width: number; height: number }[] }
  | { kind: "order"; items: readonly Option[] }
)
export type StudentLesson = Readonly<{
  schema_version: typeof LESSON_SCHEMA
  lesson_id: string
  version_id: string
  title: string
  short_lesson: string
  required: boolean
  scene: { id: string; svg_asset_id: string; accessible_description: string }
  activities: readonly Activity[]
}>
export type TeacherLessonPreview = Readonly<{
  mode: "teacher-preview"
  lesson: StudentLesson
  review: readonly { activity_id: string; correct_ids: readonly string[]; explanation: string }[]
}>
export type ActivityAnswer = Readonly<{ activity_id: string; selected_ids: readonly string[] }>
export type LessonFeedback = Readonly<{
  lesson_version_id: string
  answer_revision: number
  accepted_at: string
  completed: boolean
  items: readonly { activity_id: string; passed: boolean; explanation?: string }[]
}>
