import { useCallback, useState } from "react"
import axios from "axios"
import { TeachingService, type RequestView } from "../../client"
import { Button, Dialog, Notice, PageContainer, Pagination, Panel, RecordList, StatePanel } from "../../components/labconnect"
import { useCommand, useResource } from "../../components/labconnect/hooks"
import { dateLabel, JoinClassDialog, enrollmentMessage, requestStatus } from "./enrollment-ui"

export function EnrollmentRequestsPage() {
  const [offset, setOffset] = useState(0), [reload, setReload] = useState(0), [joining, setJoining] = useState(false)
  const [selected, setSelected] = useState<RequestView>(), [notice, setNotice] = useState(""), [conflict, setConflict] = useState(false)
  const size = 20
  const resource = useResource(useCallback(async (signal: AbortSignal) => (await TeachingService.myRequests({ query: { offset, limit: size }, signal })).data, [offset, reload]))
  const action = useCommand()
  const refresh = () => { setReload(value => value + 1); setSelected(undefined) }
  return <div className="lc-student-enrollment-workspace"><PageContainer title="班级申请与历史" description="本人加入和退出申请由教师审批。申请结果与当前在班关系分别确认。"
    actions={<><Button variant="secondary" onClick={refresh} pending={resource.loading}>刷新申请状态</Button><Button onClick={() => setJoining(true)}>使用班级邀请码加入</Button></>}>
    {notice && <Notice kind="success">{notice}</Notice>}{conflict && <Notice kind="warning">申请状态已变化，已重新读取。请核对教师处理结果。</Notice>}
    <Panel title="本人班级申请"><p>“加入已批准”记录不代表现在仍在班；退出、移出或归档后的权限以当前关系为准。</p>
      {resource.loading ? <StatePanel kind="loading" /> : resource.error ? <StatePanel kind="error" description={resource.error} retry={refresh} /> : resource.data && <>
        {resource.data.data.length ? <RecordList items={resource.data.data} itemKey={row => row.id} title={row => row.kind === "join" ? "加入教学班申请" : row.kind === "leave" ? "退出教学班申请" : "班级申请"}
          fields={[{ label: "教学班编号", value: row => row.course_id }, { label: "处理状态", value: row => requestStatus[row.status] || "状态需核对" }, { label: "申请时间", value: row => dateLabel(row.created_at) }, { label: "处理时间", value: row => dateLabel(row.decided_at) }]}
          actions={row => row.status === "pending" ? <Button variant="secondary" onClick={() => { setSelected(row); action.clear(); setConflict(false) }}>撤销申请</Button> : <span className="lc-enrollment-readonly">已处理记录，只读保留</span>} />
          : <StatePanel kind="empty" title="暂无本人班级申请" description="直接加入或直接退出不一定产生审批申请。" />}
        <Pagination total={resource.data.count} offset={offset} pageSize={size} onChange={setOffset} />
      </>}
    </Panel>
    <Panel title="本人班级关系历史"><StatePanel kind="unavailable" title="关系历史待接入" description="当前接口仅提供申请记录，尚不能查询完整退出、移出和归档关系；申请记录不会被当作当前权限凭据。" /></Panel>
    {joining && <JoinClassDialog onClose={() => setJoining(false)} onConfirmed={result => { setJoining(false); setNotice(enrollmentMessage(result)); refresh() }} />}
    {selected && <Dialog title="撤销待处理申请" busy={action.pending} onClose={() => setSelected(undefined)}><p>撤销本次{selected.kind === "leave" ? "退出" : "加入"}申请？已处理的申请不能撤销。</p>
      <p className="lc-enrollment-code">教学班编号：{selected.course_id}</p>{action.error && <Notice kind="error">{action.error}。结果未确认时可重试原请求。</Notice>}
      <div className="lc-actions"><Button variant="secondary" disabled={action.pending} onClick={() => setSelected(undefined)}>保留申请</Button><Button pending={action.pending} onClick={async () => {
        const response = await action.run("cancel:" + selected.id, async key => {
          try { return await TeachingService.cancelMyRequest({ path: { request_id: selected.id }, headers: { "Idempotency-Key": key } }) }
          catch (reason) { if (axios.isAxiosError(reason) && reason.response?.status === 409) { setConflict(true); refresh() } throw reason }
        })
        if (response) { setNotice("服务端已确认撤销申请。"); refresh() }
      }}>确认撤销申请</Button></div></Dialog>}
  </PageContainer></div>
}
