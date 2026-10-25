import type { VersionView } from "../../client"
import type { MaterialItem } from "./ContentWorkspace"

export function materialItem(version: VersionView, libraryLabel: string): MaterialItem {
  const binding = version.binding, review = binding?.review
  const publication = binding?.active_publication?.active ? "published"
    : review?.state === "approved" ? "approved" : review?.state === "submitted" ? "submitted" : review?.state === "rejected" ? "rejected" : "unpublished"
  return { versionId: version.version_id, targetLibraryId: binding?.target_library_id || version.library_id, title: version.title,
    originalName: version.original_name, libraryLabel, versionNo: version.version_no, extraction: version.extraction_state, publication,
    snippet: version.search_match?.snippet,
    locatorLabel: version.search_match?.kind === "chunk" && version.search_match.chunk_id && version.search_match.locator ? locatorLabel(version.search_match.locator)
      : version.search_match ? ({ title: "标题命中 · 无页段定位", filename: "文件名命中 · 无页段定位", input_text: "输入知识点文字命中 · 无页段定位", chunk: "正文命中 · 定位不可用" })[version.search_match.kind] : undefined,
    actions: { preview: !!version.actions?.preview, download: !!version.actions?.download, edit: !!version.actions?.edit_material && version.material_revision != null,
      submit: !!version.actions?.submit_review, review: !!review?.can_decide, publish: !!review?.can_publish } }
}
export function locatorLabel(locator: Record<string, unknown>): string {
  const labels: string[] = []
  const kindLabel = ({ page: "页", slide: "张幻灯片", paragraph: "段" } as Record<string, string>)[String(locator.kind)]
  if (kindLabel && typeof locator.position === "number") {
    labels.push(`第 ${locator.position} ${kindLabel}`)
    if (typeof locator.part === "number") labels.push(`分片 ${locator.part}`)
    return labels.join(" · ")
  }
  for (const [key, label] of [["page", "页"], ["slide", "张幻灯片"], ["paragraph", "段"]]) {
    const value = locator[key]
    if (typeof value === "number" || typeof value === "string") labels.push(`第 ${value} ${label}`)
  }
  return labels.join(" · ") || "原文定位"
}
