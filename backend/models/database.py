from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

#in this file, we create the tables for the database using SQLAlchemy ORM. Each class represents a table in the database, and each attribute of the class represents a column in the table. The relationships between tables are also defined here.

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    github_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    avatar_url = Column(String)
    access_token = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    repositories = relationship("Repository", back_populates="user")


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    github_repo_id = Column(String, unique=True)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    webhook_id = Column(String)
    health_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="repositories")
    reviews = relationship("Review", back_populates="repository")
    diary_entries = relationship("DiaryEntry", back_populates="repository")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    commit_sha = Column(String)
    pr_number = Column(Integer)
    files_changed = Column(Text)
    ai_review = Column(Text)
    health_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="reviews")


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"))
    commit_sha = Column(String)
    summary = Column(Text)
    changes_made = Column(Text)
    senior_feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="diary_entries")