import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AttributeTemplate, MediaAsset

router = APIRouter(tags=["library"])

UPLOADS = Path(__file__).resolve().parents[2] / "data" / "uploads"
ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
MAX_BYTES = 8 * 1024 * 1024


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    fields: list[str] = []


def _template_out(row: AttributeTemplate) -> dict:
    import json

    try:
        fields = json.loads(row.fields or "[]")
    except json.JSONDecodeError:
        fields = []
    if not isinstance(fields, list):
        fields = []
    return {"id": row.id, "name": row.name, "target": row.target, "fields": [str(item) for item in fields if str(item).strip()]}


def _asset_out(row: MediaAsset) -> dict:
    return {
        "id": row.id,
        "owner_kind": row.owner_kind,
        "owner_id": row.owner_id,
        "filename": row.filename,
        "mime": row.mime,
        "note": row.note,
        "url": f"/uploads/{row.stored_name}",
        "created_at": row.created_at,
    }


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AttributeTemplate).order_by(AttributeTemplate.created_at.desc())).all()
    return [_template_out(row) for row in rows]


@router.post("/templates", status_code=201)
def create_template(payload: TemplateIn, db: Session = Depends(get_db)) -> dict:
    import json

    fields = [item.strip() for item in payload.fields if item.strip()]
    row = AttributeTemplate(name=payload.name.strip(), target="character", fields=json.dumps(fields, ensure_ascii=False))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _template_out(row)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(AttributeTemplate, template_id)
    if row is None:
        raise HTTPException(404, "模板不存在")
    db.delete(row)
    db.commit()


@router.get("/assets")
def list_assets(owner_kind: str = "", owner_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = select(MediaAsset).order_by(MediaAsset.created_at.desc())
    if owner_kind:
        query = query.where(MediaAsset.owner_kind == owner_kind)
    if owner_id is not None:
        query = query.where(MediaAsset.owner_id == owner_id)
    return [_asset_out(row) for row in db.scalars(query).all()]


@router.post("/assets", status_code=201)
async def create_asset(
    file: UploadFile = File(...),
    owner_kind: str = Form(""),
    owner_id: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    mime = file.content_type or ""
    if mime not in ALLOWED:
        raise HTTPException(422, "只能上传 jpg、png、gif 或 webp 图片")
    payload = await file.read()
    if not payload or len(payload) > MAX_BYTES:
        raise HTTPException(422, "图片不能为空，也不能超过 8MB")
    parsed_owner: uuid.UUID | None = None
    if owner_id.strip():
        try:
            parsed_owner = uuid.UUID(owner_id.strip())
        except ValueError as exc:
            raise HTTPException(422, "所属对象不正确") from exc
    UPLOADS.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ALLOWED[mime]}"
    (UPLOADS / stored).write_bytes(payload)
    row = MediaAsset(
        owner_kind=owner_kind.strip(),
        owner_id=parsed_owner,
        filename=(file.filename or stored)[:255],
        stored_name=stored,
        mime=mime,
        note=note.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _asset_out(row)


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(MediaAsset, asset_id)
    if row is None:
        raise HTTPException(404, "素材不存在")
    path = UPLOADS / row.stored_name
    if path.is_file():
        path.unlink()
    db.delete(row)
    db.commit()
