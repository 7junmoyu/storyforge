import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import complete_text
from app.database import get_db
from app.models import Chapter, Character, Foreshadow, Novel, OutlineNode

router = APIRouter(tags=["foreshadows"])
STATUSES = {"planned", "planted", "pending_payoff", "paid", "discarded"}
IMPORTANCE = {"low", "medium", "high"}
OPEN_STATUSES = {"planted", "pending_payoff"}


class ForeshadowIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = ""
    kind: str = ""
    importance: str = "medium"
    status: str = "planned"
    outline_node_id: uuid.UUID | None = None
    plant_chapter_id: uuid.UUID | None = None
    expected_chapter_id: uuid.UUID | None = None
    actual_chapter_id: uuid.UUID | None = None
    notes: str = ""
    source_quote: str = ""
    source_start: int | None = None
    source_end: int | None = None
    character_ids: list[uuid.UUID] = []


class ForeshadowUpdate(ForeshadowIn):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    importance: str | None = None
    status: str | None = None


class DraftIn(BaseModel):
    instruction: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _novel(db: Session, novel_id: uuid.UUID) -> Novel:
    novel = db.get(Novel, novel_id)
    if novel is None:
        raise HTTPException(404, "小说不存在")
    return novel


def _check_refs(db: Session, novel_id: uuid.UUID, payload: ForeshadowIn | ForeshadowUpdate) -> None:
    if payload.importance is not None and payload.importance not in IMPORTANCE:
        raise HTTPException(422, "重要程度无效")
    if payload.status is not None and payload.status not in STATUSES:
        raise HTTPException(422, "伏笔状态无效")
    if payload.outline_node_id is not None:
        node = db.get(OutlineNode, payload.outline_node_id)
        if node is None or node.novel_id != novel_id:
            raise HTTPException(404, "大纲节点不存在")
    for chapter_id in (payload.plant_chapter_id, payload.expected_chapter_id, payload.actual_chapter_id):
        if chapter_id is None:
            continue
        chapter = db.get(Chapter, chapter_id)
        if chapter is None or chapter.novel_id != novel_id:
            raise HTTPException(404, "章节不存在")


def _out(row: Foreshadow, novel_title: str | None = None) -> dict:
    data = {
        "id": row.id,
        "novel_id": row.novel_id,
        "outline_node_id": row.outline_node_id,
        "name": row.name,
        "content": row.content,
        "kind": row.kind,
        "importance": row.importance,
        "status": row.status,
        "plant_chapter_id": row.plant_chapter_id,
        "expected_chapter_id": row.expected_chapter_id,
        "actual_chapter_id": row.actual_chapter_id,
        "source_quote": row.source_quote,
        "source_start": row.source_start,
        "source_end": row.source_end,
        "notes": row.notes,
        "character_ids": [item.id for item in row.characters],
        "updated_at": row.updated_at,
    }
    if novel_title is not None:
        data["novel_title"] = novel_title
    return data


def _set_characters(db: Session, row: Foreshadow, character_ids: list[uuid.UUID]) -> None:
    rows: list[Character] = []
    for character_id in character_ids:
        item = db.get(Character, character_id)
        if item is None:
            raise HTTPException(404, "角色不存在")
        rows.append(item)
    row.characters = rows


@router.get("/novels/{novel_id}/foreshadows")
def list_foreshadows(
    novel_id: uuid.UUID,
    status: str | None = None,
    importance: str | None = None,
    db: Session = Depends(get_db),
) -> list[dict]:
    _novel(db, novel_id)
    query = select(Foreshadow).where(Foreshadow.novel_id == novel_id)
    if status:
        query = query.where(Foreshadow.status == status)
    if importance:
        query = query.where(Foreshadow.importance == importance)
    rows = db.scalars(query.order_by(Foreshadow.updated_at.desc())).all()
    return [_out(row) for row in rows]


@router.post("/novels/{novel_id}/foreshadows", status_code=201)
def create_foreshadow(novel_id: uuid.UUID, payload: ForeshadowIn, db: Session = Depends(get_db)) -> dict:
    _novel(db, novel_id)
    _check_refs(db, novel_id, payload)
    data = payload.model_dump()
    character_ids = data.pop("character_ids")
    row = Foreshadow(novel_id=novel_id, **data)
    row.name = payload.name.strip()
    _set_characters(db, row, character_ids)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/foreshadows/{foreshadow_id}")
def update_foreshadow(foreshadow_id: uuid.UUID, payload: ForeshadowUpdate, db: Session = Depends(get_db)) -> dict:
    row = db.get(Foreshadow, foreshadow_id)
    if row is None:
        raise HTTPException(404, "伏笔不存在")
    data = payload.model_dump(exclude_unset=True)
    _check_refs(db, row.novel_id, ForeshadowIn(
        name=data.get("name", row.name),
        content=data.get("content", row.content),
        kind=data.get("kind", row.kind),
        importance=data.get("importance", row.importance),
        status=data.get("status", row.status),
        outline_node_id=data.get("outline_node_id", row.outline_node_id),
        plant_chapter_id=data.get("plant_chapter_id", row.plant_chapter_id),
        expected_chapter_id=data.get("expected_chapter_id", row.expected_chapter_id),
        actual_chapter_id=data.get("actual_chapter_id", row.actual_chapter_id),
        notes=data.get("notes", row.notes),
    ))
    character_ids = data.pop("character_ids", None)
    for key, value in data.items():
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(row, key, value)
    if character_ids is not None:
        _set_characters(db, row, character_ids)
    row.updated_at = _now()
    db.commit()
    db.refresh(row)
    return _out(row)


@router.delete("/foreshadows/{foreshadow_id}", status_code=204)
def delete_foreshadow(foreshadow_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    row = db.get(Foreshadow, foreshadow_id)
    if row is None:
        raise HTTPException(404, "伏笔不存在")
    db.delete(row)
    db.commit()


@router.get("/inbox/foreshadows")
def inbox_foreshadows(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Foreshadow, Novel.title)
        .join(Novel, Novel.id == Foreshadow.novel_id)
        .where(Foreshadow.status.in_(OPEN_STATUSES))
        .order_by(Foreshadow.updated_at.desc())
    ).all()
    return [_out(row, title) for row, title in rows]


@router.post("/novels/{novel_id}/foreshadows/draft")
async def draft_foreshadow(novel_id: uuid.UUID, payload: DraftIn, db: Session = Depends(get_db)) -> dict:
    novel = _novel(db, novel_id)
    try:
        text, provider = await complete_text("continue", payload.instruction or novel.summary or novel.title, novel.title)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    if provider == "demo":
        suggestion = {
            "name": "未说完的名字",
            "content": f"有人在《{novel.title}》里听见一个不该出现的名字，却还不知道它指向谁。",
            "kind": "人物",
            "importance": "medium",
            "status": "planned",
            "notes": text,
        }
    else:
        suggestion = {
            "name": "模型建议的伏笔",
            "content": text,
            "kind": "",
            "importance": "medium",
            "status": "planned",
            "notes": "",
        }
    return {"provider": provider, "suggestion": suggestion}


@router.post("/novels/{novel_id}/foreshadows/review")
async def review_foreshadows(novel_id: uuid.UUID, kind: str = "forgotten", db: Session = Depends(get_db)) -> dict:
    if kind not in {"forgotten", "payoff", "conflict"}:
        raise HTTPException(422, "检查类型无效")
    novel = _novel(db, novel_id)
    rows = list(db.scalars(select(Foreshadow).where(Foreshadow.novel_id == novel_id)).all())
    open_rows = [row for row in rows if row.status in OPEN_STATUSES]
    try:
        text, provider = await complete_text("conflict", novel.summary or novel.title, "伏笔：" + "、".join(row.name for row in rows))
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    if kind == "forgotten":
        findings = [
            {
                "foreshadow_id": row.id,
                "name": row.name,
                "reason": "这条伏笔已经埋下，还没有实际回收章节。",
                "proposed_status": "pending_payoff",
            }
            for row in open_rows
        ]
        report = "确认后才会把列出的伏笔改为待回收。" if findings else "没有已埋设或待回收的伏笔。这只是检查结果，不会改状态。"
    elif kind == "payoff":
        findings = [
            {
                "foreshadow_id": row.id,
                "name": row.name,
                "reason": "已有实际回收章节，回收和埋下位置可以对照。" if row.actual_chapter_id else "还没有实际回收位置，现在谈回收合理性缺少落点。",
                "proposed_status": None,
            }
            for row in rows
        ]
        report = "这是回收检查。确认不会自动改状态。"
    else:
        findings = [
            {
                "foreshadow_id": row.id,
                "name": row.name,
                "reason": text if provider != "demo" else "只对照了伏笔自己的记录，没有发现和埋下、回收位置互相矛盾的状态。",
                "proposed_status": None,
            }
            for row in rows
        ]
        report = "这是冲突检查。确认不会自动改伏笔正文。"
    return {"provider": provider, "report": report, "findings": findings}
