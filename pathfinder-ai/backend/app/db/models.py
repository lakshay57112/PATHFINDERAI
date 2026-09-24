"""Relational data model.

Catalog tables (Career, Skill, CareerSkill, ...) are *projections* of the YAML knowledge
files in ``backend/data``; they are re-synced on startup so new careers can be added
without touching application code. User tables are always filtered by ``user_id``.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import decrypt_str, encrypt_str
from app.db.session import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EncryptedText(TypeDecorator):
    """Text column transparently encrypted at rest with Fernet."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return decrypt_str(value) if value is not None else None


# --------------------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="password")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    profile: Mapped[Profile | None] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    interests: Mapped[list[Interest]] = relationship(cascade="all, delete-orphan", order_by="Interest.id")
    skills: Mapped[list[UserSkill]] = relationship(cascade="all, delete-orphan")
    education: Mapped[list[Education]] = relationship(cascade="all, delete-orphan")
    certificates: Mapped[list[Certificate]] = relationship(cascade="all, delete-orphan")
    projects: Mapped[list[Project]] = relationship(cascade="all, delete-orphan")
    roadmaps: Mapped[list[Roadmap]] = relationship(cascade="all, delete-orphan")
    progress: Mapped[list[Progress]] = relationship(cascade="all, delete-orphan")
    recommendations: Mapped[list[Recommendation]] = relationship(cascade="all, delete-orphan")
    chat_sessions: Mapped[list[ChatSession]] = relationship(cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    activities: Mapped[list[str]] = mapped_column(JSON, default=list)  # "what do you enjoy doing"
    work_styles: Mapped[list[str]] = mapped_column(JSON, default=list)  # "what work sounds interesting"
    subjects: Mapped[list[str]] = mapped_column(JSON, default=list)
    education_level: Mapped[str | None] = mapped_column(String(60), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    work_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    internships: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    learning_preferences: Mapped[list[str]] = mapped_column(JSON, default=list)
    hours_per_week: Mapped[int] = mapped_column(Integer, default=8)
    target_career_id: Mapped[str | None] = mapped_column(ForeignKey("careers.id", ondelete="SET NULL"), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="profile")


class Interest(Base):
    __tablename__ = "interests"
    __table_args__ = (UniqueConstraint("user_id", "domain"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    domain: Mapped[str] = mapped_column(String(40))


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str] = mapped_column(Text, default="")


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id"), Index("ix_user_skills_user", "user_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    level: Mapped[int] = mapped_column(Integer, default=0)  # 0 none · 1 beginner · 2 intermediate · 3 advanced
    unsure: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="stated")  # stated|roadmap|assessment|mentor
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str | None] = mapped_column(String(160), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(120), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    catalog_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    file_key: Mapped[str | None] = mapped_column(String(120), nullable=True)  # encrypted blob on disk
    file_mime: Mapped[str | None] = mapped_column(String(60), nullable=True)
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    technologies: Mapped[list[str]] = mapped_column(JSON, default=list)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # planned|in_progress|completed
    source: Mapped[str] = mapped_column(String(20), default="user")  # user|recommended
    template_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ------------------------------------------------------------------------ catalog
class Career(Base):
    __tablename__ = "careers"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    family: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))


class CareerSkill(Base):
    __tablename__ = "career_skills"
    __table_args__ = (UniqueConstraint("career_id", "skill_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    career_id: Mapped[str] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    target_level: Mapped[int] = mapped_column(Integer)
    importance: Mapped[str] = mapped_column(String(12))  # core|important|useful


class CareerTechnology(Base):
    __tablename__ = "career_technologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    career_id: Mapped[str] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))


class CareerResource(Base):
    __tablename__ = "career_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    career_id: Mapped[str | None] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"), nullable=True, index=True)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20))  # learn|practice|build|prove
    title: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    url: Mapped[str | None] = mapped_column(String(300), nullable=True)


# ------------------------------------------------------------------------ roadmap
class Roadmap(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (Index("ix_roadmaps_user_status", "user_id", "status"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    career_id: Mapped[str] = mapped_column(ForeignKey("careers.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|archived
    hours_per_week: Mapped[int] = mapped_column(Integer, default=8)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    steps: Mapped[list[RoadmapStep]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan", order_by="(RoadmapStep.phase_index, RoadmapStep.order)"
    )


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"
    __table_args__ = (Index("ix_steps_roadmap", "roadmap_id", "phase_index", "order"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmaps.id", ondelete="CASCADE"))
    phase_index: Mapped[int] = mapped_column(Integer)
    phase_name: Mapped[str] = mapped_column(String(80))
    order: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(20), default="skill")  # skill|project
    skill_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo|in_progress|done|skipped
    est_hours: Mapped[float] = mapped_column(Float, default=0)
    from_level: Mapped[int] = mapped_column(Integer, default=0)
    target_level: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roadmap: Mapped[Roadmap] = relationship(back_populates="steps")


class Progress(Base):
    """Evidence log: every completed item produces a piece of evidence."""

    __tablename__ = "progress"
    __table_args__ = (Index("ix_progress_user", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # skill|project|certificate|assessment|quiz|artifact
    ref_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    skill_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recs_user_kind", "user_id", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # career|resource|certificate|project
    ref_id: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# --------------------------------------------------------------------- job market
class JobMarketData(Base):
    __tablename__ = "job_market_data"
    __table_args__ = (Index("ix_jobs_filters", "career_id", "country", "remote"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(160))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    posted_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    industry: Mapped[str | None] = mapped_column(String(60), nullable=True)
    career_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    extracted: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# --------------------------------------------------------------------------- chat
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_user_kind", "user_id", "kind"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20), default="mentor")  # mentor|interview
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))  # user|assistant
    content: Mapped[str] = mapped_column(EncryptedText)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
