import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import ACTIONS, complete_text
from app.database import get_db
from sqlalchemy import select

from app.models import AiSuggestion, Chapter, Novel
from app.schemas import AiRequest, AiSuggestionOut
from app.textutil import plain_text

router = APIRouter(tags=["ai"])


def _out(row: AiSuggestion) -> AiSuggestionOut:
    return AiSuggestionOut(
        id=row.id,
        action=row.action,
        source_text=row.source_text,
        suggestion=row.suggestion,
        status=row.status,
        provider=row.provider,
        created_at=row.created_at,
    )


@router.post("/chapters/{chapter_id}/suggestions", response_model=AiSuggestionOut, status_code=201)
async def create_suggestion(chapter_id: uuid.UUID, payload: AiRequest, db: Session = Depends(get_db)) -> AiSuggestionOut:
    chapter = db.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    if payload.action not in ACTIONS:
        raise HTTPException(422, "不支持的写作操作")
    context = plain_text(chapter.content)
    source = payload.selected_text.strip()
    if payload.action not in {"continue", "character", "plot", "conflict"} and not source:
        raise HTTPException(422, "请先选中一段正文")
    try:
        suggestion, provider = await complete_text(payload.action, source, context)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    except (KeyError, IndexError, ValueError) as exc:
        raise HTTPException(502, "模型没有返回可用正文") from exc
    if not suggestion.strip():
        raise HTTPException(502, "模型返回了空结果")
    row = AiSuggestion(
        chapter_id=chapter.id,
        action=payload.action,
        source_text=source,
        suggestion=suggestion.strip(),
        status="pending",
        provider=provider,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/suggestions/{suggestion_id}/accept", response_model=AiSuggestionOut)
def accept_suggestion(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> AiSuggestionOut:
    row = db.get(AiSuggestion, suggestion_id)
    if row is None:
        raise HTTPException(404, "建议不存在")
    if row.status != "pending":
        raise HTTPException(409, "这条建议已经处理过")
    row.status = "accepted"
    db.commit()
    db.refresh(row)
    return _out(row)


@router.post("/suggestions/{suggestion_id}/reject", response_model=AiSuggestionOut)
def reject_suggestion(suggestion_id: uuid.UUID, db: Session = Depends(get_db)) -> AiSuggestionOut:
    row = db.get(AiSuggestion, suggestion_id)
    if row is None:
        raise HTTPException(404, "建议不存在")
    if row.status != "pending":
        raise HTTPException(409, "这条建议已经处理过")
    row.status = "rejected"
    db.commit()
    db.refresh(row)
    return _out(row)


@router.get("/inbox/suggestions")
def inbox_suggestions(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(AiSuggestion, Chapter.title, Novel.id, Novel.title)
        .join(Chapter, Chapter.id == AiSuggestion.chapter_id)
        .join(Novel, Novel.id == Chapter.novel_id)
        .where(AiSuggestion.status == "pending")
        .order_by(AiSuggestion.created_at.desc())
    ).all()
    return [
        {
            "id": suggestion.id,
            "action": suggestion.action,
            "chapter_id": suggestion.chapter_id,
            "chapter_title": chapter_title,
            "novel_id": novel_id,
            "novel_title": novel_title,
            "created_at": suggestion.created_at,
        }
        for suggestion, chapter_title, novel_id, novel_title in rows
    ]
