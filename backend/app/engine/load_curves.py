"""Load curve implementations for controlling virtual user count over time.

Each curve answers: "how many users should be active at elapsed time T?"
Used by ramp and breaking_point test modes.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod


class LoadCurve(ABC):
    """Base class for load curve strategies."""

    @abstractmethod
    def target_users(self, elapsed: float, total_users: int, duration: float) -> int:
        """Return desired active user count at the given elapsed time.

        Args:
            elapsed: Seconds since benchmark start.
            total_users: Maximum number of virtual users configured.
            duration: Total benchmark duration in seconds.

        Returns:
            Number of users that should be active (1 to total_users).
        """


class StepCurve(LoadCurve):
    """Staircase ramp: add step_size users every interval seconds.

    This reproduces the original ramp behavior.
    """

    def __init__(self, step_size: int = 1, interval: int = 10) -> None:
        self.step_size = max(1, step_size)
        self.interval = max(1, interval)

    def target_users(self, elapsed: float, total_users: int, duration: float) -> int:
        steps_completed = int(elapsed / self.interval) + 1  # start with first batch
        target = steps_completed * self.step_size
        return max(1, min(target, total_users))


class LinearCurve(LoadCurve):
    """Smooth linear ramp from 1 user to total_users over the full duration."""

    def target_users(self, elapsed: float, total_users: int, duration: float) -> int:
        if duration <= 0:
            return total_users
        progress = min(elapsed / duration, 1.0)
        target = 1 + (total_users - 1) * progress
        return max(1, min(round(target), total_users))


class SpikeCurve(LoadCurve):
    """Base load with a sharp spike at a configurable point.

    Runs at ~20% of users, spikes to 100% at spike_at_pct of duration,
    holds for spike_duration_seconds, then returns to base.
    """

    BASE_FRACTION = 0.2  # 20% base load

    def __init__(self, spike_at_pct: float = 50.0, spike_duration: int = 10) -> None:
        self.spike_at_pct = max(0.0, min(spike_at_pct, 100.0))
        self.spike_duration = max(1, spike_duration)

    def target_users(self, elapsed: float, total_users: int, duration: float) -> int:
        if duration <= 0:
            return total_users
        base = max(1, round(total_users * self.BASE_FRACTION))
        spike_start = duration * (self.spike_at_pct / 100.0)
        spike_end = spike_start + self.spike_duration

        if spike_start <= elapsed < spike_end:
            return total_users
        return base


class WaveCurve(LoadCurve):
    """Sinusoidal oscillation between ~20% and 100% of users.

    Creates periodic load waves to test how the endpoint handles
    fluctuating concurrency.
    """

    MIN_FRACTION = 0.2  # trough at 20%

    def __init__(self, period: int = 30) -> None:
        self.period = max(5, period)

    def target_users(self, elapsed: float, total_users: int, duration: float) -> int:
        # Sine wave: oscillates between MIN_FRACTION and 1.0
        # Start at minimum (sine = -1), peak at period/2
        sin_val = math.sin(2 * math.pi * elapsed / self.period - math.pi / 2)
        # Map [-1, 1] to [MIN_FRACTION, 1.0]
        fraction = self.MIN_FRACTION + (1.0 - self.MIN_FRACTION) * (sin_val + 1) / 2
        target = round(total_users * fraction)
        return max(1, min(target, total_users))


def create_curve(load_config: dict) -> LoadCurve:
    """Factory: build a LoadCurve from a scenario's load_config dict."""
    curve_type = load_config.get("load_curve", "step")

    if curve_type == "linear":
        return LinearCurve()
    elif curve_type == "spike":
        return SpikeCurve(
            spike_at_pct=load_config.get("spike_at_pct", 50.0),
            spike_duration=load_config.get("spike_duration_seconds", 10),
        )
    elif curve_type == "wave":
        return WaveCurve(
            period=load_config.get("wave_period_seconds", 30),
        )
    else:  # "step" or unknown → default staircase
        return StepCurve(
            step_size=load_config.get("ramp_users_per_step", 1),
            interval=load_config.get("ramp_interval_seconds", 10),
        )
