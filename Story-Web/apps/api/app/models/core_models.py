import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgres.base import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    clerk_id = Column(String, unique=True, index=True, nullable=False)  # ID từ Clerk
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="projects")
    lorebooks = relationship("Lorebook", back_populates="project", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="project", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan")


class Chat(Base):
    """Session hội thoại (chứa nhiều ChatMessage)"""
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False, default="Cuộc trò chuyện mới")
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")


class ChatMessage(Base):
    """Từng tin nhắn trong một Chat session"""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "ai" | "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")


class Chapter(Base):
    """Chương truyện đã chốt"""
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="chapters")


class Lorebook(Base):
    """Từ điển thuật ngữ, chiêu thức, luật lệ do tác giả định nghĩa — hỗ trợ FTS"""
    __tablename__ = "lorebooks"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    keyword = Column(String, nullable=False, index=True)     # VD: "Hắc Lôi"
    category = Column(String, nullable=False, default="Rule") # "Skill" | "Character" | "Rule" | "Location"
    description = Column(Text, nullable=False)
    fts_vector = Column(TSVECTOR)                            # Tự động build bởi Postgres trigger
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="lorebooks")

    # Index cho FTS search
    __table_args__ = (
        Index("ix_lorebooks_fts", "fts_vector", postgresql_using="gin"),
    )
