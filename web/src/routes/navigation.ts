export const navigation = [
  { key: "courses", label: "我的课程", available: true },
  { key: "learning", label: "安全闯关", available: false },
  { key: "assistant", label: "学习助手", available: false },
  { key: "records", label: "培训记录", available: false },
] as const

export const roleNames: Record<string, string> = {
  platform_admin: "平台运维", school_admin: "学校管理员", college_admin: "学院管理员",
  teacher: "教师", student: "学生",
}
