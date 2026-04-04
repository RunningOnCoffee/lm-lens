import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Scenario, ScenarioProfile
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioProfileRead,
    ScenarioRead,
    ScenarioSummary,
    ScenarioUpdate,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_scenario_or_404(
    scenario_id: UUID, db: AsyncSession, *, eager: bool = False
) -> Scenario:
    stmt = select(Scenario).where(Scenario.id == scenario_id)
    if eager:
        stmt = stmt.options(
            selectinload(Scenario.profiles).selectinload(ScenarioProfile.profile)
        )
    result = await db.execute(stmt)
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


async def _next_clone_name(source_name: str, db: AsyncSession) -> str:
    base = re.sub(r"\s*\(\d+\)\s*$", "", source_name).strip()
    pattern = f"{base} (%"
    result = await db.execute(
        select(Scenario.name).where(Scenario.name.like(pattern))
    )
    existing = {row[0] for row in result.all()}
    n = 1
    while f"{base} ({n})" in existing:
        n += 1
    return f"{base} ({n})"


def _compute_weight(sp: ScenarioProfile, total_users: int) -> float:
    """Compute proportional weight from user_count."""
    if total_users == 0:
        return 0.0
    return round(sp.user_count / total_users, 4)


def _build_profile_read(sp: ScenarioProfile, total_users: int) -> dict:
    return ScenarioProfileRead(
        id=sp.id,
        scenario_id=sp.scenario_id,
        profile_id=sp.profile_id,
        user_count=sp.user_count,
        weight=_compute_weight(sp, total_users),
        behavior_overrides=sp.behavior_overrides,
        profile_name=sp.profile.name if sp.profile else "",
        created_at=sp.created_at,
    ).model_dump()


def _build_scenario_read(scenario: Scenario) -> dict:
    total_users = sum(sp.user_count for sp in scenario.profiles)
    data = ScenarioRead.model_validate(scenario).model_dump()
    data["profiles"] = [_build_profile_read(sp, total_users) for sp in scenario.profiles]
    return data


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
async def list_scenarios(db: AsyncSession = Depends(get_db)) -> dict:
    profile_count_sub = (
        select(func.count())
        .where(ScenarioProfile.scenario_id == Scenario.id)
        .correlate(Scenario)
        .scalar_subquery()
    )
    total_users_sub = (
        select(func.coalesce(func.sum(ScenarioProfile.user_count), 0))
        .where(ScenarioProfile.scenario_id == Scenario.id)
        .correlate(Scenario)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Scenario, profile_count_sub.label("profile_count"), total_users_sub.label("total_users"))
        .order_by(Scenario.created_at.desc())
    )
    rows = result.all()

    summaries = [
        ScenarioSummary(
            id=s.id,
            name=s.name,
            description=s.description,
            profile_count=pc or 0,
            total_users=tu or 0,
            duration_seconds=(s.load_config or {}).get("duration_seconds", 0),
            test_mode=(s.load_config or {}).get("test_mode", "stress"),
            created_at=s.created_at,
        ).model_dump()
        for s, pc, tu in rows
    ]

    return {"data": summaries, "meta": {"total": len(summaries)}}


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@router.get("/{scenario_id}", response_model=dict)
async def get_scenario(scenario_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    scenario = await _get_scenario_or_404(scenario_id, db, eager=True)
    return {"data": _build_scenario_read(scenario)}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201)
async def create_scenario(
    body: ScenarioCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    scenario = Scenario(
        name=body.name,
        description=body.description,
        llm_params=body.llm_params.model_dump(),
        load_config=body.load_config.model_dump(),
        max_concurrency=body.max_concurrency,
    )
    db.add(scenario)
    await db.flush()

    for sp_data in body.profiles:
        db.add(
            ScenarioProfile(
                scenario_id=scenario.id,
                profile_id=sp_data.profile_id,
                user_count=sp_data.user_count,
                behavior_overrides=(
                    sp_data.behavior_overrides.model_dump()
                    if sp_data.behavior_overrides
                    else None
                ),
            )
        )

    await db.commit()

    scenario = await _get_scenario_or_404(scenario.id, db, eager=True)
    return {"data": _build_scenario_read(scenario)}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.put("/{scenario_id}", response_model=dict)
async def update_scenario(
    scenario_id: UUID,
    body: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    scenario = await _get_scenario_or_404(scenario_id, db)

    if body.name is not None:
        scenario.name = body.name
    if body.description is not None:
        scenario.description = body.description
    if body.llm_params is not None:
        scenario.llm_params = body.llm_params.model_dump()
    if body.load_config is not None:
        scenario.load_config = body.load_config.model_dump()
    if body.max_concurrency is not None:
        scenario.max_concurrency = body.max_concurrency

    if body.profiles is not None:
        await db.execute(
            delete(ScenarioProfile).where(
                ScenarioProfile.scenario_id == scenario.id
            )
        )
        await db.flush()
        for sp_data in body.profiles:
            db.add(
                ScenarioProfile(
                    scenario_id=scenario.id,
                    profile_id=sp_data.profile_id,
                    user_count=sp_data.user_count,
                    behavior_overrides=(
                        sp_data.behavior_overrides.model_dump()
                        if sp_data.behavior_overrides
                        else None
                    ),
                )
            )

    await db.commit()

    scenario = await _get_scenario_or_404(scenario.id, db, eager=True)
    return {"data": _build_scenario_read(scenario)}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{scenario_id}", response_model=dict)
async def delete_scenario(
    scenario_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    scenario = await _get_scenario_or_404(scenario_id, db)
    await db.delete(scenario)
    await db.commit()
    return {"data": {"deleted": True}}


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

@router.post("/{scenario_id}/clone", response_model=dict, status_code=201)
async def clone_scenario(
    scenario_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    source = await _get_scenario_or_404(scenario_id, db, eager=True)

    clone_name = await _next_clone_name(source.name, db)
    clone = Scenario(
        name=clone_name,
        description=source.description,
        llm_params=dict(source.llm_params),
        load_config=dict(source.load_config),
        max_concurrency=source.max_concurrency,
    )
    db.add(clone)
    await db.flush()

    for sp in source.profiles:
        db.add(
            ScenarioProfile(
                scenario_id=clone.id,
                profile_id=sp.profile_id,
                user_count=sp.user_count,
                behavior_overrides=(
                    dict(sp.behavior_overrides) if sp.behavior_overrides else None
                ),
            )
        )

    await db.commit()

    clone = await _get_scenario_or_404(clone.id, db, eager=True)
    return {"data": _build_scenario_read(clone)}
