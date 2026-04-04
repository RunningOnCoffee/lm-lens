import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session, get_db
from app.engine.runner import BenchmarkRunner, get_active_runner
from app.engine.snapshots import percentile, ws_manager
from app.models.benchmark import Benchmark, BenchmarkRequest, BenchmarkSnapshot
from app.models.endpoint import Endpoint
from app.models.scenario import Scenario, ScenarioProfile
from app.schemas.benchmark import (
    BenchmarkCreate,
    BenchmarkRead,
    BenchmarkRequestRead,
    BenchmarkSnapshotRead,
    BenchmarkSummary,
    HistogramBin,
    HistogramResponse,
    HistogramStats,
    ProfileStatsEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


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


def _profile_name_map(benchmark: Benchmark) -> dict[str, str]:
    """Build a profile_id→name mapping from a benchmark's scenario snapshot."""
    names: dict[str, str] = {}
    snap = benchmark.scenario_snapshot or {}
    for sp in snap.get("profiles", []):
        profile = sp.get("profile", {})
        pid = str(profile.get("id", ""))
        name = profile.get("name", pid[:8] if pid else "unknown")
        if pid:
            names[pid] = name
    return names


# Allowed sort columns for requests endpoint
_REQUEST_SORT_COLUMNS = {
    "created_at": BenchmarkRequest.created_at,
    "ttft_ms": BenchmarkRequest.ttft_ms,
    "tgt_ms": BenchmarkRequest.tgt_ms,
    "tokens_per_second": BenchmarkRequest.tokens_per_second,
    "output_tokens": BenchmarkRequest.output_tokens,
    "input_tokens": BenchmarkRequest.input_tokens,
    "turn_number": BenchmarkRequest.turn_number,
}


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


@router.get("/compare")
async def compare_benchmarks(
    ids: str = Query(..., description="Comma-separated benchmark UUIDs (exactly 2)"),
    db: AsyncSession = Depends(get_db),
):
    """Compare two benchmark runs side by side."""
    parts = [p.strip() for p in ids.split(",") if p.strip()]
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Provide exactly 2 comma-separated benchmark IDs")

    try:
        id_a, id_b = UUID(parts[0]), UUID(parts[1])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    bench_a = await _get_benchmark_or_404(id_a, db)
    bench_b = await _get_benchmark_or_404(id_b, db)

    ep_snap_a = bench_a.endpoint_snapshot or {}
    ep_snap_b = bench_b.endpoint_snapshot or {}

    benchmarks = [
        BenchmarkRead(
            id=b.id, scenario_id=b.scenario_id, endpoint_id=b.endpoint_id,
            status=b.status, scenario_snapshot=b.scenario_snapshot,
            endpoint_snapshot=b.endpoint_snapshot, results_summary=b.results_summary,
            error_message=b.error_message, started_at=b.started_at,
            completed_at=b.completed_at, created_at=b.created_at, updated_at=b.updated_at,
            scenario_name=b.scenario_snapshot.get("name", "") if b.scenario_snapshot else "",
            endpoint_name=ep.get("name", ""),
        ).model_dump(mode="json")
        for b, ep in [(bench_a, ep_snap_a), (bench_b, ep_snap_b)]
    ]

    return {"data": {"benchmarks": benchmarks}}


@router.get("/export/{benchmark_id}")
async def export_benchmark(
    benchmark_id: UUID,
    format: str = Query("json"),
    db: AsyncSession = Depends(get_db),
):
    """Export benchmark request data as JSON or CSV."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)
    profile_names = _profile_name_map(benchmark)

    result = await db.execute(
        select(BenchmarkRequest)
        .where(BenchmarkRequest.benchmark_id == benchmark_id)
        .order_by(BenchmarkRequest.created_at)
    )
    rows = result.scalars().all()

    if format == "csv":
        csv_fields = [
            "profile_name", "session_id", "turn_number", "ttft_ms", "tgt_ms",
            "input_tokens", "output_tokens", "tokens_per_second",
            "http_status", "error_type", "error_detail", "model_reported",
            "quality_flags", "response_text", "created_at",
        ]

        def generate_csv():
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=csv_fields)
            writer.writeheader()
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

            for r in rows:
                pid = str(r.profile_id) if r.profile_id else ""
                writer.writerow({
                    "profile_name": profile_names.get(pid, pid[:8]),
                    "session_id": str(r.session_id),
                    "turn_number": r.turn_number,
                    "ttft_ms": r.ttft_ms,
                    "tgt_ms": r.tgt_ms,
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "tokens_per_second": r.tokens_per_second,
                    "http_status": r.http_status,
                    "error_type": r.error_type or "",
                    "error_detail": r.error_detail or "",
                    "model_reported": r.model_reported or "",
                    "quality_flags": ",".join(r.quality_flags) if r.quality_flags else "",
                    "response_text": (r.response_text or "")[:500],
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                })
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)

        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=benchmark_{benchmark_id}.csv"},
        )

    # JSON format (default)
    data = []
    for r in rows:
        item = BenchmarkRequestRead.model_validate(r).model_dump(mode="json")
        pid = str(r.profile_id) if r.profile_id else ""
        item["profile_name"] = profile_names.get(pid, pid[:8] if pid else "unknown")
        data.append(item)

    return {"data": data}


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
async def get_benchmark_requests(
    benchmark_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    profile_id: UUID | None = Query(None),
    turn_number: int | None = Query(None),
    error_type: str | None = Query(None),
    quality_flag: str | None = Query(None),
    success: bool | None = Query(None),
    session_id: UUID | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated request log entries with filtering and sorting."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)
    profile_names = _profile_name_map(benchmark)

    # Build query with filters
    query = select(BenchmarkRequest).where(BenchmarkRequest.benchmark_id == benchmark_id)

    if profile_id is not None:
        query = query.where(BenchmarkRequest.profile_id == profile_id)
    if turn_number is not None:
        query = query.where(BenchmarkRequest.turn_number == turn_number)
    if error_type is not None:
        query = query.where(BenchmarkRequest.error_type == error_type)
    if session_id is not None:
        query = query.where(BenchmarkRequest.session_id == session_id)
    if success is not None:
        if success:
            query = query.where(BenchmarkRequest.error_type.is_(None))
        else:
            query = query.where(BenchmarkRequest.error_type.isnot(None))
    if quality_flag is not None:
        query = query.where(
            BenchmarkRequest.quality_flags.contains([quality_flag])
        )

    # Count total matching rows
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    sort_col = _REQUEST_SORT_COLUMNS.get(sort_by, BenchmarkRequest.created_at)
    if sort_dir == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    rows = result.scalars().all()

    data = []
    for r in rows:
        item = BenchmarkRequestRead.model_validate(r).model_dump(mode="json")
        pid_str = str(r.profile_id) if r.profile_id else ""
        item["profile_name"] = profile_names.get(pid_str, pid_str[:8] if pid_str else "unknown")
        data.append(item)

    return {"data": data, "meta": {"total": total, "page": page, "per_page": per_page}}


@router.get("/{benchmark_id}/histogram")
async def get_benchmark_histogram(
    benchmark_id: UUID,
    metric: str = Query("ttft_ms"),
    bins: int = Query(30, ge=5, le=100),
    profile_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Compute a histogram of request metrics for a benchmark."""
    await _get_benchmark_or_404(benchmark_id, db)

    # Map metric name to column
    metric_columns = {
        "ttft_ms": BenchmarkRequest.ttft_ms,
        "tgt_ms": BenchmarkRequest.tgt_ms,
        "tokens_per_second": BenchmarkRequest.tokens_per_second,
    }
    col = metric_columns.get(metric)
    if col is None:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    query = (
        select(col)
        .where(
            BenchmarkRequest.benchmark_id == benchmark_id,
            col.isnot(None),
            BenchmarkRequest.error_type.is_(None),
        )
    )
    if profile_id is not None:
        query = query.where(BenchmarkRequest.profile_id == profile_id)

    result = await db.execute(query)
    values = sorted([row[0] for row in result.all()])

    if not values:
        return {"data": HistogramResponse(bins=[], stats=HistogramStats()).model_dump()}

    v_min, v_max = values[0], values[-1]
    bin_width = (v_max - v_min) / bins if v_max > v_min else 1.0
    if bin_width == 0:
        bin_width = 1.0

    histogram_bins: list[HistogramBin] = []
    for i in range(bins):
        b_min = v_min + i * bin_width
        b_max = v_min + (i + 1) * bin_width
        count = sum(1 for v in values if b_min <= v < b_max or (i == bins - 1 and v == b_max))
        histogram_bins.append(HistogramBin(min=round(b_min, 2), max=round(b_max, 2), count=count))

    stats = HistogramStats(
        p50=_round(percentile(values, 50)),
        p95=_round(percentile(values, 95)),
        p99=_round(percentile(values, 99)),
        mean=_round(sum(values) / len(values)),
        min=_round(v_min),
        max=_round(v_max),
    )

    return {"data": HistogramResponse(bins=histogram_bins, stats=stats).model_dump()}


@router.get("/{benchmark_id}/profile-stats")
async def get_profile_stats(benchmark_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get per-profile aggregated statistics for a benchmark."""
    benchmark = await _get_benchmark_or_404(benchmark_id, db)
    profile_names = _profile_name_map(benchmark)

    result = await db.execute(
        select(BenchmarkRequest)
        .where(BenchmarkRequest.benchmark_id == benchmark_id)
    )
    rows = result.scalars().all()

    # Group by profile
    by_profile: dict[str, list[BenchmarkRequest]] = {}
    for r in rows:
        pid = str(r.profile_id) if r.profile_id else "unknown"
        by_profile.setdefault(pid, []).append(r)

    data = []
    for pid, reqs in by_profile.items():
        ok = [r for r in reqs if r.error_type is None]
        failed = len(reqs) - len(ok)

        ttft_vals = [r.ttft_ms for r in ok if r.ttft_ms is not None]
        tps_vals = [r.tokens_per_second for r in ok if r.tokens_per_second is not None]
        out_tokens = [r.output_tokens for r in ok if r.output_tokens is not None]

        # Quality flag counts
        qf_counts: dict[str, int] = {}
        for r in reqs:
            if r.quality_flags:
                for flag in r.quality_flags:
                    qf_counts[flag] = qf_counts.get(flag, 0) + 1

        data.append(ProfileStatsEntry(
            profile_id=pid,
            profile_name=profile_names.get(pid, pid[:8]),
            total_requests=len(reqs),
            success_count=len(ok),
            fail_count=failed,
            ttft_p50=_round(percentile(ttft_vals, 50)),
            ttft_p95=_round(percentile(ttft_vals, 95)),
            tps_p50=_round(percentile(tps_vals, 50)),
            tps_p5=_round(percentile(tps_vals, 5)),
            avg_output_tokens=_round(sum(out_tokens) / len(out_tokens)) if out_tokens else None,
            quality_flag_counts=qf_counts,
        ).model_dump())

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
