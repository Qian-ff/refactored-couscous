import { PageContainer, StatePanel } from "../../components/labconnect"
import type { PageRegistration } from "../../lib/extensions"

export function ContentPage() {
  return <PageContainer title="资料中心" description="授权资料检索、定位预览和原件下载。"><StatePanel kind="unavailable" title="资料接口尚未接通" description="当前服务尚未发布资料接口。上传、审核、发布和下载将随真实接口接入；现有账号和课程功能可继续使用。" /></PageContainer>
}
export const contentPages: readonly PageRegistration[] = [
  { id: "d-content-materials", path: "/content/materials", title: "资料中心", workRoles: ["student", "teacher", "administrator"], component: ContentPage, navGroup: "content" },
]
