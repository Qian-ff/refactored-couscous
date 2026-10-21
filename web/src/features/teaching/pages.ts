import type { PageRegistration } from "../../lib/extensions"
import { ClassManagementPage } from "./ClassManagementPage"

export const teachingPages: PageRegistration[] = [
  { id: "b1-teacher-class", path: "/teaching/classes/:courseId", title: "教学班管理", workRoles: ["teacher"], component: ClassManagementPage },
]
