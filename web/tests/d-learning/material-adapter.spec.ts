import { expect, test } from "@playwright/test"
import type { VersionView } from "../../src/client"
import { locatorLabel, materialItem } from "../../src/features/content/material-adapter"

function version(): VersionView {
  return { material_id: "material", version_id: "version", library_id: "target-a", title: "合成资料", version_no: 1, input_kind: "file", extraction_state: "succeeded", original_name: "合成.pdf", file_bytes: 10,
    content_hash: "a".repeat(64), parser_version: "fixture", created_at: "2026-10-25T00:00:00Z", warnings: [], warning_hash: "b".repeat(64), material_revision: 4,
    actions: { edit_material: true, submit_review: true, preview: true, download: true }, binding: { target_library_id: "target-a" } }
}
test("同一版本按精确目标分别映射发布与待审核，不串用动作", () => {
  const a = version(), b = version()
  a.binding = { target_library_id: "target-a", active_publication: { id: "pub-a", version_id: "version", target_library_id: "target-a", review_id: "review-a", active: true, revision: 3, published_at: "2026-10-25T00:00:00Z", retired_at: null } }
  b.library_id = "target-b"
  b.binding = { target_library_id: "target-b", review: { id: "review-b", version_id: "version", target_library_id: "target-b", state: "submitted", revision: 5, warning_hash: "c".repeat(64), original_authorized: false, authorization_statement: "合成说明", reason: null, submitted_at: "2026-10-25T00:00:00Z", decided_at: null, can_decide: true, can_publish: false } }
  expect(materialItem(a, "A")).toMatchObject({ targetLibraryId: "target-a", publication: "published", actions: { review: false, publish: false } })
  expect(materialItem(b, "B")).toMatchObject({ targetLibraryId: "target-b", publication: "submitted", actions: { review: true, publish: false } })
})
test("解析成功和提交权不推断发布、编辑或审核权限", () => {
  const row = version(); row.material_revision = null; row.actions = { submit_review: true, edit_material: true, preview: true, download: false }
  expect(materialItem(row, "范围")).toMatchObject({ publication: "unpublished", actions: { edit: false, submit: true, review: false, publish: false, download: false } })
})
test("页段定位仅呈现标量字段，不拼接HTML", () => {
  expect(locatorLabel({ page: 3, paragraph: 2 })).toBe("第 3 页 · 第 2 段")
  expect(locatorLabel({ kind: "paragraph", position: 2, part: 1 })).toBe("第 2 段 · 分片 1")
  expect(locatorLabel({ page: { html: "untrusted" } })).toBe("原文定位")
})
test("仅chunk命中携带页段，输入文字、标题与文件名命中不造定位", () => {
  const row = version()
  row.search_match = { kind: "chunk", snippet: "真实正文片段", chunk_id: "chunk-2", ordinal: 2, locator: { kind: "paragraph", position: 2, part: 1 } }
  expect(materialItem(row, "范围")).toMatchObject({ snippet: "真实正文片段", locatorLabel: "第 2 段 · 分片 1" })
  for (const kind of ["input_text", "title", "filename"] as const) {
    row.search_match = { kind, snippet: "实际匹配片段", locator: { kind: "paragraph", position: 999 } }
    expect(materialItem(row, "范围").locatorLabel).toContain("无页段定位")
    expect(materialItem(row, "范围").locatorLabel).not.toContain("999")
  }
})
