import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, World, character_worlds, foreshadow_characters, novel_characters, outline_characters

router = APIRouter(prefix="/characters", tags=["characters"])


class CharacterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""


class WorldLinkIn(BaseModel):
    world_id: uuid.UUID
    note: str = ""


class CharacterOut(BaseModel):
    id: uuid.UUID
    name: str
    summary: str
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
    row = Character(name=payload.name.strip(), summary=payload.summary.strip())
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


@router.get("/{character_id}/worlds")
def character_worlds_list(character_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    rows = db.execute(
        select(World, character_worlds.c.note)
        .join(character_worlds, character_worlds.c.world_id == World.id)
        .where(character_worlds.c.character_id == character_id)
        .order_by(World.name)
    ).all()
    return [{"id": world.id, "name": world.name, "summary": world.summary, "note": note} for world, note in rows]


@router.post("/{character_id}/worlds", status_code=201)
def link_character_world(character_id: uuid.UUID, payload: WorldLinkIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Character, character_id) is None:
        raise HTTPException(404, "角色不存在")
    world = db.get(World, payload.world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    note = payload.note.strip()
    existing = db.execute(
        select(character_worlds).where(
            character_worlds.c.character_id == character_id,
            character_worlds.c.world_id == world.id,
        )
    ).first()
    if existing is None:
        db.execute(character_worlds.insert().values(character_id=character_id, world_id=world.id, note=note))
    else:
        db.execute(
            character_worlds.update()
            .where(character_worlds.c.character_id == character_id, character_worlds.c.world_id == world.id)
            .values(note=note)
        )
    db.commit()
    return {"id": world.id, "name": world.name, "note": note}


@router.delete("/{character_id}/worlds/{world_id}", status_code=204)
def unlink_character_world(character_id: uuid.UUID, world_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    db.execute(
        character_worlds.delete().where(
            character_worlds.c.character_id == character_id,
            character_worlds.c.world_id == world_id,
        )
    )
    db.commit()
