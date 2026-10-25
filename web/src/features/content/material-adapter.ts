import type { VersionView } from "../../client"
import type { MaterialItem } from "./ContentWorkspace"

export function materialItem(version: VersionView, libraryLabel: string): MaterialItem {
  const binding = version.binding, review = binding?.review
  const publication = binding?.active_publication?.active ? "published"
    : review?.state === "approved" ? "approved" : review?.state === "submitted" ? "submitted" : review?.state === "rejected" ? "rejected" : "unpublished"
  return { versionId: version.version_id, targetLibraryId: binding?.target_library_id || version.library_id, title: version.title,
    originalName: version.original_name, libraryLabel, versionNo: version.version_no, extraction: version.extraction_state, publication,
    actions: { preview: !!version.actions?.preview, download: !!version.actions?.download, edit: !!version.actions?.edit_material && version.material_revision != null,
      submit: !!version.actions?.submit_review, review: !!review?.can_decide, publish: !!review?.can_publish } }
}
export function locatorLabel(locator: Record<string, unknown>): string {
  const labels: string[] = []
  for (const [key, label] of [["page", "页"], ["slide", "张幻灯片"], ["paragraph", "段"]]) {
    const value = locator[key]
    if (typeof value === "number" || typeof value === "string") labels.push(`第 ${value} ${label}`)
  }
  return labels.join(" · ") || "原文定位"
}
