import type { PageRegistration } from "../../lib/extensions"
import { ClassManagementPage } from "../teaching/ClassManagementPage"
import { CoursesPage } from "../teaching/CoursesPage"
import { AccountsPage } from "./AccountsPage"
import { InvitationsPage } from "./InvitationsPage"
import { OrganizationsPage } from "./OrganizationsPage"

export const adminPages: PageRegistration[] = [
  { id: "b1-admin-courses", path: "/administration/courses", title: "课程与教学班", workRoles: ["administrator"], component: CoursesPage, navGroup: "courses" },
  { id: "b1-organizations", path: "/administration/organizations", title: "组织管理", workRoles: ["administrator"], component: OrganizationsPage, navGroup: "administration" },
  { id: "b1-accounts", path: "/administration/accounts", title: "账号与授权", workRoles: ["administrator"], component: AccountsPage, navGroup: "administration" },
  { id: "b1-account-invitations", path: "/administration/invitations", title: "学生账号邀请", workRoles: ["administrator"], component: InvitationsPage, navGroup: "administration" },
  { id: "b1-admin-class", path: "/administration/classes/:courseId", title: "教学班管理", workRoles: ["administrator"], component: ClassManagementPage },
]
