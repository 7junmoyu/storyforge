import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AttributeTemplate,
    Character,
    CharacterPeriod,
    CharacterVersion,
    Novel,
    World,
    character_worlds,
    foreshadow_characters,
    novel_characters,
    outline_characters,
)

router = APIRouter(prefix="/characters", tags=["characters"])


class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""
    cover_url: str | None = None
    attributes: dict[str, str] | None = None


class WorldLinkIn(BaseModel):
    world_id: uuid.UUID
    note: str = ""
    scope: str = "global"
    source: str = "手动"
    novel_id: uuid.UUID | None = None


class PeriodIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    time_range: str = ""
    attributes: dict[str, str] = {}


class PeriodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    time_range: str | None = None
    attributes: dict[str, str] | None = None


class VersionIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""
    attributes: dict[str, str] = {}
    period_id: uuid.UUID | None = None


class ConfirmIn(BaseModel):
    confirm: bool = False
    period_id: uuid.UUID | None = None


class CharacterOut(BaseModel):
    id: uuid.UUID
    name: str
    summary: str
    cover_url: str = ""
    attributes: dict[str, str] = {}
    novel_count: int = 0
    created_at: datetime
    updated_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(db: Session, row: Character) -> CharacterOut:
    count = db.scalar(
        select(func.count()).select_from(novel_characters).where(novel_characters.c.character_id == row.id)
    ) or 0
    return CharacterOut(
        id=row.id,
        name=row.name,
        summary=row.summary,
        cover_url=row.cover_url,
        attributes=_load_attrs(row.attributes),
        novel_count=int(count),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[CharacterOut])
def list_characters(q: str = "", db: Session = Depends(get_db)) -> list[CharacterOut]:
    query = select(Character).order_by(Character.updated_at.desc())
    if q.strip():
        query = query.where(Character.name.contains(q.strip()))
    return [_out(db, row) for row in db.scalars(query).all()]


@router.post("", response_model=CharacterOut, status_code=201)
def create_character(payload: CharacterIn, db: Session = Depends(get_db)) -> CharacterOut:
    row = Character(
        name=payload.name.strip(),
        summary=payload.summary.strip(),
        cover_url=(payload.cover_url or "").strip(),
        attributes=_dump_attrs(payload.attributes or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.patch("/{character_id}", response_model=CharacterOut)
def update_character(character_id: uuid.UUID, payload: CharacterIn, db: Session = Depends(get_db)) -> CharacterOut:
    row = db.get(Character, character_id)
    if row is None:
        raise HTTPException(404, "角色不存在")
    row.name = payload.name.strip()
    row.summary = payload.summary.strip()
    if payload.cover_url is not None:
        row.cover_url = payload.cover_url.strip()
    if payload.attributes is not None:
        row.attributes = _dump_attrs(payload.attributes)
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(Character, character_id)
    if row is None:
        raise HTTPException(404, "角色不存在")
    linked = db.scalar(select(func.count()).select_from(novel_characters).where(novel_characters.c.character_id == character_id)) or 0
    outlined = db.scalar(select(func.count()).select_from(outline_characters).where(outline_characters.c.character_id == character_id)) or 0
    foreshadowed = db.scalar(
        select(func.count()).select_from(foreshadow_characters).where(foreshadow_characters.c.character_id == character_id)
    ) or 0
    if linked or outlined or foreshadowed:
        raise HTTPException(409, "仍有小说、大纲或伏笔使用这个角色，不能删除")
    db.delete(row)
    db.commit()


def _link_fields(db: Session, payload: WorldLinkIn) -> dict:
    scope = payload.scope if payload.scope in {"global", "novel"} else ""
    if not scope:
        raise HTTPException(422, "关联范围只能是全局或某本小说")
    novel_id = payload.novel_id
    if scope == "novel":
        if novel_id is None or db.get(Novel, novel_id) is None:
            raise HTTPException(404, "要标明这是哪本小说里的关联")
    else:
        novel_id = None
    return {
        "note": payload.note.strip(),
        "scope": scope,
        "source": (payload.source or "手动").strip() or "手动",
        "novel_id": novel_id,
    }


def _link_out(db: Session, world: World, note: str, scope: str, source: str, novel_id: uuid.UUID | None, created_at: datetime) -> dict:
    novel = db.get(Novel, novel_id) if novel_id else None
    return {
        "id": world.id,
        "name": world.name,
        "summary": world.summary,
        "note": note,
        "scope": scope,
        "source": source,
        "novel_id": novel_id,
        "novel_title": novel.title if novel else "",
        "created_at": created_at,
    }


@router.get("/{character_id}/worlds")
def character_worlds_list(character_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    rows = db.execute(
        select(
            World,
            character_worlds.c.note,
            character_worlds.c.scope,
            character_worlds.c.source,
            character_worlds.c.novel_id,
            character_worlds.c.created_at,
        )
        .join(character_worlds, character_worlds.c.world_id == World.id)
        .where(character_worlds.c.character_id == character_id)
        .order_by(World.name)
    ).all()
    return [_link_out(db, world, note, scope, source, novel_id, created_at) for world, note, scope, source, novel_id, created_at in rows]


@router.post("/{character_id}/worlds", status_code=201)
def link_character_world(character_id: uuid.UUID, payload: WorldLinkIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    world = db.get(World, payload.world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    fields = _link_fields(db, payload)
    existing = db.execute(
        select(character_worlds).where(
            character_worlds.c.character_id == character_id,
            character_worlds.c.world_id == world.id,
        )
    ).first()
    if existing is None:
        db.execute(character_worlds.insert().values(character_id=character_id, world_id=world.id, **fields))
    else:
        db.execute(
            character_worlds.update()
            .where(character_worlds.c.character_id == character_id, character_worlds.c.world_id == world.id)
            .values(**fields)
        )
    db.commit()
    created_at = db.scalar(
        select(character_worlds.c.created_at).where(
            character_worlds.c.character_id == character_id,
            character_worlds.c.world_id == world.id,
        )
    )
    return _link_out(db, world, fields["note"], fields["scope"], fields["source"], fields["novel_id"], created_at)


@router.delete("/{character_id}/worlds/{world_id}", status_code=204)
def unlink_character_world(character_id: uuid.UUID, world_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    db.execute(
        character_worlds.delete().where(
            character_worlds.c.character_id == character_id,
            character_worlds.c.world_id == world_id,
        )
    )
    db.commit()


def _dump_attrs(attributes: dict[str, str]) -> str:
    return json.dumps({str(key): str(value) for key, value in attributes.items()}, ensure_ascii=False)


def _load_attrs(raw: str) -> dict[str, str]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def _period_out(row: CharacterPeriod) -> dict:
    return {
        "id": row.id,
        "character_id": row.character_id,
        "name": row.name,
        "time_range": row.time_range,
        "attributes": _load_attrs(row.attributes),
        "position": row.position,
        "updated_at": row.updated_at,
    }


def _version_out(db: Session, row: CharacterVersion) -> dict:
    novel = db.get(Novel, row.novel_id)
    return {
        "id": row.id,
        "novel_id": row.novel_id,
        "novel_title": novel.title if novel else "",
        "character_id": row.character_id,
        "period_id": row.period_id,
        "name": row.name,
        "summary": row.summary,
        "attributes": _load_attrs(row.attributes),
        "updated_at": row.updated_at,
    }


def _require_link(db: Session, character_id: uuid.UUID, novel_id: uuid.UUID) -> tuple[Character, Novel]:
    character = db.get(Character, character_id)
    novel = db.get(Novel, novel_id)
    if character is None or novel is None:
        raise HTTPException(404, "角色或小说不存在")
    linked = db.execute(
        select(novel_characters).where(
            novel_characters.c.character_id == character_id,
            novel_characters.c.novel_id == novel_id,
        )
    ).first()
    if linked is None:
        raise HTTPException(404, "这本小说还没有关联这个角色")
    return character, novel


def _version_row(db: Session, character_id: uuid.UUID, novel_id: uuid.UUID) -> CharacterVersion | None:
    return db.scalar(
        select(CharacterVersion).where(
            CharacterVersion.character_id == character_id,
            CharacterVersion.novel_id == novel_id,
        )
    )


@router.get("/{character_id}/periods")
def list_periods(character_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    rows = db.scalars(
        select(CharacterPeriod).where(CharacterPeriod.character_id == character_id).order_by(CharacterPeriod.position)
    ).all()
    return [_period_out(row) for row in rows]


@router.post("/{character_id}/periods", status_code=201)
def create_period(character_id: uuid.UUID, payload: PeriodIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    position = db.scalar(
        select(func.coalesce(func.max(CharacterPeriod.position), 0)).where(CharacterPeriod.character_id == character_id)
    )
    row = CharacterPeriod(
        character_id=character_id,
        name=payload.name.strip(),
        time_range=payload.time_range.strip(),
        attributes=_dump_attrs(payload.attributes),
        position=int(position or 0) + 1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _period_out(row)


@router.patch("/periods/{period_id}")
def update_period(period_id: uuid.UUID, payload: PeriodUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.get(CharacterPeriod, period_id)
    if row is None:
        raise HTTPException(404, "角色时期不存在")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.time_range is not None:
        row.time_range = payload.time_range.strip()
    if payload.attributes is not None:
        row.attributes = _dump_attrs(payload.attributes)
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _period_out(row)


@router.delete("/periods/{period_id}", status_code=204)
def delete_period(period_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(CharacterPeriod, period_id)
    if row is None:
        raise HTTPException(404, "角色时期不存在")
    db.delete(row)
    db.commit()


@router.get("/{character_id}/versions")
def list_versions(character_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    rows = db.scalars(select(CharacterVersion).where(CharacterVersion.character_id == character_id)).all()
    return [_version_out(db, row) for row in rows]


@router.put("/{character_id}/versions/{novel_id}")
def save_version(character_id: uuid.UUID, novel_id: uuid.UUID, payload: VersionIn, db: Session = Depends(get_db)) -> dict:
    _require_link(db, character_id, novel_id)
    if payload.period_id is not None:
        period = db.get(CharacterPeriod, payload.period_id)
        if period is None or period.character_id != character_id:
            raise HTTPException(404, "角色时期不存在")
    row = _version_row(db, character_id, novel_id)
    if row is None:
        row = CharacterVersion(character_id=character_id, novel_id=novel_id, name=payload.name.strip())
        db.add(row)
    row.name = payload.name.strip()
    row.summary = payload.summary.strip()
    row.attributes = _dump_attrs(payload.attributes)
    row.period_id = payload.period_id
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _version_out(db, row)


@router.post("/{character_id}/versions/{novel_id}/from-global")
def version_from_global(character_id: uuid.UUID, novel_id: uuid.UUID, payload: ConfirmIn, db: Session = Depends(get_db)) -> dict:
    character, _novel = _require_link(db, character_id, novel_id)
    if not payload.confirm:
        raise HTTPException(400, "需要确认后才会把全局档案写入这本小说的专属版本")
    row = _version_row(db, character_id, novel_id)
    if row is None:
        row = CharacterVersion(character_id=character_id, novel_id=novel_id, name=character.name)
        db.add(row)
    row.name = character.name
    row.summary = character.summary
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _version_out(db, row)


@router.post("/{character_id}/versions/{novel_id}/from-period")
def version_from_period(character_id: uuid.UUID, novel_id: uuid.UUID, payload: ConfirmIn, db: Session = Depends(get_db)) -> dict:
    character, _novel = _require_link(db, character_id, novel_id)
    if not payload.confirm or payload.period_id is None:
        raise HTTPException(400, "需要确认并指定时期后才会写入这本小说的专属版本")
    period = db.get(CharacterPeriod, payload.period_id)
    if period is None or period.character_id != character_id:
        raise HTTPException(404, "角色时期不存在")
    row = _version_row(db, character_id, novel_id)
    if row is None:
        row = CharacterVersion(character_id=character_id, novel_id=novel_id, name=character.name)
        db.add(row)
    row.name = character.name
    row.summary = character.summary
    row.attributes = period.attributes
    row.period_id = period.id
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _version_out(db, row)


class ApplyTemplateIn(BaseModel):
    template_id: uuid.UUID
    confirm: bool = False


@router.post("/{character_id}/apply-template", response_model=CharacterOut)
def apply_template(character_id: uuid.UUID, payload: ApplyTemplateIn, db: Session = Depends(get_db)) -> CharacterOut:
    row = db.get(Character, character_id)
    template = db.get(AttributeTemplate, payload.template_id)
    if row is None or template is None or template.target != "character":
        raise HTTPException(404, "角色或模板不存在")
    if not payload.confirm:
        raise HTTPException(400, "确认后才会补充空字段，已经填写的内容不会被覆盖")
    try:
        names = json.loads(template.fields or "[]")
    except json.JSONDecodeError:
        names = []
    current = _load_attrs(row.attributes)
    if isinstance(names, list):
        for key in names:
            label = str(key).strip()
            if label and not current.get(label):
                current[label] = ""
    row.attributes = _dump_attrs(current)
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.delete("/{character_id}/versions/{novel_id}", status_code=204)
def delete_version(character_id: uuid.UUID, novel_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = _version_row(db, character_id, novel_id)
    if row is None:
        raise HTTPException(404, "专属版本不存在")
    db.delete(row)
    db.commit()
