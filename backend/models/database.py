#importing necessary modules from SQLAlchemy and other libraries.
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float

#importing relationship function from SQLAlchemy to define relationships between tables
from sqlalchemy.orm import relationship

#importing datetime module to work with date and time
from datetime import datetime

#importing Base class from core.database module, which is the declarative base for SQLAlchemy models
from core.database import Base

#in this file, we create the tables for the database using SQLAlchemy ORM. Each class represents a table in the database, and each attribute of the class represents a column in the table. The relationships between tables are also defined here.

#by inheriting from Base, the User class becomes a SQLAlchemy model that can be used to interact with the users table in the database.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    github_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    avatar_url = Column(String)
    access_token = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    #relationship is used to define the relationship between the User and Repository models. The back_populates argument specifies the attribute on the related model that will be used to access the relationship from the other side. In this case, it allows us to access a user's repositories using user.repositories and a repository's user using repository.user.
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