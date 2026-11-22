import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from pydantic import BaseModel, Field

from app.models import Character, Novel, NovelWorldSetting, World, WorldRecord, character_worlds, novel_worlds
from app.schemas import WorldIn, WorldOut

router = APIRouter(prefix="/worlds", tags=["worlds"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(db: Session, world: World) -> WorldOut:
    count = db.scalar(select(func.count()).select_from(novel_worlds).where(novel_worlds.c.world_id == world.id)) or 0
    return WorldOut(
        id=world.id,
        name=world.name,
        summary=world.summary,
        cover_url=world.cover_url,
        novel_count=int(count),
        created_at=world.created_at,
        updated_at=world.updated_at,
    )


@router.get("", response_model=list[WorldOut])
def list_worlds(db: Session = Depends(get_db)) -> list[WorldOut]:
    worlds = db.scalars(select(World).order_by(World.updated_at.desc())).all()
    return [_out(db, world) for world in worlds]


@router.post("", response_model=WorldOut, status_code=201)
def create_world(payload: WorldIn, db: Session = Depends(get_db)) -> WorldOut:
    world = World(name=payload.name.strip(), summary=payload.summary.strip(), cover_url=(payload.cover_url or "").strip())
    db.add(world)
    db.commit()
    db.refresh(world)
    return _out(db, world)


@router.patch("/{world_id}", response_model=WorldOut)
def update_world(world_id: uuid.UUID, payload: WorldIn, db: Session = Depends(get_db)) -> WorldOut:
    world = db.get(World, world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    world.name = payload.name.strip()
    world.summary = payload.summary.strip()
    if payload.cover_url is not None:
        world.cover_url = payload.cover_url.strip()
    world.updated_at = _now()
    db.commit()
    db.refresh(world)
    return _out(db, world)


@router.delete("/{world_id}", status_code=204)
def delete_world(world_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    world = db.get(World, world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    linked = db.scalar(select(func.count()).select_from(novel_worlds).where(novel_worlds.c.world_id == world.id)) or 0
    people = db.scalar(select(func.count()).select_from(character_worlds).where(character_worlds.c.world_id == world.id)) or 0
    if linked or people:
        raise HTTPException(409, "仍有小说或角色关联这个世界，不能删除")
    db.delete(world)
    db.commit()


@router.get("/{world_id}/relations")
def world_relations(world_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    world = db.get(World, world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    novels = db.execute(
        select(Novel.id, Novel.title).join(novel_worlds, novel_worlds.c.novel_id == Novel.id).where(novel_worlds.c.world_id == world_id)
    ).all()
    people = db.execute(
        select(
            Character.id,
            Character.name,
            character_worlds.c.note,
            character_worlds.c.scope,
            character_worlds.c.source,
            character_worlds.c.novel_id,
            character_worlds.c.created_at,
        )
        .join(character_worlds, character_worlds.c.character_id == Character.id)
        .where(character_worlds.c.world_id == world_id)
    ).all()
    characters = []
    for character_id, name, note, scope, source, novel_id, created_at in people:
        novel = db.get(Novel, novel_id) if novel_id else None
        characters.append(
            {
                "id": character_id,
                "name": name,
                "note": note,
                "scope": scope,
                "source": source,
                "novel_id": novel_id,
                "novel_title": novel.title if novel else "",
                "created_at": created_at,
            }
        )
    return {
        "id": world.id,
        "name": world.name,
        "summary": world.summary,
        "novels": [{"id": novel_id, "title": title} for novel_id, title in novels],
        "characters": characters,
    }


class SettingIn(BaseModel):
    supplement: str = ""


def _linked_novel(db: Session, world_id: uuid.UUID, novel_id: uuid.UUID) -> None:
    if db.get(World, world_id) is None or db.get(Novel, novel_id) is None:
        raise HTTPException(404, "世界或小说不存在")
    linked = db.execute(
        select(novel_worlds).where(novel_worlds.c.world_id == world_id, novel_worlds.c.novel_id == novel_id)
    ).first()
    if linked is None:
        raise HTTPException(404, "这本小说还没有关联这个世界")


@router.get("/{world_id}/novels/{novel_id}/setting")
def world_setting(world_id: uuid.UUID, novel_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _linked_novel(db, world_id, novel_id)
    row = db.scalar(
        select(NovelWorldSetting).where(NovelWorldSetting.world_id == world_id, NovelWorldSetting.novel_id == novel_id)
    )
    return {"novel_id": novel_id, "world_id": world_id, "supplement": row.supplement if row else ""}


@router.put("/{world_id}/novels/{novel_id}/setting")
def save_world_setting(world_id: uuid.UUID, novel_id: uuid.UUID, payload: SettingIn, db: Session = Depends(get_db)) -> dict:
    _linked_novel(db, world_id, novel_id)
    row = db.scalar(
        select(NovelWorldSetting).where(NovelWorldSetting.world_id == world_id, NovelWorldSetting.novel_id == novel_id)
    )
    if row is None:
        row = NovelWorldSetting(world_id=world_id, novel_id=novel_id, supplement=payload.supplement.strip())
        db.add(row)
    else:
        row.supplement = payload.supplement.strip()
        row.updated_at = _now()
    db.commit()
    return {"novel_id": novel_id, "world_id": world_id, "supplement": row.supplement}


RECORD_KINDS = {"object", "faction", "place", "event"}


class RecordIn(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""
    time_label: str = ""


class RecordUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    time_label: str | None = None


def _record_out(row: WorldRecord) -> dict:
    return {
        "id": row.id,
        "world_id": row.world_id,
        "kind": row.kind,
        "name": row.name,
        "summary": row.summary,
        "time_label": row.time_label,
        "updated_at": row.updated_at,
    }


@router.get("/{world_id}/records")
def list_records(world_id: uuid.UUID, kind: str = "", db: Session = Depends(get_db)) -> list[dict]:
    if db.get(World, world_id) is None:
        raise HTTPException(404, "世界不存在")
    query = select(WorldRecord).where(WorldRecord.world_id == world_id)
    if kind:
        if kind not in RECORD_KINDS:
            raise HTTPException(422, "记录类型不正确")
        query = query.where(WorldRecord.kind == kind)
    rows = db.scalars(query.order_by(WorldRecord.updated_at.desc())).all()
    return [_record_out(row) for row in rows]


@router.post("/{world_id}/records", status_code=201)
def create_record(world_id: uuid.UUID, payload: RecordIn, db: Session = Depends(get_db)) -> dict:
    if db.get(World, world_id) is None:
        raise HTTPException(404, "世界不存在")
    if payload.kind not in RECORD_KINDS:
        raise HTTPException(422, "记录类型不正确")
    row = WorldRecord(
        world_id=world_id,
        kind=payload.kind,
        name=payload.name.strip(),
        summary=payload.summary.strip(),
        time_label=payload.time_label.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _record_out(row)


@router.patch("/records/{record_id}")
def update_record(record_id: uuid.UUID, payload: RecordUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.get(WorldRecord, record_id)
    if row is None:
        raise HTTPException(404, "记录不存在")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.summary is not None:
        row.summary = payload.summary.strip()
    if payload.time_label is not None:
        row.time_label = payload.time_label.strip()
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _record_out(row)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(record_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(WorldRecord, record_id)
    if row is None:
        raise HTTPException(404, "记录不存在")
    db.delete(row)
    db.commit()
