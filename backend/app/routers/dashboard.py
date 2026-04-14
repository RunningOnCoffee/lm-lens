import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.benchmark import Benchmark, BenchmarkRequest
from app.schemas.dashboard import (
    DashboardResponse,
    EndpointPerformance,
    FleetOverview,
    ProfileLatencySummary,
    TokenEconomyEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_FINISHED_STATUSES = ("completed", "aborted", "failed")


def _round(value: float | None, precision: int = 2) -> float | None:
    return round(value, precision) if value is not None else None


def _safe_avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@router.get("")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Aggregated dashboard data across all completed benchmarks."""

    # --- Load all finished benchmarks with results ---
    result = await db.execute(
        select(Benchmark)
        .where(
            Benchmark.status.in_(_FINISHED_STATUSES),
            Benchmark.results_summary.isnot(None),
        )
        .order_by(Benchmark.created_at.desc())
    )
    benchmarks = result.scalars().all()

    if not benchmarks:
        return {
            "data": DashboardResponse(
                fleet=FleetOverview(),
                endpoints=[],
                profiles=[],
                recent_runs=[],
            ).model_dump(mode="json")
        }

    # --- Fleet totals ---
    total_requests = 0
    total_input = 0
    total_output = 0
    quality_scores: list[float] = []

    for b in benchmarks:
        s = b.results_summary or {}
        total_requests += s.get("total_requests", 0)
        total_input += s.get("total_input_tokens", 0)
        total_output += s.get("total_output_tokens", 0)
        qs = s.get("quality_scores", {})
        if qs and qs.get("overall") is not None:
            quality_scores.append(qs["overall"])

    fleet = FleetOverview(
        total_benchmarks=len(benchmarks),
        total_requests=total_requests,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        avg_quality_overall=_round(_safe_avg(quality_scores), 4),
    )

    # --- Per-endpoint aggregation ---
    ep_groups: dict[str, list[Benchmark]] = {}
    for b in benchmarks:
        ep_id = str(b.endpoint_id) if b.endpoint_id else "unknown"
        ep_groups.setdefault(ep_id, []).append(b)

    endpoints_data: list[EndpointPerformance] = []
    for ep_id, runs in ep_groups.items():
        # Use endpoint_snapshot from the most recent run for name/model/gpu
        latest = runs[0]  # already ordered by created_at desc
        ep_snap = latest.endpoint_snapshot or {}

        ttft_vals = []
        tps_vals = []
        q_vals = []
        ep_input = 0
        ep_output = 0

        for b in runs:
            s = b.results_summary or {}
            if s.get("ttft_t1_p50_ms") is not None:
                ttft_vals.append(s["ttft_t1_p50_ms"])
            if s.get("tps_p50") is not None:
                tps_vals.append(s["tps_p50"])
            qs = s.get("quality_scores", {})
            if qs and qs.get("overall") is not None:
                q_vals.append(qs["overall"])
            ep_input += s.get("total_input_tokens", 0)
            ep_output += s.get("total_output_tokens", 0)

        endpoints_data.append(EndpointPerformance(
            endpoint_id=ep_id,
            name=ep_snap.get("name", "Unknown"),
            model_name=ep_snap.get("model_name", ""),
            gpu=ep_snap.get("gpu"),
            inference_engine=ep_snap.get("inference_engine"),
            run_count=len(runs),
            avg_ttft_p50=_round(_safe_avg(ttft_vals)),
            avg_tps_p50=_round(_safe_avg(tps_vals)),
            avg_quality_overall=_round(_safe_avg(q_vals), 4),
            total_input_tokens=ep_input,
            total_output_tokens=ep_output,
            last_run_at=latest.completed_at or latest.created_at,
        ))

    # --- Per-profile latency (from benchmark_requests) ---
    # Only from completed benchmarks
    completed_ids = [b.id for b in benchmarks if b.status == "completed"]
    profiles_data: list[ProfileLatencySummary] = []

    if completed_ids:
        profile_result = await db.execute(
            select(
                BenchmarkRequest.profile_id,
                func.percentile_cont(0.5).within_group(
                    BenchmarkRequest.ttft_ms
                ).label("ttft_p50"),
                func.count(func.distinct(BenchmarkRequest.benchmark_id)).label("bench_count"),
            )
            .where(
                BenchmarkRequest.benchmark_id.in_(completed_ids),
                BenchmarkRequest.error_type.is_(None),
                BenchmarkRequest.ttft_ms.isnot(None),
            )
            .group_by(BenchmarkRequest.profile_id)
        )
        profile_rows = profile_result.all()

        # Build profile name map from all benchmarks' scenario_snapshots
        profile_names: dict[str, str] = {}
        for b in benchmarks:
            snap = b.scenario_snapshot or {}
            for sp in snap.get("profiles", []):
                profile = sp.get("profile", {})
                pid = str(profile.get("id", ""))
                name = profile.get("name", "")
                if pid and name:
                    profile_names[pid] = name  # latest wins (benchmarks sorted desc)

        for row in profile_rows:
            pid = str(row.profile_id) if row.profile_id else "unknown"
            profiles_data.append(ProfileLatencySummary(
                profile_id=pid,
                profile_name=profile_names.get(pid, pid[:8]),
                avg_ttft_p50=_round(row.ttft_p50),
                benchmark_count=row.bench_count,
            ))

    # --- Recent runs (top 10) ---
    # Count requests per benchmark
    req_count = (
        select(
            BenchmarkRequest.benchmark_id,
            func.count(BenchmarkRequest.id).label("total_requests"),
        )
        .group_by(BenchmarkRequest.benchmark_id)
        .subquery()
    )

    recent_result = await db.execute(
        select(Benchmark, req_count.c.total_requests)
        .outerjoin(req_count, Benchmark.id == req_count.c.benchmark_id)
        .where(Benchmark.status.in_(_FINISHED_STATUSES))
        .order_by(Benchmark.created_at.desc())
        .limit(10)
    )
    recent_rows = recent_result.all()

    recent_runs = []
    for bench, total_reqs in recent_rows:
        ep_snap = bench.endpoint_snapshot or {}
        duration = None
        if bench.started_at and bench.completed_at:
            duration = (bench.completed_at - bench.started_at).total_seconds()
        recent_runs.append({
            "id": str(bench.id),
            "scenario_id": str(bench.scenario_id),
            "endpoint_id": str(bench.endpoint_id) if bench.endpoint_id else None,
            "scenario_name": (bench.scenario_snapshot or {}).get("name", ""),
            "endpoint_name": ep_snap.get("name", ""),
            "model_name": ep_snap.get("model_name", ""),
            "gpu": ep_snap.get("gpu"),
            "seed": bench.seed,
            "status": bench.status,
            "total_requests": total_reqs or 0,
            "duration_seconds": duration,
            "created_at": bench.created_at.isoformat() if bench.created_at else None,
        })

    return {
        "data": DashboardResponse(
            fleet=fleet,
            endpoints=endpoints_data,
            profiles=profiles_data,
            recent_runs=recent_runs,
        ).model_dump(mode="json")
    }


@router.get("/token-economy")
async def get_token_economy(
    group_by: str = Query("endpoint", pattern="^(endpoint|profile)$"),
    endpoint_id: UUID | None = Query(None),
    profile_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Token economy breakdown, grouped by endpoint or profile."""

    # Base query: completed benchmarks only
    base_filter = [
        Benchmark.status == "completed",
        BenchmarkRequest.benchmark_id == Benchmark.id,
    ]
    if endpoint_id:
        base_filter.append(Benchmark.endpoint_id == endpoint_id)
    if profile_id:
        base_filter.append(BenchmarkRequest.profile_id == profile_id)

    if group_by == "endpoint":
        query = (
            select(
                Benchmark.endpoint_id,
                func.sum(BenchmarkRequest.input_tokens).label("total_input"),
                func.sum(BenchmarkRequest.output_tokens).label("total_output"),
                func.count(BenchmarkRequest.id).label("req_count"),
            )
            .where(*base_filter)
            .group_by(Benchmark.endpoint_id)
        )
        result = await db.execute(query)
        rows = result.all()

        # Get endpoint names from most recent benchmarks
        ep_names: dict[str, str] = {}
        name_result = await db.execute(
            select(Benchmark.endpoint_id, Benchmark.endpoint_snapshot)
            .where(Benchmark.status == "completed", Benchmark.endpoint_id.isnot(None))
            .order_by(Benchmark.created_at.desc())
        )
        for row in name_result.all():
            eid = str(row.endpoint_id)
            if eid not in ep_names:
                snap = row.endpoint_snapshot or {}
                ep_names[eid] = snap.get("name", eid[:8])

        data = [
            TokenEconomyEntry(
                group_id=str(r.endpoint_id) if r.endpoint_id else "unknown",
                group_name=ep_names.get(str(r.endpoint_id), str(r.endpoint_id)[:8] if r.endpoint_id else "unknown"),
                total_input_tokens=r.total_input or 0,
                total_output_tokens=r.total_output or 0,
                request_count=r.req_count or 0,
            ).model_dump()
            for r in rows
        ]
    else:
        query = (
            select(
                BenchmarkRequest.profile_id,
                func.sum(BenchmarkRequest.input_tokens).label("total_input"),
                func.sum(BenchmarkRequest.output_tokens).label("total_output"),
                func.count(BenchmarkRequest.id).label("req_count"),
            )
            .where(*base_filter)
            .group_by(BenchmarkRequest.profile_id)
        )
        result = await db.execute(query)
        rows = result.all()

        # Get profile names from scenario snapshots
        profile_names: dict[str, str] = {}
        snap_result = await db.execute(
            select(Benchmark.scenario_snapshot)
            .where(Benchmark.status == "completed")
            .order_by(Benchmark.created_at.desc())
        )
        for row in snap_result.scalars().all():
            snap = row or {}
            for sp in snap.get("profiles", []):
                profile = sp.get("profile", {})
                pid = str(profile.get("id", ""))
                name = profile.get("name", "")
                if pid and name and pid not in profile_names:
                    profile_names[pid] = name

        data = [
            TokenEconomyEntry(
                group_id=str(r.profile_id) if r.profile_id else "unknown",
                group_name=profile_names.get(str(r.profile_id), str(r.profile_id)[:8] if r.profile_id else "unknown"),
                total_input_tokens=r.total_input or 0,
                total_output_tokens=r.total_output or 0,
                request_count=r.req_count or 0,
            ).model_dump()
            for r in rows
        ]

    return {"data": data, "group_by": group_by}
