import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.profile import Profile  # noqa: F401 — needed for relationship


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    llm_params: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {
            "max_tokens": None,
            "temperature": 0.7,
            "top_p": 1.0,
            "stop": [],
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }
    )
    load_config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {
            "test_mode": "stress",
            "duration_seconds": 60,
            "ramp_users_per_step": 1,
            "ramp_interval_seconds": 10,
            "breaking_criteria": None,
        }
    )
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    profiles: Mapped[list["ScenarioProfile"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan"
    )


class ScenarioProfile(Base):
    __tablename__ = "scenario_profiles"
    __table_args__ = (
        UniqueConstraint("scenario_id", "profile_id", name="uq_scenario_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    behavior_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    scenario: Mapped["Scenario"] = relationship(back_populates="profiles")
    profile: Mapped["Profile"] = relationship(lazy="selectin")
