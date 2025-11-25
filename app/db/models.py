from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class CompanySize(str, enum.Enum):
    small = "small"
    medium = "medium"
    large = "large"


class VacancyStatus(str, enum.Enum):
    new = "new"
    sent = "sent"
    skipped = "skipped"
    applied = "applied"


class DocumentType(str, enum.Enum):
    resume = "resume"
    cover_letter = "cover_letter"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    desired_position: Mapped[str | None] = mapped_column(String(255))
    skills: Mapped[str | None] = mapped_column(Text)
    base_resume: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    search_filters = relationship("SearchFilter", back_populates="user", uselist=False)


class SearchFilter(Base):
    __tablename__ = "search_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    position: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    min_salary: Mapped[int | None] = mapped_column(Integer)

    metro_stations: Mapped[list[str] | None] = mapped_column(JSON)
    freshness_days: Mapped[int] = mapped_column(Integer, default=1)

    employment_types: Mapped[list[str] | None] = mapped_column(
        JSON
    )  # full, part, remote
    experience_level: Mapped[str | None] = mapped_column(String(50))
    only_direct_employers: Mapped[bool] = mapped_column(Boolean, default=True)
    company_size: Mapped[CompanySize | None]
    only_top_companies: Mapped[bool] = mapped_column(Boolean, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="search_filters")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    hh_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(255))
    salary_from: Mapped[int | None] = mapped_column(Integer)
    salary_to: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(String(512))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    raw: Mapped[dict | None] = mapped_column(JSON)


class UserVacancy(Base):
    __tablename__ = "user_vacancies"
    __table_args__ = (
        UniqueConstraint("user_id", "vacancy_id", name="uq_user_vacancy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE")
    )
    status: Mapped[VacancyStatus] = mapped_column(
        Enum(VacancyStatus), default=VacancyStatus.new
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    vacancy_id: Mapped[int | None] = mapped_column(
        ForeignKey("vacancies.id", ondelete="SET NULL")
    )
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
