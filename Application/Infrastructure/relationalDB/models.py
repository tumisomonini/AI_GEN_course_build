from sqlalchemy import Integer, String, Text, Float, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import List, Optional
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    courses: Mapped[List['Course']] = relationship('Course', back_populates='creator')


class Course(Base):
    __tablename__ = 'courses'

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    audience: Mapped[Optional[str]] = mapped_column(String(255))
    created_by_id: Mapped[Optional[int]] = mapped_column('created_by', Integer, ForeignKey('users.user_id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    status: Mapped[str] = mapped_column(String(50), default='draft')

    creator: Mapped[Optional[User]] = relationship('User', back_populates='courses')
    chapters: Mapped[List['Chapter']] = relationship('Chapter', back_populates='course', cascade='all, delete-orphan')
    syllabus: Mapped[List['Syllabus']] = relationship('Syllabus', back_populates='course', cascade='all, delete-orphan')
    runs: Mapped[List['Run']] = relationship('Run', back_populates='course', cascade='all, delete-orphan')


class Chapter(Base):
    __tablename__ = 'chapters'

    chapter_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    chapter_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    status: Mapped[str] = mapped_column(String(50), default='pending')

    __table_args__ = (UniqueConstraint('course_id', 'title', name='unique_course_chapter'),)

    course: Mapped[Course] = relationship('Course', back_populates='chapters')
    approvals: Mapped[List['Approval']] = relationship('Approval', back_populates='chapter')


class Syllabus(Base):
    __tablename__ = 'syllabus'

    syllabus_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    content: Mapped[str] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    status: Mapped[str] = mapped_column(String(50), default='draft')

    course: Mapped[Course] = relationship('Course', back_populates='syllabus')


class Run(Base):
    __tablename__ = 'runs'

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey('courses.course_id', ondelete='CASCADE'), nullable=False)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50), default='running')

    course: Mapped[Course] = relationship('Course', back_populates='runs')
    logs: Mapped[List['Log']] = relationship('Log', back_populates='run', cascade='all, delete-orphan')
    metrics: Mapped[List['Metric']] = relationship('Metric', back_populates='run', cascade='all, delete-orphan')
    approvals: Mapped[List['Approval']] = relationship('Approval', back_populates='run', cascade='all, delete-orphan')


class Log(Base):
    __tablename__ = 'logs'

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(50), default='info')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    run: Mapped[Run] = relationship('Run', back_populates='logs')


class Approval(Base):
    __tablename__ = 'approvals'

    approval_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    chapter_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('chapters.chapter_id', ondelete='CASCADE'))
    approver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.user_id'))
    status: Mapped[str] = mapped_column(String(50), default='pending')
    comments: Mapped[Optional[str]] = mapped_column(Text)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    run: Mapped[Run] = relationship('Run', back_populates='approvals')
    chapter: Mapped[Optional[Chapter]] = relationship('Chapter', back_populates='approvals')


class Review(Base):
    __tablename__ = 'reviews'

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(Integer, ForeignKey('chapters.chapter_id', ondelete='CASCADE'), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())


class Metric(Base):
    __tablename__ = 'metrics'

    metric_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255))
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    run: Mapped[Run] = relationship('Run', back_populates='metrics')


class Cost(Base):
    __tablename__ = 'costs'

    cost_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255))
    cost_type: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())


class Artifact(Base):
    __tablename__ = 'artifacts'

    artifact_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())


class Export(Base):
    __tablename__ = 'exports'

    export_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey('runs.run_id', ondelete='CASCADE'), nullable=False)
    artifact_id: Mapped[int] = mapped_column(Integer, ForeignKey('artifacts.artifact_id', ondelete='CASCADE'), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    status: Mapped[str] = mapped_column(String(50), default='pending')


class Session(Base):
    __tablename__ = 'sessions'

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data: Mapped[str] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
