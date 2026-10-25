import type { SourceMetadata } from "../../client"
import { Field } from "../../components/labconnect"

export function SourceFields({ value, onChange, disabled = false }: { value: SourceMetadata; onChange: (value: SourceMetadata) => void; disabled?: boolean }) {
  return <fieldset disabled={disabled} className="lc-material-source"><legend>来源与许可</legend>
    <Field label="原作者"><input value={value.author || ""} maxLength={200} onChange={e => onChange({ ...value, author: e.target.value || null })} /></Field>
    <Field label="来源链接" hint="选填，不含账号密码的 HTTPS 地址。"><input type="url" pattern="https://.*" value={value.original_url || ""} maxLength={1000} onChange={e => onChange({ ...value, original_url: e.target.value || null })} /></Field>
    <Field label="许可名称"><input value={value.license || ""} maxLength={200} onChange={e => onChange({ ...value, license: e.target.value || null })} /></Field>
    <Field label="许可链接"><input type="url" pattern="https://.*" value={value.license_url || ""} maxLength={1000} onChange={e => onChange({ ...value, license_url: e.target.value || null })} /></Field>
    <Field label="获取日期"><input type="date" value={value.acquired_date || ""} onChange={e => onChange({ ...value, acquired_date: e.target.value || null })} /></Field>
    <Field label="原文版本"><input value={value.source_version || ""} maxLength={200} onChange={e => onChange({ ...value, source_version: e.target.value || null })} /></Field>
    <label className="lc-material-check"><input type="checkbox" checked={!!value.adapted} onChange={e => onChange({ ...value, adapted: e.target.checked })} />本资料经过翻译或改编</label>
    <label className="lc-material-check"><input type="checkbox" checked={!!value.public_reuse_allowed} onChange={e => onChange({ ...value, public_reuse_allowed: e.target.checked })} />已核对许可允许向公共范围复用</label>
  </fieldset>
}
