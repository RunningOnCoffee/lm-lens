"""Generate a deterministic prompt plan from a scenario snapshot + seed.

A prompt plan is a list of session definitions, each containing pre-generated
user prompts for every turn. When two benchmark runs use the same scenario and
seed, they produce identical prompt plans — enabling fair side-by-side comparison.

Structure:
[
  {
    "session_index": 0,
    "profile_id": "uuid-string",
    "prompts": ["Turn 1 prompt", "Turn 2 prompt", ...]
  },
  ...
]
"""
from __future__ import annotations

import random
import re
import uuid

_VAR_PATTERN = re.compile(r"\$([A-Z_][A-Z0-9_]*)")


def generate_prompt_plan(scenario_snapshot: dict, seed: int) -> list[dict]:
    """Generate a fully deterministic prompt plan from a scenario and seed."""
    rng = random.Random(seed)
    plan: list[dict] = []
    session_index = 0

    profiles_data = scenario_snapshot.get("profiles", [])

    for sp in profiles_data:
        profile = sp.get("profile", {})
        behavior = sp.get("behavior_overrides") or profile.get("behavior_defaults", {})
        user_count = sp.get("user_count", 1)

        # Resolve templates
        templates = []
        for t in profile.get("conversation_templates", []):
            templates.append({
                "starter_prompt": t.get("starter_prompt", "Hello"),
                "follow_ups": t.get("follow_ups", []),
            })

        # Resolve universal follow-ups
        universal_fus = [
            fp.get("content", "")
            for fp in profile.get("follow_up_prompts", [])
            if fp.get("is_universal", False)
        ]

        # Resolve variables
        variables = {
            v["name"]: v.get("values", [])
            for v in profile.get("template_variables", [])
        }

        turns_range = behavior.get("turns_per_session", {"min": 1, "max": 3})
        session_mode = behavior.get("session_mode", "multi_turn")

        profile_id = str(profile.get("id", str(uuid.uuid4())))

        for _ in range(user_count):
            if not templates:
                session_index += 1
                continue

            template = rng.choice(templates)

            if session_mode == "single_shot":
                num_turns = 1
            else:
                num_turns = rng.randint(
                    turns_range.get("min", 1),
                    turns_range.get("max", 3),
                )

            prompts: list[str] = []
            for turn in range(num_turns):
                if turn == 0:
                    prompt = _substitute_vars(template["starter_prompt"], variables, rng)
                else:
                    prompt = _pick_follow_up(template, universal_fus, variables, rng)
                prompts.append(prompt)

            plan.append({
                "session_index": session_index,
                "profile_id": profile_id,
                "prompts": prompts,
            })
            session_index += 1

    return plan


def _substitute_vars(text: str, variables: dict[str, list[str]], rng: random.Random) -> str:
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        values = variables.get(var_name, [])
        return rng.choice(values) if values else match.group(0)
    return _VAR_PATTERN.sub(replacer, text)


def _pick_follow_up(
    template: dict,
    universal_fus: list[str],
    variables: dict[str, list[str]],
    rng: random.Random,
) -> str:
    follow_ups = template.get("follow_ups", [])
    if follow_ups:
        fu = rng.choice(follow_ups)
        content = fu["content"] if isinstance(fu, dict) else fu
        return _substitute_vars(content, variables, rng)
    if universal_fus:
        return _substitute_vars(rng.choice(universal_fus), variables, rng)
    return "Can you elaborate on that?"
