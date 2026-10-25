"""Material source IDs are validated against real authorized versions and immutable chunks."""
from dataclasses import dataclass

from fastapi import HTTPException

from app.domains.content.access import require_version as require_material
from app.domains.content.models import Library, Material, MaterialVersion, SourceChunk


@dataclass(frozen=True)
class SourceSnapshot:
    material_version_id: object
    chunk_id: object
    locator: dict
    school_id: object
    provenance: dict


def resolve_sources(db, identity, pointers):
    result = []
    for pointer in pointers:
        version, material, _projection = require_material(db, identity, pointer.material_version_id)
        if version.extraction_state != "succeeded":
            raise HTTPException(409, "来源资料尚无成功固定快照")
        source = db.get(Library, material.library_id)
        locator = {}
        if pointer.chunk_id is not None:
            chunk = db.get(SourceChunk, pointer.chunk_id)
            if chunk is None or chunk.material_version_id != version.id:
                raise HTTPException(403, "来源页段与版本不匹配")
            locator = dict(chunk.locator)
        result.append(SourceSnapshot(version.id, pointer.chunk_id, locator, source.school_id, version.source_metadata))
    return result


def retained_sources(db, rows):
    """Internal provenance validation, not a material read grant or a public DTO."""
    result = []
    for row in rows:
        version = db.get(MaterialVersion, row.material_version_id)
        if version is None or version.extraction_state != "succeeded":
            raise HTTPException(409, "固定来源快照不可用")
        material = db.get(Material, version.material_id)
        library = db.get(Library, material.library_id)
        locator = {}
        if row.chunk_id is not None:
            chunk = db.get(SourceChunk, row.chunk_id)
            if chunk is None or chunk.material_version_id != version.id:
                raise HTTPException(409, "固定来源页段不匹配")
            locator = dict(chunk.locator)
        if hasattr(row, "locator") and row.locator != locator:
            raise HTTPException(409, "固定来源定位指纹不匹配")
        result.append(SourceSnapshot(version.id, row.chunk_id, locator, library.school_id, version.source_metadata))
    return result


def check_publication(provenance, source_library, target_library, statement, sources=(), *, reusing=False,
                      public_origin=False, public_source_ids=frozenset()):
    if not statement.strip():
        raise HTTPException(422, "须声明本次教学使用和共享授权")
    if (source_library.school_id is not None and target_library.school_id is not None
            and source_library.school_id != target_library.school_id and not public_origin):
        raise HTTPException(403, "学校私库不能直接跨校共享")
    for ref in sources:
        public_ref = (ref.material_version_id, ref.chunk_id) in public_source_ids
        if public_ref and not (ref.provenance.get("public_reuse_allowed") is True and ref.provenance.get("license")
                               and ref.provenance.get("license_url")):
            raise HTTPException(409, "保留公共来源缺少明确公开许可")
        if ref.school_id is not None and target_library.school_id is not None and ref.school_id != target_library.school_id and not (public_origin or public_ref):
            raise HTTPException(403, "不能通过引用穿透学校私库")
    if reusing and not (provenance.get("license") and (
            provenance.get("teaching_reuse_allowed") is True or provenance.get("public_reuse_allowed") is True)):
        raise HTTPException(409, "来源没有明确的教学复用许可")
    if target_library.scope == "platform_public" or public_origin:
        for metadata in (provenance, *(ref.provenance for ref in sources)):
            if not (metadata.get("public_reuse_allowed") is True and metadata.get("license") and metadata.get("license_url")):
                raise HTTPException(409, "公开复用须有明确许可和许可来源")
