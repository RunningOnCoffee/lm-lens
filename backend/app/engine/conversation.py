from __future__ import annotations

import asyncio
import random
import re
import uuid
from dataclasses import dataclass, field
from uuid import UUID

from app.engine.collector import MetricCollector
from app.engine.llm_client import LLMClient


@dataclass
class SessionConfig:
    """Pre-resolved configuration for one virtual user session."""

    profile_id: UUID
    session_mode: str  # "multi_turn" or "single_shot"
    turns_per_session: tuple[int, int]  # (min, max)
    think_time_seconds: tuple[float, float]  # (min, max)
    sessions_per_user: tuple[int, int]  # (min, max)
    read_time_factor: float  # seconds per output token
    templates: list[dict] = field(default_factory=list)
    universal_follow_ups: list[str] = field(default_factory=list)
    variables: dict[str, list[str]] = field(default_factory=dict)
    # Seeded mode: pre-generated prompts, no conversation history
    seeded_prompts: list[str] | None = None
    session_index: int | None = None


_VAR_PATTERN = re.compile(r"\$([A-Z_][A-Z0-9_]*)")


class ConversationSimulator:
    """Drives one virtual user session: template selection, variable substitution,
    multi-turn conversation with think/read time."""

    def __init__(
        self,
        config: SessionConfig,
        llm_client: LLMClient,
        collector: MetricCollector,
        abort_event: asyncio.Event,
    ) -> None:
        self._config = config
        self._client = llm_client
        self._collector = collector
        self._abort = abort_event
        self._session_id = uuid.uuid4()

    @property
    def session_id(self) -> UUID:
        return self._session_id

    async def run(self) -> None:
        """Run one complete conversation session."""
        if self._config.seeded_prompts is not None:
            await self._run_seeded()
            return

        if not self._config.templates:
            return

        template = random.choice(self._config.templates)
        messages: list[dict] = []

        if self._config.session_mode == "single_shot":
            num_turns = 1
        else:
            min_t, max_t = self._config.turns_per_session
            num_turns = random.randint(min_t, max_t)

        for turn in range(num_turns):
            if self._abort.is_set():
                return

            # Build prompt
            if turn == 0:
                prompt = self._substitute_vars(template["starter_prompt"])
            else:
                prompt = self._pick_follow_up(template)

            messages.append({"role": "user", "content": prompt})

            # Send to LLM
            result = await self._client.send(messages)

            # Record metric
            await self._collector.record(
                result=result,
                profile_id=self._config.profile_id,
                session_id=self._session_id,
                turn_number=turn,
            )

            # Add assistant response to conversation history
            if result.success and result.response_text:
                messages.append({"role": "assistant", "content": result.response_text})

            # Simulate read time + think time (unless last turn or aborted)
            if turn < num_turns - 1 and not self._abort.is_set():
                read_time = len(result.response_text.split()) * self._config.read_time_factor
                think_time = random.uniform(*self._config.think_time_seconds)
                await self._interruptible_sleep(read_time + think_time)

    async def _run_seeded(self) -> None:
        """Run with pre-generated prompts and accumulated conversation history."""
        prompts = self._config.seeded_prompts
        messages: list[dict] = []
        for turn, prompt in enumerate(prompts):
            if self._abort.is_set():
                return

            messages.append({"role": "user", "content": prompt})
            result = await self._client.send(messages)

            await self._collector.record(
                result=result,
                profile_id=self._config.profile_id,
                session_id=self._session_id,
                turn_number=turn,
            )

            if result.success and result.response_text:
                messages.append({"role": "assistant", "content": result.response_text})

            # Think time between turns
            if turn < len(prompts) - 1 and not self._abort.is_set():
                read_time = len(result.response_text.split()) * self._config.read_time_factor if result.response_text else 0
                think_time = random.uniform(*self._config.think_time_seconds)
                await self._interruptible_sleep(read_time + think_time)

    def _substitute_vars(self, text: str) -> str:
        """Replace $VAR_NAME with a random value from the variables dict."""
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            values = self._config.variables.get(var_name, [])
            return random.choice(values) if values else match.group(0)
        return _VAR_PATTERN.sub(replacer, text)

    def _pick_follow_up(self, template: dict) -> str:
        """Pick a follow-up prompt: template-specific first, then universal, then fallback."""
        follow_ups = template.get("follow_ups", [])
        if follow_ups:
            fu = random.choice(follow_ups)
            content = fu["content"] if isinstance(fu, dict) else fu
            return self._substitute_vars(content)
        if self._config.universal_follow_ups:
            return self._substitute_vars(random.choice(self._config.universal_follow_ups))
        return "Can you elaborate on that?"

    async def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep that returns early if the abort event is set."""
        try:
            await asyncio.wait_for(self._abort.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass  # Normal: abort wasn't set, sleep completed
