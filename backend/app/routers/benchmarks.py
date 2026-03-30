import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session, get_db
from app.engine.runner import BenchmarkRunner, get_active_runner
from app.engine.snapshots import ws_manager
from app.models.benchmark import Benchmark, BenchmarkRequest
from app.models.scenario import Scenario, ScenarioProfile
from app.schemas.benchmark import BenchmarkCreate, BenchmarkRead, BenchmarkSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_benchmark_or_404(benchmark_id: UUID, db: AsyncSession) -> Benchmark:
    result = await db.execute(
        select(Benchmark).where(Benchmark.id == benchmark_id)
    )
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


def _build_scenario_snapshot(scenario, scenario_profiles) -> dict:
    """Freeze the scenario config into a JSON-serializable dict."""
    profiles_data = []
    for sp in scenario_profiles:
        profile = sp.profile
        # Serialize the full profile data needed by the runner
        templates = []
        for t in profile.conversation_templates:
            follow_ups = [
                {"content": fu.content, "is_universal": fu.is_universal}
                for fu in t.follow_ups
            ]
            templates.append({
                "starter_prompt": t.starter_prompt,
                "category": t.category,
                "follow_ups": follow_ups,
            })

        universal_fus = [
            {"content": fu.content, "is_universal": True}
            for fu in profile.follow_up_prompts
            if fu.is_universal
        ]

        variables = [
            {"name": v.name, "values": v.values}
            for v in profile.template_variables
        ]

        profiles_data.append({
            "profile": {
                "id": str(profile.id),
                "name": profile.name,
                "slug": profile.slug,
                "behavior_defaults": profile.behavior_defaults,
                "conversation_templates": templates,
                "follow_up_prompts": universal_fus,
                "template_variables": variables,
            },
            "user_count": sp.user_count,
            "behavior_overrides": sp.behavior_overrides,
        })

    return {
        "scenario_id": str(scenario.id),
        "name": scenario.name,
        "endpoint_url": scenario.endpoint_url,
        "api_key": scenario.api_key,
        "model_name": scenario.model_name,
        "llm_params": scenario.llm_params,
        "load_config": scenario.load_config,
        "max_concurrency": scenario.max_concurrency,
        "profiles": profiles_data,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def start_benchmark(body: BenchmarkCreate, db: AsyncSession = Depends(get_db)):
    """Start a new benchmark run for a scenario."""
    from app.models.profile import (
        ConversationTemplate,
        FollowUpPrompt,
        Profile,
        TemplateVariable,
    )

    # Load scenario with profiles (shallow first)
    result = await db.execute(
        select(Scenario)
        .where(Scenario.id == body.scenario_id)
        .options(selectinload(Scenario.profiles).selectinload(ScenarioProfile.profile))
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Collect profile IDs, then load full profile data with all nested relations
    profile_ids = [sp.profile.id for sp in scenario.profiles]
    if profile_ids:
        profiles_result = await db.execute(
            select(Profile)
            .where(Profile.id.in_(profile_ids))
            .options(
                selectinload(Profile.conversation_templates)
                .selectinload(ConversationTemplate.follow_ups),
                selectinload(Profile.follow_up_prompts),
                selectinload(Profile.template_variables),
            )
        )
        full_profiles = {p.id: p for p in profiles_result.scalars().all()}

        # Swap in the fully-loaded profiles
        for sp in scenario.profiles:
            if sp.profile.id in full_profiles:
                sp.profile = full_profiles[sp.profile.id]

    # Build frozen snapshot
    snapshot = _build_scenario_snapshot(scenario, scenario.profiles)

    # Create benchmark row
    benchmark = Benchmark(
        scenario_id=body.scenario_id,
        status="pending",
        scenario_snapshot=snapshot,
    )
    db.add(benchmark)
    await db.flush()
    await db.refresh(benchmark)
    await db.commit()

    # Launch runner in background
    runner = BenchmarkRunner(
        benchmark_id=benchmark.id,
        scenario_snapshot=snapshot,
        session_factory=async_session,
    )
    asyncio.create_task(runner.run())

    return {
        "data": BenchmarkRead(
            id=benchmark.id,
            scenario_id=benchmark.scenario_id,
            status=benchmark.status,
            scenario_snapshot=benchmark.scenario_snapshot,
            results_summary=benchmark.results_summary,
            error_message=benchmark.error_message,
            started_at=benchmark.started_at,
            completed_at=benchmark.completed_at,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
            scenario_name=snapshot.get("name", ""),
        ).model_dump(mode="json")
    }


@router.get("")
async def list_benchmarks(db: AsyncSession = Depends(get_db)):
    """List all benchmark runs."""
    # Count requests per benchmark via subquery
    req_count = (
        select(
            BenchmarkRequest.benchmark_id,
            func.count(BenchmarkRequest.id).label("total_requests"),
        )
        .group_by(BenchmarkRequest.benchmark_id)
        .subquery()
    )

    result = await db.execute(
        select(Benchmark, req_count.c.total_requests)
        .outerjoin(req_count, Benchmark.id == req_count.c.benchmark_id)
        .order_by(Benchmark.created_at.desc())
    )
    rows = result.all()

    items = []
    for bench, total_reqs in rows:
        duration = None
        if bench.started_at and bench.completed_at:
            duration = (bench.completed_at - bench.started_at).total_seconds()

        items.append(
            BenchmarkSummary(
                id=bench.id,
                scenario_id=bench.scenario_id,
                scenario_name=bench.scenario_snapshot.get("name", "") if bench.scenario_snapshot else "",
                status=bench.status,
                total_requests=total_reqs or 0,
                duration_seconds=duration,
                created_at=bench.created_at,
            ).model_dump(mode="json")
        )

    return {"data": items, "meta": {"total": len(items)}}


@router.get("/{benchmark_id}")
async def get_benchmark(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get benchmark details including results summary."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)

    return {
        "data": BenchmarkRead(
            id=benchmark.id,
            scenario_id=benchmark.scenario_id,
            status=benchmark.status,
            scenario_snapshot=benchmark.scenario_snapshot,
            results_summary=benchmark.results_summary,
            error_message=benchmark.error_message,
            started_at=benchmark.started_at,
            completed_at=benchmark.completed_at,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
            scenario_name=benchmark.scenario_snapshot.get("name", "") if benchmark.scenario_snapshot else "",
        ).model_dump(mode="json")
    }


@router.delete("/{benchmark_id}")
async def delete_benchmark(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a benchmark and all its data. Aborts if running."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)

    # Abort if running
    runner = get_active_runner(benchmark_id)
    if runner:
        runner.abort()

    await db.delete(benchmark)
    await db.commit()
    return {"data": {"deleted": True}}


@router.post("/{benchmark_id}/abort")
async def abort_benchmark(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Abort a running benchmark."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)

    if benchmark.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Benchmark is not running")

    runner = get_active_runner(benchmark_id)
    if runner:
        runner.abort()
        return {"data": {"status": "aborting"}}

    # Runner not found (maybe already finished) — update status directly
    benchmark.status = "aborted"
    benchmark.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"data": {"status": "aborted"}}


@router.websocket("/{benchmark_id}/live")
async def benchmark_live(websocket: WebSocket, benchmark_id: UUID):
    """WebSocket endpoint for live metric snapshots."""
    await ws_manager.connect(benchmark_id, websocket)
    try:
        # Keep connection alive until client disconnects
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(benchmark_id, websocket)
