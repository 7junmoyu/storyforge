import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.exporting import novel_docx, novel_pdf, novel_text
from app.textutil import plain_text
from app.models import Chapter, Character, CharacterVersion, Novel, NovelGroup, Volume, World
from app.schemas import NovelDetail, NovelImport, NovelIn, NovelOut, NovelUpdate, VolumeIn, VolumeOut, VolumeUpdate, WorldBrief

router = APIRouter(prefix="/novels", tags=["novels"])

STATUSES = {"draft", "writing", "finished"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _stats(db: Session, novel_id: uuid.UUID) -> tuple[int, int]:
    word_count, chapter_count = db.execute(
        select(func.coalesce(func.sum(Chapter.word_count), 0), func.count(Chapter.id)).where(Chapter.novel_id == novel_id)
    ).one()
    return int(word_count), int(chapter_count)


def _out(db: Session, novel: Novel) -> NovelOut:
    words, chapters = _stats(db, novel.id)
    return NovelOut(
        id=novel.id,
        title=novel.title,
        summary=novel.summary,
        genre=novel.genre,
        status=novel.status,
        target_words=novel.target_words,
        word_count=words,
        chapter_count=chapters,
        tags=novel.tags,
        cover_url=novel.cover_url,
        archived=novel.archived,
        worlds=[WorldBrief(id=world.id, name=world.name) for world in novel.worlds],
        characters=[WorldBrief(id=row.id, name=row.name) for row in novel.characters],
        group_id=novel.group_id,
        grouped_at=novel.grouped_at,
        created_at=novel.created_at,
        updated_at=novel.updated_at,
    )


def _get_novel(db: Session, novel_id: uuid.UUID) -> Novel:
    novel = db.scalar(
        select(Novel).options(selectinload(Novel.worlds), selectinload(Novel.characters)).where(Novel.id == novel_id)
    )
    if novel is None:
        raise HTTPException(404, "小说不存在")
    return novel


def _apply_worlds(db: Session, novel: Novel, world_ids: list[uuid.UUID]) -> None:
    rows: list[World] = []
    for world_id in world_ids:
        world = db.get(World, world_id)
        if world is None:
            raise HTTPException(404, "世界不存在")
        if world not in rows:
            rows.append(world)
    novel.worlds = rows


def _apply_world(db: Session, novel: Novel, world_id: uuid.UUID | None, clear: bool) -> None:
    if clear or world_id is None and clear:
        novel.worlds.clear()
        return
    if world_id is None:
        return
    world = db.get(World, world_id)
    if world is None:
        raise HTTPException(404, "世界不存在")
    novel.worlds = [world]


def _apply_characters(db: Session, novel: Novel, character_ids: list[uuid.UUID]) -> None:
    rows: list[Character] = []
    for character_id in character_ids:
        row = db.get(Character, character_id)
        if row is None:
            raise HTTPException(404, "角色不存在")
        if row not in rows:
            rows.append(row)
    novel.characters = rows


@router.get("", response_model=list[NovelOut])
def list_novels(include_archived: bool = False, db: Session = Depends(get_db)) -> list[NovelOut]:
    query = select(Novel).options(selectinload(Novel.worlds), selectinload(Novel.characters)).order_by(Novel.updated_at.desc())
    if not include_archived:
        query = query.where(Novel.archived.is_(False))
    return [_out(db, novel) for novel in db.scalars(query).all()]


@router.post("", response_model=NovelDetail, status_code=201)
def create_novel(payload: NovelIn, db: Session = Depends(get_db)) -> NovelDetail:
    if payload.status not in STATUSES:
        raise HTTPException(422, "创作状态无效")
    novel = Novel(
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        genre=payload.genre.strip(),
        status=payload.status,
        target_words=payload.target_words,
        tags=payload.tags.strip(),
        cover_url=payload.cover_url.strip(),
    )
    db.add(novel)
    db.flush()
    if payload.world_ids is not None:
        _apply_worlds(db, novel, payload.world_ids)
    else:
        _apply_world(db, novel, payload.world_id, clear=False)
    _apply_characters(db, novel, payload.character_ids)
    chapter = Chapter(novel_id=novel.id, title="第一章", content="<p></p>", position=1, word_count=0)
    db.add(chapter)
    db.commit()
    return get_novel(novel.id, db)


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


def _group_out(row: NovelGroup) -> dict:
    return {"id": row.id, "name": row.name, "created_at": row.created_at, "updated_at": row.updated_at}


@router.get("/groups")
def list_groups(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(NovelGroup).order_by(NovelGroup.created_at.desc())).all()
    return [_group_out(row) for row in rows]


@router.post("/groups", status_code=201)
def create_group(payload: GroupIn, db: Session = Depends(get_db)) -> dict:
    row = NovelGroup(name=payload.name.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _group_out(row)


@router.patch("/groups/{group_id}")
def rename_group(group_id: uuid.UUID, payload: GroupIn, db: Session = Depends(get_db)) -> dict:
    row = db.get(NovelGroup, group_id)
    if row is None:
        raise HTTPException(404, "分类不存在")
    row.name = payload.name.strip()
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _group_out(row)


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(NovelGroup, group_id)
    if row is None:
        raise HTTPException(404, "分类不存在")
    for novel in db.scalars(select(Novel).where(Novel.group_id == group_id)).all():
        novel.group_id = None
        novel.grouped_at = None
    db.delete(row)
    db.commit()


@router.get("/{novel_id}", response_model=NovelDetail)
def get_novel(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> NovelDetail:
    novel = _get_novel(db, novel_id)
    chapters = db.scalars(select(Chapter).where(Chapter.novel_id == novel.id).order_by(Chapter.position)).all()
    base = _out(db, novel)
    return NovelDetail(
        **base.model_dump(),
        chapters=[
            {
                "id": chapter.id,
                "title": chapter.title,
                "position": chapter.position,
                "word_count": chapter.word_count,
                "volume_id": chapter.volume_id,
                "world_id": chapter.world_id,
                "excerpt": " ".join(plain_text(chapter.content).split())[:160],
                "updated_at": chapter.updated_at,
            }
            for chapter in chapters
        ],
    )


@router.patch("/{novel_id}", response_model=NovelOut)
def update_novel(novel_id: uuid.UUID, payload: NovelUpdate, db: Session = Depends(get_db)) -> NovelOut:
    novel = _get_novel(db, novel_id)
    if payload.status is not None and payload.status not in STATUSES:
        raise HTTPException(422, "创作状态无效")
    if payload.title is not None:
        novel.title = payload.title.strip()
    if payload.summary is not None:
        novel.summary = payload.summary.strip()
    if payload.genre is not None:
        novel.genre = payload.genre.strip()
    if payload.status is not None:
        novel.status = payload.status
    if payload.target_words is not None:
        novel.target_words = payload.target_words
    if payload.tags is not None:
        novel.tags = payload.tags.strip()
    if payload.cover_url is not None:
        novel.cover_url = payload.cover_url.strip()
    if "group_id" in payload.model_fields_set:
        if payload.group_id is None:
            novel.group_id = None
            novel.grouped_at = None
        else:
            if db.get(NovelGroup, payload.group_id) is None:
                raise HTTPException(404, "分类不存在")
            novel.group_id = payload.group_id
            novel.grouped_at = _now()
    if payload.archived is not None:
        novel.archived = payload.archived
    if payload.character_ids is not None:
        _apply_characters(db, novel, payload.character_ids)
    if payload.world_ids is not None:
        _apply_worlds(db, novel, payload.world_ids)
    elif payload.clear_world:
        novel.worlds.clear()
    elif payload.world_id is not None:
        _apply_world(db, novel, payload.world_id, clear=False)
    novel.updated_at = _now()
    db.commit()
    db.refresh(novel)
    return _out(db, novel)


@router.delete("/{novel_id}", status_code=204)
def delete_novel(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    novel = db.get(Novel, novel_id)
    if novel is None:
        raise HTTPException(404, "小说不存在")
    db.delete(novel)
    db.commit()


@router.post("/{novel_id}/duplicate", response_model=NovelDetail, status_code=201)
def duplicate_novel(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> NovelDetail:
    source = _get_novel(db, novel_id)
    copy = Novel(
        title=f"{source.title} 副本"[:200],
        summary=source.summary,
        genre=source.genre,
        status=source.status,
        target_words=source.target_words,
        tags=source.tags,
        cover_url=source.cover_url,
        archived=False,
    )
    copy.worlds = list(source.worlds)
    copy.characters = list(source.characters)
    db.add(copy)
    db.flush()
    for volume in db.scalars(select(Volume).where(Volume.novel_id == source.id).order_by(Volume.position)).all():
        db.add(Volume(novel_id=copy.id, title=volume.title, position=volume.position))
    db.flush()
    volume_by_title = {
        row.title: row.id
        for row in db.scalars(select(Volume).where(Volume.novel_id == copy.id)).all()
    }
    source_volumes = {row.id: row.title for row in db.scalars(select(Volume).where(Volume.novel_id == source.id)).all()}
    for chapter in db.scalars(select(Chapter).where(Chapter.novel_id == source.id).order_by(Chapter.position)).all():
        volume_title = source_volumes.get(chapter.volume_id) if chapter.volume_id else None
        db.add(
            Chapter(
                novel_id=copy.id,
                volume_id=volume_by_title.get(volume_title) if volume_title else None,
                title=chapter.title,
                content=chapter.content,
                position=chapter.position,
                word_count=chapter.word_count,
            )
        )
    for version in db.scalars(select(CharacterVersion).where(CharacterVersion.novel_id == source.id)).all():
        db.add(
            CharacterVersion(
                novel_id=copy.id,
                character_id=version.character_id,
                period_id=version.period_id,
                name=version.name,
                summary=version.summary,
                attributes=version.attributes,
            )
        )
    db.commit()
    return get_novel(copy.id, db)


@router.post("/import", response_model=NovelDetail, status_code=201)
def import_novel(payload: NovelImport, db: Session = Depends(get_db)) -> NovelDetail:
    if payload.status not in STATUSES:
        raise HTTPException(422, "创作状态无效")
    novel = Novel(
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        genre=payload.genre.strip(),
        status=payload.status,
        target_words=payload.target_words,
        tags=payload.tags.strip(),
    )
    db.add(novel)
    db.flush()
    for index, chapter in enumerate(payload.chapters or [], start=1):
        db.add(
            Chapter(
                novel_id=novel.id,
                title=chapter.title.strip(),
                content=chapter.content or "<p></p>",
                position=index,
                word_count=0,
            )
        )
    if not payload.chapters:
        db.add(Chapter(novel_id=novel.id, title="第一章", content="<p></p>", position=1, word_count=0))
    db.commit()
    return get_novel(novel.id, db)


def _pairs(db: Session, novel_id: uuid.UUID) -> tuple[Novel, list[tuple[str, str]]]:
    novel = _get_novel(db, novel_id)
    rows = db.scalars(select(Chapter).where(Chapter.novel_id == novel_id).order_by(Chapter.position)).all()
    return novel, [(row.title, row.content) for row in rows]


@router.get("/{novel_id}/export.txt")
def export_txt(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    novel, pairs = _pairs(db, novel_id)
    body = novel_text(novel.title, pairs).encode("utf-8")
    return Response(body, media_type="text/plain; charset=utf-8", headers={"Content-Disposition": "attachment; filename=novel.txt"})


@router.get("/{novel_id}/export.docx")
def export_docx(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    novel, pairs = _pairs(db, novel_id)
    return Response(
        novel_docx(novel.title, pairs),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=novel.docx"},
    )


@router.get("/{novel_id}/export.pdf")
def export_pdf(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    novel, pairs = _pairs(db, novel_id)
    try:
        payload = novel_pdf(novel.title, pairs)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(payload, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=novel.pdf"})


@router.get("/{novel_id}/volumes", response_model=list[VolumeOut])
def list_volumes(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> list[VolumeOut]:
    _get_novel(db, novel_id)
    rows = db.scalars(select(Volume).where(Volume.novel_id == novel_id).order_by(Volume.position)).all()
    return [VolumeOut(id=row.id, novel_id=row.novel_id, title=row.title, position=row.position) for row in rows]


@router.post("/{novel_id}/volumes", response_model=VolumeOut, status_code=201)
def create_volume(novel_id: uuid.UUID, payload: VolumeIn, db: Session = Depends(get_db)) -> VolumeOut:
    _get_novel(db, novel_id)
    position = db.scalar(select(func.coalesce(func.max(Volume.position), 0)).where(Volume.novel_id == novel_id)) or 0
    row = Volume(novel_id=novel_id, title=payload.title.strip(), position=int(position) + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return VolumeOut(id=row.id, novel_id=row.novel_id, title=row.title, position=row.position)


@router.patch("/{novel_id}/volumes/{volume_id}", response_model=VolumeOut)
def update_volume(novel_id: uuid.UUID, volume_id: uuid.UUID, payload: VolumeUpdate, db: Session = Depends(get_db)) -> VolumeOut:
    row = db.get(Volume, volume_id)
    if row is None or row.novel_id != novel_id:
        raise HTTPException(404, "分卷不存在")
    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.position is not None:
        row.position = payload.position
    db.commit()
    db.refresh(row)
    return VolumeOut(id=row.id, novel_id=row.novel_id, title=row.title, position=row.position)


@router.delete("/{novel_id}/volumes/{volume_id}", status_code=204)
def delete_volume(novel_id: uuid.UUID, volume_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(Volume, volume_id)
    if row is None or row.novel_id != novel_id:
        raise HTTPException(404, "分卷不存在")
    for chapter in db.scalars(select(Chapter).where(Chapter.volume_id == row.id)).all():
        chapter.volume_id = None
    db.delete(row)
    db.commit()
