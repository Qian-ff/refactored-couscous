import { useCallback, useState } from "react"
import { ManagementService, type AccountView, type CatalogView, type Role } from "../../client"
import type { PageProps } from "../../lib/extensions"
import { useBusinessQuery } from "../teaching/ui"

export function isPlatform(page: PageProps) { return page.session.workRole === "administrator" && page.user.effective_grants.some(g => g.role === "platform_admin") }
export function isSchoolManager(page: PageProps) { return isPlatform(page) || (page.session.workRole === "administrator" && page.user.effective_grants.some(g => g.role === "school_admin")) }
export function grantRoles(page: PageProps): Role[] {
  return isPlatform(page) ? ["student", "teacher", "college_admin", "school_admin"] : isSchoolManager(page) ? ["student", "teacher", "college_admin"] : ["student", "teacher"]
}
export function canManageAccount(page: PageProps, target: AccountView) {
  if (page.session.workRole !== "administrator" || target.id === page.user.id || target.grants.some(g => g.role === "platform_admin")) return false
  return isPlatform(page) || !target.grants.some(g => g.role === "school_admin" || (!isSchoolManager(page) && g.role === "college_admin"))
}
export function canManageCatalog(page: PageProps, target: CatalogView) {
  if (page.session.workRole === "teacher") return target.owner_id === page.user.id && target.school_id === page.user.school?.id
  return isPlatform(page) || (target.school_id === page.user.school?.id && page.user.effective_grants.some(g => g.role === "school_admin" || (g.role === "college_admin" && g.college_id === target.college_id)))
}
export function useOrganizationChoices(page: PageProps) {
  const [selectedSchool, setSchool] = useState("")
  const [selectedCollege, setCollege] = useState("")
  const admin = page.session.workRole === "administrator"
  const schools = useBusinessQuery(page.session, useCallback(async signal => (await ManagementService.listSchools({ query: { limit: 100 }, signal })).data, []), admin)
  const schoolId = selectedSchool || page.user.school?.id || schools.data?.data[0]?.id || ""
  const colleges = useBusinessQuery(page.session, useCallback(async signal => (await ManagementService.listColleges({ query: { school_id: schoolId, limit: 100 }, signal })).data, [schoolId]), admin && Boolean(schoolId))
  const collegeId = selectedCollege || colleges.data?.data.find(value => value.id === page.user.college?.id)?.id || colleges.data?.data[0]?.id || ""
  const majors = useBusinessQuery(page.session, useCallback(async signal => (await ManagementService.listMajors({ query: { college_id: collegeId, limit: 100 }, signal })).data, [collegeId]), admin && Boolean(collegeId))
  return { schools, colleges, majors, schoolId, collegeId,
    selectSchool: (id: string) => { setSchool(id); setCollege("") }, selectCollege: setCollege,
    reload: () => { schools.reload(); colleges.reload(); majors.reload() } }
}
