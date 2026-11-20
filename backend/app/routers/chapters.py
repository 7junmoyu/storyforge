import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Chapter, ChapterRevision, Novel, TextMark, Volume
from app.schemas import ChapterIn, ChapterOut, ChapterUpdate, RevisionOut
from app.textutil import count_words

router = APIRouter(tags=["chapters"])


class MoveIn(BaseModel):
    direction: str = Field(pattern="^(up|down)$")


class MarkIn(BaseModel):
    quote: str = ""
    start: int = Field(default=0, ge=0)
    end: int = Field(default=0, ge=0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chapter_out(chapter: Chapter) -> ChapterOut:
    return ChapterOut(
        id=chapter.id,
        novel_id=chapter.novel_id,
        volume_id=chapter.volume_id,
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
    if payload.volume_id is not None:
        volume = db.get(Volume, payload.volume_id)
        if volume is None or volume.novel_id != novel_id:
            raise HTTPException(404, "分卷不存在")
    chapter = Chapter(
        novel_id=novel_id,
        title=payload.title.strip(),
        volume_id=payload.volume_id,
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
    if payload.clear_volume:
        chapter.volume_id = None
    elif payload.volume_id is not None:
        volume = db.get(Volume, payload.volume_id)
        if volume is None or volume.novel_id != chapter.novel_id:
            raise HTTPException(404, "分卷不存在")
        chapter.volume_id = volume.id
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


@router.post("/chapters/{chapter_id}/move")
def move_chapter(chapter_id: uuid.UUID, payload: MoveIn, db: Session = Depends(get_db)) -> list[ChapterOut]:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    rows = list(
        db.scalars(select(Chapter).where(Chapter.novel_id == chapter.novel_id).order_by(Chapter.position)).all()
    )
    index = next(i for i, item in enumerate(rows) if item.id == chapter.id)
    target = index - 1 if payload.direction == "up" else index + 1
    if 0 <= target < len(rows):
        rows[index], rows[target] = rows[target], rows[index]
        for position, item in enumerate(rows, start=1):
            item.position = position
        _touch_novel(db, chapter.novel_id)
        db.commit()
    return [_chapter_out(item) for item in rows]


@router.get("/chapters/{chapter_id}/marks")
def list_marks(chapter_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    if db.get(Chapter, chapter_id) is None:
        raise HTTPException(404, "章节不存在")
    rows = db.scalars(select(TextMark).where(TextMark.chapter_id == chapter_id).order_by(TextMark.start)).all()
    return [{"id": row.id, "quote": row.quote, "start": row.start, "end": row.end, "chapter_id": row.chapter_id} for row in rows]


@router.post("/chapters/{chapter_id}/marks", status_code=201)
def create_mark(chapter_id: uuid.UUID, payload: MarkIn, db: Session = Depends(get_db)) -> dict:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    row = TextMark(novel_id=chapter.novel_id, chapter_id=chapter.id, quote=payload.quote.strip(), start=payload.start, end=payload.end)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "quote": row.quote, "start": row.start, "end": row.end, "chapter_id": row.chapter_id}


@router.delete("/marks/{mark_id}", status_code=204)
def delete_mark(mark_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(TextMark, mark_id)
    if row is None:
        raise HTTPException(404, "标记不存在")
    db.delete(row)
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
