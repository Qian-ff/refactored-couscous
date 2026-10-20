export type SourceIdentity = { source_sha: string; surface: "api" | "web"; worktree_id: string; source_fingerprint: string; contract: string }
export const root: string
export const primaryRoot: string
export const webPort: number
export function sourceIdentity(surface: "api" | "web", selectedRoot?: string): SourceIdentity
export function demoAccounts(): { password: string; [key: string]: unknown }
export function requireService(url: string, expected: SourceIdentity): Promise<SourceIdentity>
