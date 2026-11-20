import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chapter, ChapterRevision, Novel
from app.schemas import ChapterIn, ChapterOut, ChapterUpdate, RevisionOut
from app.textutil import count_words

router = APIRouter(tags=["chapters"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chapter_out(chapter: Chapter) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        novel_id=chapter.novel_id,
        title=chapter.title,
        content=chapter.content,
        position=chapter.position,
        word_count=chapter.word_count,
        updated_at=chapter.updated_at,
    )


def _touch_novel(db: Session, novel_id: uuid.UUID) -> None:
    novel = db.get(Novel, novel_id)
    if novel is not None:
        novel.updated_at = _now()


def _snapshot(db: Session, chapter: Chapter) -> None:
    db.add(ChapterRevision(chapter_id=chapter.id, content=chapter.content, word_count=chapter.word_count))


@router.post("/novels/{novel_id}/chapters", response_model=ChapterOut, status_code=201)
def create_chapter(novel_id: uuid.UUID, payload: ChapterIn, db: Session = Depends(get_db)) -> ChapterOut:
    novel = db.get(Novel, novel_id)
    if novel is None:
        raise HTTPException(404, "小说不存在")
    position = db.scalar(select(func.coalesce(func.max(Chapter.position), 0)).where(Chapter.novel_id == novel_id)) or 0
    chapter = Chapter(
        novel_id=novel_id,
        title=payload.title.strip(),
        content="<p></p>",
        position=int(position) + 1,
        word_count=0,
    )
    db.add(chapter)
    _touch_novel(db, novel_id)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter)


@router.get("/chapters/{chapter_id}", response_model=ChapterOut)
def get_chapter(chapter_id: uuid.UUID, db: Session = Depends(get_db)) -> ChapterOut:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    return _chapter_out(chapter)


@router.patch("/chapters/{chapter_id}", response_model=ChapterOut)
def update_chapter(chapter_id: uuid.UUID, payload: ChapterUpdate, db: Session = Depends(get_db)) -> ChapterOut:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    if payload.content is not None and payload.content != chapter.content:
        _snapshot(db, chapter)
        chapter.content = payload.content
        chapter.word_count = count_words(payload.content)
    if payload.title is not None:
        chapter.title = payload.title.strip()
    chapter.updated_at = _now()
    _touch_novel(db, chapter.novel_id)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter)


@router.delete("/chapters/{chapter_id}", status_code=204)
def delete_chapter(chapter_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    remaining = db.scalar(select(func.count()).select_from(Chapter).where(Chapter.novel_id == chapter.novel_id)) or 0
    if remaining <= 1:
        raise HTTPException(409, "至少保留一个章节")
    novel_id = chapter.novel_id
    db.delete(chapter)
    _touch_novel(db, novel_id)
    db.commit()


@router.get("/chapters/{chapter_id}/revisions", response_model=list[RevisionOut])
def list_revisions(chapter_id: uuid.UUID, db: Session = Depends(get_db)) -> list[RevisionOut]:
    if db.get(Chapter, chapter_id) is None:
        raise HTTPException(404, "章节不存在")
    rows = db.scalars(
        select(ChapterRevision).where(ChapterRevision.chapter_id == chapter_id).order_by(ChapterRevision.created_at.desc()).limit(20)
    ).all()
    return [RevisionOut(id=row.id, word_count=row.word_count, created_at=row.created_at) for row in rows]


@router.post("/chapters/{chapter_id}/revisions/{revision_id}/restore", response_model=ChapterOut)
def restore_revision(chapter_id: uuid.UUID, revision_id: uuid.UUID, db: Session = Depends(get_db)) -> ChapterOut:
    chapter = db.get(Chapter, chapter_id)
    revision = db.get(ChapterRevision, revision_id)
    if chapter is None or revision is None or revision.chapter_id != chapter.id:
        raise HTTPException(404, "版本不存在")
    _snapshot(db, chapter)
    chapter.content = revision.content
    chapter.word_count = count_words(revision.content)
    chapter.updated_at = _now()
    _touch_novel(db, chapter.novel_id)
    db.commit()
    db.refresh(chapter)
    return _chapter_out(chapter)
