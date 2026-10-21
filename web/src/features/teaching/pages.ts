import type { PageRegistration } from "../../lib/extensions"
import { ClassManagementPage } from "./ClassManagementPage"
import { CoursesPage } from "./CoursesPage"

export const teachingPages: PageRegistration[] = [
  { id: "b1-teacher-courses", path: "/teaching/courses", title: "课程与教学班", workRoles: ["teacher"], component: CoursesPage, navGroup: "courses" },
  { id: "b1-teacher-class", path: "/teaching/classes/:courseId", title: "教学班管理", workRoles: ["teacher"], component: ClassManagementPage },
]
