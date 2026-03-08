from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.postgres.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Clerk User ID
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    projects = relationship("Project", back_populates="user")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="projects")
    lorebooks = relationship("Lorebook", back_populates="project")
    chats = relationship("Chat", back_populates="project")

class Lorebook(Base):
    __tablename__ = "lorebooks"

    id = Column(String, primary_key=True, index=True) # UUID
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    term = Column(String, nullable=False, index=True) # Tên chiêu thức / thuật ngữ
    definition = Column(String, nullable=False) # Định nghĩa
    metadata_json = Column(JSON, default={}) # Dữ liệu phụ
    
    # 🌟 Linh hồn của PostgreSQL Full-Text Search
    search_vector = Column(TSVECTOR)
    
    project = relationship("Project", back_populates="lorebooks")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, index=True) # UUID
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    role = Column(String, nullable=False) # "user", "assistant", "system"
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    project = relationship("Project", back_populates="chats")

