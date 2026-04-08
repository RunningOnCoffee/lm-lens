"""Tests for load curve implementations."""

import pytest

from app.engine.load_curves import (
    LinearCurve,
    SpikeCurve,
    StepCurve,
    WaveCurve,
    create_curve,
)


class TestStepCurve:
    def test_starts_with_first_batch(self):
        curve = StepCurve(step_size=2, interval=10)
        assert curve.target_users(0, 10, 60) == 2

    def test_steps_up(self):
        curve = StepCurve(step_size=2, interval=10)
        assert curve.target_users(10, 10, 60) == 4
        assert curve.target_users(20, 10, 60) == 6

    def test_caps_at_total(self):
        curve = StepCurve(step_size=5, interval=10)
        assert curve.target_users(30, 10, 60) == 10

    def test_never_below_one(self):
        curve = StepCurve(step_size=1, interval=100)
        assert curve.target_users(0, 1, 60) >= 1


class TestLinearCurve:
    def test_starts_at_one(self):
        curve = LinearCurve()
        assert curve.target_users(0, 10, 60) == 1

    def test_midpoint(self):
        curve = LinearCurve()
        target = curve.target_users(30, 10, 60)
        # At 50%, should be about halfway: 1 + (10-1)*0.5 = 5.5 → 6
        assert target == 6

    def test_ends_at_total(self):
        curve = LinearCurve()
        assert curve.target_users(60, 10, 60) == 10

    def test_beyond_duration(self):
        curve = LinearCurve()
        assert curve.target_users(100, 10, 60) == 10

    def test_zero_duration(self):
        curve = LinearCurve()
        assert curve.target_users(0, 10, 0) == 10


class TestSpikeCurve:
    def test_base_before_spike(self):
        curve = SpikeCurve(spike_at_pct=50.0, spike_duration=10)
        # 20% of 10 users = 2
        assert curve.target_users(0, 10, 60) == 2

    def test_spike_at_peak(self):
        curve = SpikeCurve(spike_at_pct=50.0, spike_duration=10)
        # Spike starts at 30s (50% of 60)
        assert curve.target_users(30, 10, 60) == 10

    def test_spike_during_duration(self):
        curve = SpikeCurve(spike_at_pct=50.0, spike_duration=10)
        # During spike window (30-40s)
        assert curve.target_users(35, 10, 60) == 10

    def test_base_after_spike(self):
        curve = SpikeCurve(spike_at_pct=50.0, spike_duration=10)
        # After spike (>40s)
        assert curve.target_users(41, 10, 60) == 2

    def test_base_minimum_one(self):
        curve = SpikeCurve(spike_at_pct=50.0, spike_duration=10)
        # 20% of 3 users = 0.6 → rounded to 1
        assert curve.target_users(0, 3, 60) >= 1


class TestWaveCurve:
    def test_starts_at_minimum(self):
        curve = WaveCurve(period=30)
        # sin(-pi/2) = -1 → should be at minimum (20% of users)
        target = curve.target_users(0, 10, 60)
        assert target == 2  # 20% of 10

    def test_peak_at_half_period(self):
        curve = WaveCurve(period=30)
        # At period/2 (15s): sin(2*pi*15/30 - pi/2) = sin(pi - pi/2) = sin(pi/2) = 1
        target = curve.target_users(15, 10, 60)
        assert target == 10  # 100% of 10

    def test_back_to_minimum_at_full_period(self):
        curve = WaveCurve(period=30)
        target = curve.target_users(30, 10, 60)
        assert target == 2  # Back to minimum

    def test_never_below_one(self):
        curve = WaveCurve(period=30)
        # Even with 2 users, minimum should be at least 1
        for t in range(0, 60):
            assert curve.target_users(t, 2, 60) >= 1


class TestCreateCurve:
    def test_default_is_step(self):
        curve = create_curve({})
        assert isinstance(curve, StepCurve)

    def test_step_with_params(self):
        curve = create_curve({
            "load_curve": "step",
            "ramp_users_per_step": 3,
            "ramp_interval_seconds": 15,
        })
        assert isinstance(curve, StepCurve)
        assert curve.step_size == 3
        assert curve.interval == 15

    def test_linear(self):
        curve = create_curve({"load_curve": "linear"})
        assert isinstance(curve, LinearCurve)

    def test_spike_with_params(self):
        curve = create_curve({
            "load_curve": "spike",
            "spike_at_pct": 75.0,
            "spike_duration_seconds": 20,
        })
        assert isinstance(curve, SpikeCurve)
        assert curve.spike_at_pct == 75.0
        assert curve.spike_duration == 20

    def test_wave_with_params(self):
        curve = create_curve({
            "load_curve": "wave",
            "wave_period_seconds": 45,
        })
        assert isinstance(curve, WaveCurve)
        assert curve.period == 45

    def test_unknown_falls_back_to_step(self):
        curve = create_curve({"load_curve": "unknown"})
        assert isinstance(curve, StepCurve)
