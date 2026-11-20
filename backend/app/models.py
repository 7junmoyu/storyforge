import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


novel_worlds = Table(
    "novel_worlds",
    Base.metadata,
    Column("novel_id", ForeignKey("novels.id", ondelete="CASCADE"), primary_key=True),
    Column("world_id", ForeignKey("worlds.id", ondelete="RESTRICT"), primary_key=True),
)


class World(Base):
    __tablename__ = "worlds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    novels: Mapped[list["Novel"]] = relationship(secondary=novel_worlds, back_populates="worlds")


class Novel(Base):
    __tablename__ = "novels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft")
    target_words: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    worlds: Mapped[list[World]] = relationship(secondary=novel_worlds, back_populates="novels")
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="novel",
        cascade="all, delete-orphan",
        order_by="Chapter.position",
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    novel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("novels.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="<p></p>")
    position: Mapped[int] = mapped_column(Integer, default=1)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    novel: Mapped[Novel] = relationship(back_populates="chapters")
    revisions: Mapped[list["ChapterRevision"]] = relationship(
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterRevision.created_at.desc()",
    )


class ChapterRevision(Base):
    __tablename__ = "chapter_revisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="revisions")


class AiSuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    source_text: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    provider: Mapped[str] = mapped_column(String(32), default="demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
