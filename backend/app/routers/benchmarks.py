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
from app.models.benchmark import Benchmark, BenchmarkRequest, BenchmarkSnapshot
from app.models.endpoint import Endpoint
from app.models.scenario import Scenario, ScenarioProfile
from app.schemas.benchmark import BenchmarkCreate, BenchmarkRead, BenchmarkSnapshotRead, BenchmarkSummary

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
        "llm_params": scenario.llm_params,
        "load_config": scenario.load_config,
        "max_concurrency": scenario.max_concurrency,
        "profiles": profiles_data,
    }


def _build_endpoint_snapshot(endpoint: Endpoint) -> dict:
    """Freeze the endpoint config into a JSON-serializable dict."""
    return {
        "endpoint_id": str(endpoint.id),
        "name": endpoint.name,
        "endpoint_url": endpoint.endpoint_url,
        "api_key": endpoint.api_key,
        "model_name": endpoint.model_name,
        "gpu": endpoint.gpu,
        "inference_engine": endpoint.inference_engine,
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

    # Load endpoint
    ep_result = await db.execute(
        select(Endpoint).where(Endpoint.id == body.endpoint_id)
    )
    endpoint = ep_result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

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

    # Build frozen snapshots
    snapshot = _build_scenario_snapshot(scenario, scenario.profiles)
    ep_snapshot = _build_endpoint_snapshot(endpoint)

    # Create benchmark row
    benchmark = Benchmark(
        scenario_id=body.scenario_id,
        endpoint_id=body.endpoint_id,
        status="pending",
        scenario_snapshot=snapshot,
        endpoint_snapshot=ep_snapshot,
    )
    db.add(benchmark)
    await db.flush()
    await db.refresh(benchmark)
    await db.commit()

    # Launch runner in background
    runner = BenchmarkRunner(
        benchmark_id=benchmark.id,
        scenario_snapshot=snapshot,
        endpoint_snapshot=ep_snapshot,
        session_factory=async_session,
    )
    asyncio.create_task(runner.run())

    return {
        "data": BenchmarkRead(
            id=benchmark.id,
            scenario_id=benchmark.scenario_id,
            endpoint_id=benchmark.endpoint_id,
            status=benchmark.status,
            scenario_snapshot=benchmark.scenario_snapshot,
            endpoint_snapshot=benchmark.endpoint_snapshot,
            results_summary=benchmark.results_summary,
            error_message=benchmark.error_message,
            started_at=benchmark.started_at,
            completed_at=benchmark.completed_at,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
            scenario_name=snapshot.get("name", ""),
            endpoint_name=ep_snapshot.get("name", ""),
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

        ep_snap = bench.endpoint_snapshot or {}
        items.append(
            BenchmarkSummary(
                id=bench.id,
                scenario_id=bench.scenario_id,
                scenario_name=bench.scenario_snapshot.get("name", "") if bench.scenario_snapshot else "",
                endpoint_name=ep_snap.get("name", ""),
                model_name=ep_snap.get("model_name", ""),
                gpu=ep_snap.get("gpu"),
                inference_engine=ep_snap.get("inference_engine"),
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

    ep_snap = benchmark.endpoint_snapshot or {}
    return {
        "data": BenchmarkRead(
            id=benchmark.id,
            scenario_id=benchmark.scenario_id,
            endpoint_id=benchmark.endpoint_id,
            status=benchmark.status,
            scenario_snapshot=benchmark.scenario_snapshot,
            endpoint_snapshot=benchmark.endpoint_snapshot,
            results_summary=benchmark.results_summary,
            error_message=benchmark.error_message,
            started_at=benchmark.started_at,
            completed_at=benchmark.completed_at,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
            scenario_name=benchmark.scenario_snapshot.get("name", "") if benchmark.scenario_snapshot else "",
            endpoint_name=ep_snap.get("name", ""),
        ).model_dump(mode="json")
    }


@router.get("/{benchmark_id}/snapshots")
async def get_benchmark_snapshots(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get historical per-second snapshots for a benchmark with computed elapsed_seconds."""
    await _get_benchmark_or_404(benchmark_id, db)

    result = await db.execute(
        select(BenchmarkSnapshot)
        .where(BenchmarkSnapshot.benchmark_id == benchmark_id)
        .order_by(BenchmarkSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        return {"data": []}

    first_ts = snapshots[0].timestamp
    data = []
    for s in snapshots:
        d = BenchmarkSnapshotRead.model_validate(s).model_dump(mode="json")
        d["elapsed_seconds"] = (s.timestamp - first_ts).total_seconds()
        data.append(d)

    return {"data": data}


@router.get("/{benchmark_id}/requests")
async def get_benchmark_requests(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get individual request log entries for a benchmark."""
    from app.models.profile import Profile

    await _get_benchmark_or_404(benchmark_id, db)

    result = await db.execute(
        select(
            BenchmarkRequest.error_type,
            BenchmarkRequest.profile_id,
            BenchmarkRequest.turn_number,
            BenchmarkRequest.ttft_ms,
            BenchmarkRequest.tokens_per_second,
            BenchmarkRequest.output_tokens,
            BenchmarkRequest.http_status,
        )
        .where(BenchmarkRequest.benchmark_id == benchmark_id)
        .order_by(BenchmarkRequest.created_at)
    )
    rows = result.all()

    # Resolve profile names
    profile_ids = {r.profile_id for r in rows if r.profile_id}
    profile_names: dict[str, str] = {}
    if profile_ids:
        pres = await db.execute(
            select(Profile.id, Profile.name).where(Profile.id.in_(profile_ids))
        )
        for pid, pname in pres.all():
            profile_names[str(pid)] = pname

    data = []
    for r in rows:
        pid_str = str(r.profile_id) if r.profile_id else "unknown"
        data.append({
            "success": r.error_type is None,
            "profile": profile_names.get(pid_str, pid_str[:8]),
            "turn": r.turn_number,
            "ttft_ms": round(r.ttft_ms, 1) if r.ttft_ms is not None else None,
            "tps": round(r.tokens_per_second, 1) if r.tokens_per_second is not None else None,
            "output_tokens": r.output_tokens,
            "http_status": r.http_status,
            "error_type": r.error_type,
        })

    return {"data": data}


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
