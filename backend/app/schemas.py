import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class WorldIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = ""


class WorldOut(BaseModel):
    id: uuid.UUID
    name: str
    summary: str
    novel_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NovelIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    genre: str = ""
    status: str = "draft"
    target_words: int = Field(default=0, ge=0)
    tags: str = ""
    cover_url: str = ""
    world_id: uuid.UUID | None = None
    world_ids: list[uuid.UUID] | None = None
    character_ids: list[uuid.UUID] = []


class NovelUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    genre: str | None = None
    status: str | None = None
    target_words: int | None = Field(default=None, ge=0)
    tags: str | None = None
    cover_url: str | None = None
    archived: bool | None = None
    world_id: uuid.UUID | None = None
    world_ids: list[uuid.UUID] | None = None
    clear_world: bool = False
    character_ids: list[uuid.UUID] | None = None


class WorldBrief(BaseModel):
    id: uuid.UUID
    name: str


class NovelOut(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    genre: str
    status: str
    target_words: int
    tags: str = ""
    cover_url: str = ""
    archived: bool = False
    word_count: int = 0
    chapter_count: int = 0
    worlds: list[WorldBrief] = []
    characters: list[WorldBrief] = []
    created_at: datetime
    updated_at: datetime


class ChapterIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    volume_id: uuid.UUID | None = None


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    volume_id: uuid.UUID | None = None
    clear_volume: bool = False


class ChapterOut(BaseModel):
    id: uuid.UUID
    novel_id: uuid.UUID
    volume_id: uuid.UUID | None = None
    title: str
    content: str
    position: int
    word_count: int
    updated_at: datetime


class ChapterBrief(BaseModel):
    id: uuid.UUID
    title: str
    position: int
    word_count: int
    volume_id: uuid.UUID | None = None
    updated_at: datetime


class NovelDetail(NovelOut):
    chapters: list[ChapterBrief] = []


class VolumeIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class VolumeOut(BaseModel):
    id: uuid.UUID
    novel_id: uuid.UUID
    title: str
    position: int


class ImportedChapter(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = "<p></p>"


class NovelImport(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    genre: str = ""
    tags: str = ""
    status: str = "draft"
    target_words: int = Field(default=0, ge=0)
    chapters: list[ImportedChapter] = []


class RevisionOut(BaseModel):
    id: uuid.UUID
    word_count: int
    created_at: datetime


class AiRequest(BaseModel):
    action: str = Field(pattern="^(continue|expand|polish|rewrite|shorten|style|dialogue|character|plot|conflict)$")
    selected_text: str = ""


class AiSuggestionOut(BaseModel):
    id: uuid.UUID
    action: str
    source_text: str
    suggestion: str
    status: str
    provider: str
    created_at: datetime
