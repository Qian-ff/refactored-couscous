import { useCallback, useState } from "react"
import { Link } from "react-router"
import axios from "axios"
import { TeachingService, type SelfEnrollmentView, type SelfRequestView, type EnrollmentResult } from "../../client"
import { Button, Dialog, Field, Notice, PageContainer, Pagination, Panel, RecordList, SearchFilters, StatePanel } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import { dateLabel, JoinClassDialog, enrollmentMessage, requestStatus } from "./enrollment-ui"

export function EnrollmentRequestsPage() {
  const [offset, setOffset] = useState(0), [reload, setReload] = useState(0), [joining, setJoining] = useState(false)
  const [selected, setSelected] = useState<SelfRequestView>(), [notice, setNotice] = useState(""), [conflict, setConflict] = useState(false)
  const [noticeKind, setNoticeKind] = useState<"warning" | "success">("success")
  const [input, setInput] = useState(""), [query, setQuery] = useState(""), [historyOffset, setHistoryOffset] = useState(0)
  const [status, setStatus] = useState<"all" | SelfEnrollmentView["status"]>("all"), [archived, setArchived] = useState("all")
  const size = 20
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await TeachingService.myRequests({ query: { offset, limit: size }, signal })).data, [offset, reload]))
  const history = useResource(useCallback(async (signal: AbortSignal) => (await TeachingService.myEnrollments({ query: {
    q: query, status, archived: archived === "all" ? undefined : archived === "archived", offset: historyOffset, limit: size,
  }, signal })).data, [query, status, archived, historyOffset, reload]))
  const action = useCommand()
  const refresh = () => { setReload(value => value + 1); setSelected(undefined) }
  function joined(result: EnrollmentResult) {
    setJoining(false); setNotice(enrollmentMessage(result)); setNoticeKind(result.status.startsWith("pending_") ? "warning" : "success"); refresh()
  }
  return <div className="lc-student-enrollment-workspace"><PageContainer title="班级申请与历史" description="查看本人的审批记录和班级关系，核对最新处理结果。"
    actions={<><Button variant="secondary" onClick={() => { setNotice(""); setConflict(false); refresh() }} pending={resource.loading || history.loading}>刷新申请状态与关系</Button><Button onClick={() => setJoining(true)}>使用班级邀请码加入</Button></>}>
    {notice && <Notice kind={noticeKind}>{notice}</Notice>}{conflict && <Notice kind="warning">申请状态已变化，已重新读取。请核对教师处理结果。</Notice>}
    <div role="region" aria-label="本人班级申请"><Panel title="本人班级申请"><p>“加入已批准”记录不代表现在仍在班；退出、移出或归档后的权限以当前关系为准。</p>
      {resource.loading ? <StatePanel kind="loading" /> : resource.error ? <StatePanel kind="error" description={resource.error} retry={refresh} /> : resource.data && <>
        {resource.data.data.length ? <RecordList items={resource.data.data} itemKey={row => row.id} title={row => row.kind === "join" ? "加入教学班申请" : row.kind === "leave" ? "退出教学班申请" : "班级申请"}
          fields={[{ label: "教学班", value: row => row.course_title }, { label: "班级代码", value: row => row.course_code }, { label: "处理状态", value: row => requestStatus[row.status] || "状态需核对" }, { label: "班级状态", value: row => row.course_archived ? "已归档" : "未归档" }, { label: "申请时间", value: row => dateLabel(row.created_at) }, { label: "处理时间", value: row => dateLabel(row.decided_at) }]}
          actions={row => row.status === "pending" ? <Button variant="secondary" onClick={() => { setSelected(row); action.clear(); setConflict(false) }}>撤销申请</Button> : <span className="lc-enrollment-readonly">已处理记录，只读保留</span>} />
          : <StatePanel kind="empty" title="暂无本人班级申请" description="直接加入或直接退出不一定产生审批申请。" />}
        <Pagination total={resource.data.count} offset={offset} pageSize={size} onChange={setOffset} />
      </>}
    </Panel></div>
    <div role="region" aria-label="本人班级关系历史" className="lc-enrollment-records"><Panel title="本人班级关系历史">
      <p>按班级查看本人最新关系，包括已退出、被移出及归档班级。重新加入会更新同一关系；这里不逐次记录加退班事件，班级名称以当前名称为准。</p>
      <SearchFilters value={input} onChange={setInput} label="搜索本人班级关系" placeholder="班级名称或代码" pending={history.loading}
        onSearch={() => { setQuery(input.trim()); setHistoryOffset(0) }} onClear={() => { setInput(""); setQuery(""); setStatus("all"); setArchived("all"); setHistoryOffset(0); history.reload() }}>
        <Field label="关系状态"><select value={status} onChange={event => { setStatus(event.target.value as typeof status); setHistoryOffset(0) }}>
          <option value="all">全部关系</option><option value="active">在班</option><option value="withdrawn">已退出</option><option value="removed">已移出</option>
        </select></Field>
        <Field label="班级归档情况"><select value={archived} onChange={event => { setArchived(event.target.value); setHistoryOffset(0) }}>
          <option value="all">全部班级</option><option value="current">未归档</option><option value="archived">已归档</option>
        </select></Field>
      </SearchFilters>
      {history.loading ? <StatePanel kind="loading" /> : history.error ? <StatePanel kind="error" description={history.error} retry={history.reload} /> : history.data && <>
        {history.data.data.length ? <RecordList items={history.data.data} itemKey={row => row.enrollment_id} title={row => row.course_title}
          fields={[{ label: "班级代码", value: row => row.course_code }, { label: "关系状态", value: row => ({ active: "在班", withdrawn: "已退出", removed: "已移出" })[row.status] },
            { label: "班级状态", value: row => row.course_archived ? "已归档" : "未归档" }]}
          actions={row => row.status === "active" && !row.course_archived ? <Link className="lc-button lc-secondary" to={`/student/courses/${row.course_id}`}>查看当前班级</Link>
            : <span className="lc-enrollment-readonly">{row.course_archived ? "班级已归档" : "已无当前在班关系"}，仅保留本人关系记录。</span>} />
          : <StatePanel kind="empty" title={query || status !== "all" || archived !== "all" ? "没有匹配的本人班级关系" : "暂无本人班级关系"} description="待审批的加入申请不等于在班关系，可在上方查看审批记录。" />}
        <Pagination total={history.data.count} offset={historyOffset} pageSize={size} onChange={setHistoryOffset} />
      </>}
    </Panel></div>
    {joining && <JoinClassDialog onClose={() => setJoining(false)} onConfirmed={joined} />}
    {selected && <Dialog title="撤销待处理申请" busy={action.pending} onClose={() => setSelected(undefined)}><p>撤销本次{selected.kind === "leave" ? "退出" : "加入"}申请？已处理的申请不能撤销。</p>
      <p className="lc-enrollment-code">教学班：{selected.course_title}（{selected.course_code}）</p>{action.error && <Notice kind="error">{action.error}。结果未确认时可重试原请求。</Notice>}
      <div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={() => setSelected(undefined)}>保留申请</Button><Button pending={action.pending} onClick={async () => {
        const response = await action.run("cancel:" + selected.id, async key => {
          try { return await TeachingService.cancelMyRequest({ path: { request_id: selected.id }, headers: { "Idempotency-Key": key } }) }
          catch (reason) { if (axios.isAxiosError(reason) && reason.response?.status === 409) { setConflict(true); refresh() } throw reason }
        })
        if (response) { setNotice("服务端已确认撤销申请。"); setNoticeKind("success"); refresh() }
      }}>确认撤销申请</Button></div></Dialog>}
  </PageContainer></div>
}
