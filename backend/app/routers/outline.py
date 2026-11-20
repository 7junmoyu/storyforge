import html
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import complete_text
from app.database import get_db
from app.models import Chapter, Character, Novel, OutlineNode, World
from app.textutil import count_words, plain_text

router = APIRouter(tags=["outline"])
STATUSES = {"pending", "active", "done"}


class OutlineIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None
    content: str = ""
    notes: str = ""
    status: str = "pending"
    world_id: uuid.UUID | None = None
    character_ids: list[uuid.UUID] = []


class OutlineUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: uuid.UUID | None = None
    clear_parent: bool = False
    content: str | None = None
    notes: str | None = None
    status: str | None = None
    world_id: uuid.UUID | None = None
    clear_world: bool = False
    character_ids: list[uuid.UUID] | None = None


class MoveIn(BaseModel):
    direction: str = Field(pattern="^(up|down)$")


class ReorderItem(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None = None
    position: int = Field(ge=1)


class DraftIn(BaseModel):
    instruction: str = ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _novel(db: Session, novel_id: uuid.UUID) -> Novel:
    novel = db.get(Novel, novel_id)
    if novel is None:
        raise HTTPException(404, "小说不存在")
    return novel


def _node(db: Session, node_id: uuid.UUID) -> OutlineNode:
    node = db.get(OutlineNode, node_id)
    if node is None:
        raise HTTPException(404, "大纲节点不存在")
    return node


def _out(node: OutlineNode) -> dict:
    return {
        "id": node.id,
        "novel_id": node.novel_id,
        "parent_id": node.parent_id,
        "chapter_id": node.chapter_id,
        "world_id": node.world_id,
        "title": node.title,
        "content": node.content,
        "notes": node.notes,
        "status": node.status,
        "position": node.position,
        "character_ids": [row.id for row in node.characters],
        "updated_at": node.updated_at,
    }


def _set_characters(db: Session, node: OutlineNode, character_ids: list[uuid.UUID]) -> None:
    rows: list[Character] = []
    for character_id in character_ids:
        row = db.get(Character, character_id)
        if row is None:
            raise HTTPException(404, "角色不存在")
        rows.append(row)
    node.characters = rows


def _siblings(db: Session, novel_id: uuid.UUID, parent_id: uuid.UUID | None) -> list[OutlineNode]:
    query = select(OutlineNode).where(OutlineNode.novel_id == novel_id)
    if parent_id is None:
        query = query.where(OutlineNode.parent_id.is_(None))
    else:
        query = query.where(OutlineNode.parent_id == parent_id)
    return list(db.scalars(query.order_by(OutlineNode.position, OutlineNode.created_at)).all())


def _ensure_parent(db: Session, novel_id: uuid.UUID, parent_id: uuid.UUID | None, node_id: uuid.UUID | None = None) -> None:
    if parent_id is None:
        return
    parent = db.get(OutlineNode, parent_id)
    if parent is None or parent.novel_id != novel_id:
        raise HTTPException(404, "父节点不存在")
    if node_id is None:
        return
    current = parent
    while current is not None:
        if current.id == node_id:
            raise HTTPException(422, "不能把节点移到自己的子节点下")
        current = db.get(OutlineNode, current.parent_id) if current.parent_id else None


@router.get("/novels/{novel_id}/outline")
def list_outline(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    _novel(db, novel_id)
    rows = db.scalars(select(OutlineNode).where(OutlineNode.novel_id == novel_id).order_by(OutlineNode.position)).all()
    return [_out(row) for row in rows]


@router.post("/novels/{novel_id}/outline", status_code=201)
def create_outline(novel_id: uuid.UUID, payload: OutlineIn, db: Session = Depends(get_db)) -> dict:
    _novel(db, novel_id)
    if payload.status not in STATUSES:
        raise HTTPException(422, "大纲状态无效")
    _ensure_parent(db, novel_id, payload.parent_id)
    position = db.scalar(
        select(func.coalesce(func.max(OutlineNode.position), 0)).where(
            OutlineNode.novel_id == novel_id,
            OutlineNode.parent_id.is_(None) if payload.parent_id is None else OutlineNode.parent_id == payload.parent_id,
        )
    )
    if payload.world_id is not None and db.get(World, payload.world_id) is None:
        raise HTTPException(404, "世界不存在")
    node = OutlineNode(
        novel_id=novel_id,
        parent_id=payload.parent_id,
        world_id=payload.world_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        notes=payload.notes.strip(),
        status=payload.status,
        position=int(position or 0) + 1,
    )
    _set_characters(db, node, payload.character_ids)
    db.add(node)
    db.commit()
    db.refresh(node)
    return _out(node)


@router.patch("/outline-nodes/{node_id}")
def update_outline(node_id: uuid.UUID, payload: OutlineUpdate, db: Session = Depends(get_db)) -> dict:
    node = _node(db, node_id)
    if payload.status is not None and payload.status not in STATUSES:
        raise HTTPException(422, "大纲状态无效")
    if payload.clear_parent:
        _ensure_parent(db, node.novel_id, None, node.id)
        node.parent_id = None
    elif payload.parent_id is not None:
        _ensure_parent(db, node.novel_id, payload.parent_id, node.id)
        node.parent_id = payload.parent_id
    if payload.title is not None:
        node.title = payload.title.strip()
    if payload.content is not None:
        node.content = payload.content.strip()
    if payload.notes is not None:
        node.notes = payload.notes.strip()
    if payload.status is not None:
        node.status = payload.status
    if payload.clear_world:
        node.world_id = None
    elif payload.world_id is not None:
        world = db.get(World, payload.world_id)
        if world is None:
            raise HTTPException(404, "世界不存在")
        node.world_id = world.id
    if payload.character_ids is not None:
        _set_characters(db, node, payload.character_ids)
    node.updated_at = _now()
    db.commit()
    db.refresh(node)
    return _out(node)


@router.delete("/outline-nodes/{node_id}", status_code=204)
def delete_outline(node_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    node = _node(db, node_id)
    db.delete(node)
    db.commit()


@router.post("/outline-nodes/{node_id}/move")
def move_outline(node_id: uuid.UUID, payload: MoveIn, db: Session = Depends(get_db)) -> list[dict]:
    node = _node(db, node_id)
    siblings = _siblings(db, node.novel_id, node.parent_id)
    index = next(i for i, item in enumerate(siblings) if item.id == node.id)
    target = index - 1 if payload.direction == "up" else index + 1
    if target < 0 or target >= len(siblings):
        return [_out(item) for item in siblings]
    siblings[index], siblings[target] = siblings[target], siblings[index]
    for position, item in enumerate(siblings, start=1):
        item.position = position
    db.commit()
    return [_out(item) for item in siblings]


@router.post("/novels/{novel_id}/outline/reorder")
def reorder_outline(novel_id: uuid.UUID, items: list[ReorderItem], db: Session = Depends(get_db)) -> list[dict]:
    _novel(db, novel_id)
    rows = {row.id: row for row in db.scalars(select(OutlineNode).where(OutlineNode.novel_id == novel_id)).all()}
    if {item.id for item in items} != set(rows):
        raise HTTPException(422, "排序数据与当前大纲不一致")
    parents = {item.id: item.parent_id for item in items}
    for item in items:
        if item.parent_id is not None and item.parent_id not in rows:
            raise HTTPException(404, "父节点不存在")
        seen: set[uuid.UUID] = set()
        cursor = item.parent_id
        while cursor is not None:
            if cursor == item.id or cursor in seen:
                raise HTTPException(422, "不能把节点移到自己的子节点下")
            seen.add(cursor)
            cursor = parents.get(cursor)
    for item in items:
        rows[item.id].parent_id = item.parent_id
        rows[item.id].position = item.position
        rows[item.id].updated_at = _now()
    db.commit()
    return [_out(row) for row in rows.values()]


@router.post("/outline-nodes/{node_id}/to-chapter", status_code=201)
def outline_to_chapter(node_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    node = _node(db, node_id)
    if node.chapter_id is not None:
        chapter = db.get(Chapter, node.chapter_id)
        if chapter is not None:
            raise HTTPException(409, "这个节点已经对应一个章节")
    position = db.scalar(select(func.coalesce(func.max(Chapter.position), 0)).where(Chapter.novel_id == node.novel_id)) or 0
    body = node.content.strip()
    content_html = "".join(f"<p>{html.escape(line)}</p>" for line in body.splitlines()) or "<p></p>"
    chapter = Chapter(
        novel_id=node.novel_id,
        title=node.title,
        content=content_html,
        position=int(position) + 1,
        word_count=count_words(content_html),
    )
    db.add(chapter)
    db.flush()
    node.chapter_id = chapter.id
    node.updated_at = _now()
    db.commit()
    db.refresh(chapter)
    return {"chapter_id": chapter.id, "node": _out(node)}


@router.post("/novels/{novel_id}/outline/draft")
async def draft_outline(novel_id: uuid.UUID, payload: DraftIn, db: Session = Depends(get_db)) -> dict:
    novel = _novel(db, novel_id)
    existing = db.scalars(select(OutlineNode.title).where(OutlineNode.novel_id == novel_id)).all()
    instruction = payload.instruction.strip() or novel.summary or novel.title
    try:
        text, provider = await complete_text("continue", instruction, "已有节点：" + "、".join(existing))
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    if provider == "demo":
        nodes = [
            {"title": "开端", "content": f"{novel.title}里的人第一次碰到改变局势的事。", "children": []},
            {"title": "转折", "content": "一个旧约定露出裂缝。", "children": [{"title": "误认", "content": "有人认错了关键人物。", "children": []}]},
            {"title": "收束", "content": "选择被公开，后果留下。", "children": []},
        ]
    else:
        nodes = [{"title": "AI 建议", "content": plain_text(text), "children": []}]
    return {"provider": provider, "nodes": nodes}


@router.post("/outline-nodes/{node_id}/draft-expand")
async def expand_outline(node_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    node = _node(db, node_id)
    try:
        text, provider = await complete_text("expand", node.content or node.title, node.title)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    if provider == "demo":
        text = f"{node.title}下面还可以写清：谁在场、他为什么不能现在说破、这一步结束后谁被改变。"
    return {"provider": provider, "content": text}


@router.post("/novels/{novel_id}/outline/check")
async def check_outline(novel_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    novel = _novel(db, novel_id)
    titles = db.scalars(select(OutlineNode.title).where(OutlineNode.novel_id == novel_id)).all()
    try:
        text, provider = await complete_text("plot", "、".join(titles) or novel.title, novel.summary)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型请求失败") from exc
    if provider == "demo":
        text = "这是检查建议，还没有写入大纲。节点之间如果没有因果，后面转成章节时会显得跳。确认后只会记到备注，不改节点正文。"
    return {"provider": provider, "report": text}
