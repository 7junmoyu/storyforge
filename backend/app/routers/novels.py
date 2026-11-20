import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Chapter, Novel, World
from app.schemas import NovelDetail, NovelIn, NovelOut, NovelUpdate, WorldBrief

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
        worlds=[WorldBrief(id=world.id, name=world.name) for world in novel.worlds],
        created_at=novel.created_at,
        updated_at=novel.updated_at,
    )


def _get_novel(db: Session, novel_id: uuid.UUID) -> Novel:
    novel = db.scalar(select(Novel).options(selectinload(Novel.worlds)).where(Novel.id == novel_id))
    if novel is None:
        raise HTTPException(404, "小说不存在")
    return novel


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


@router.get("", response_model=list[NovelOut])
def list_novels(db: Session = Depends(get_db)) -> list[NovelOut]:
    novels = db.scalars(select(Novel).options(selectinload(Novel.worlds)).order_by(Novel.updated_at.desc())).all()
    return [_out(db, novel) for novel in novels]


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
    )
    db.add(novel)
    db.flush()
    _apply_world(db, novel, payload.world_id, clear=False)
    chapter = Chapter(novel_id=novel.id, title="第一章", content="<p></p>", position=1, word_count=0)
    db.add(chapter)
    db.commit()
    return get_novel(novel.id, db)


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
    if payload.clear_world:
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
