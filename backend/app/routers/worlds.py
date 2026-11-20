import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Novel, World, character_worlds, novel_worlds
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
    world = World(name=payload.name.strip(), summary=payload.summary.strip())
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
        select(Character.id, Character.name, character_worlds.c.note)
        .join(character_worlds, character_worlds.c.character_id == Character.id)
        .where(character_worlds.c.world_id == world_id)
    ).all()
    return {
        "id": world.id,
        "name": world.name,
        "summary": world.summary,
        "novels": [{"id": novel_id, "title": title} for novel_id, title in novels],
        "characters": [{"id": character_id, "name": name, "note": note} for character_id, name, note in people],
    }
