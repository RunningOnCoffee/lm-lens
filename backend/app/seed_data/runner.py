"""
Seed runner — upserts built-in profiles on startup.
Uses slug as the stable identifier. Inserts if missing, updates if exists.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CodeSnippet,
    ConversationTemplate,
    FollowUpPrompt,
    Profile,
    TemplateVariable,
)
from app.models.endpoint import Endpoint
from app.seed_data.code_snippets import CODE_SNIPPETS
from app.seed_data.profiles import PROFILES

logger = logging.getLogger(__name__)


async def seed_profiles(session: AsyncSession) -> None:
    """Seed built-in profiles — only creates profiles that don't exist yet.
    User edits to built-in profiles are preserved across restarts.
    Use the /reset endpoint to restore a profile to defaults."""
    for profile_data in PROFILES:
        slug = profile_data["slug"]

        # Check if profile already exists
        result = await session.execute(
            select(Profile).where(Profile.slug == slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Built-in profile already exists, skipping: {slug}")
            continue

        # Create new profile
        profile = Profile(
            id=uuid.uuid4(),
            slug=slug,
            name=profile_data["name"],
            description=profile_data["description"],
            is_builtin=True,
            behavior_defaults=profile_data["behavior_defaults"],
        )
        session.add(profile)
        await session.flush()

        _seed_profile_children(session, profile.id, profile_data)
        await session.flush()
        logger.info(f"Created built-in profile: {slug}")

    await session.flush()


def _seed_profile_children(session: AsyncSession, profile_id, profile_data: dict) -> None:
    """Create conversation templates, follow-ups, and variables for a profile."""
    for tmpl_data in profile_data.get("conversation_templates", []):
        template = ConversationTemplate(
            id=uuid.uuid4(),
            profile_id=profile_id,
            category=tmpl_data["category"],
            starter_prompt=tmpl_data["starter_prompt"],
            expected_response_tokens=tmpl_data.get(
                "expected_response_tokens", {"min": 50, "max": 500}
            ),
        )
        session.add(template)

        for fu_data in tmpl_data.get("follow_ups", []):
            follow_up = FollowUpPrompt(
                id=uuid.uuid4(),
                profile_id=profile_id,
                template_id=template.id,
                content=fu_data["content"],
                is_universal=False,
            )
            session.add(follow_up)

    for fu_content in profile_data.get("universal_follow_ups", []):
        follow_up = FollowUpPrompt(
            id=uuid.uuid4(),
            profile_id=profile_id,
            template_id=None,
            content=fu_content,
            is_universal=True,
        )
        session.add(follow_up)

    for var_data in profile_data.get("template_variables", []):
        variable = TemplateVariable(
            id=uuid.uuid4(),
            profile_id=profile_id,
            name=var_data["name"],
            values=var_data["values"],
        )
        session.add(variable)


async def reset_profile_to_defaults(session: AsyncSession, profile: Profile) -> None:
    """Reset a built-in profile to its original seed data."""
    # Find the matching seed data by slug
    seed_data = next((p for p in PROFILES if p["slug"] == profile.slug), None)
    if seed_data is None:
        raise ValueError(f"No seed data found for slug: {profile.slug}")

    # Restore top-level fields
    profile.name = seed_data["name"]
    profile.description = seed_data["description"]
    profile.behavior_defaults = seed_data["behavior_defaults"]

    # Clear all child entities
    result = await session.execute(
        select(ConversationTemplate).where(
            ConversationTemplate.profile_id == profile.id
        )
    )
    for tmpl in result.scalars().all():
        await session.delete(tmpl)

    result = await session.execute(
        select(FollowUpPrompt).where(
            FollowUpPrompt.profile_id == profile.id,
            FollowUpPrompt.template_id.is_(None),
        )
    )
    for fu in result.scalars().all():
        await session.delete(fu)

    result = await session.execute(
        select(TemplateVariable).where(
            TemplateVariable.profile_id == profile.id
        )
    )
    for tv in result.scalars().all():
        await session.delete(tv)

    await session.flush()

    # Re-create from seed data
    _seed_profile_children(session, profile.id, seed_data)
    await session.flush()


async def seed_code_snippets(session: AsyncSession) -> None:
    """Upsert code snippets — clear and re-seed."""
    result = await session.execute(select(CodeSnippet))
    for snippet in result.scalars().all():
        await session.delete(snippet)
    await session.flush()

    for snippet_data in CODE_SNIPPETS:
        snippet = CodeSnippet(
            id=uuid.uuid4(),
            language=snippet_data["language"],
            pattern=snippet_data["pattern"],
            domain=snippet_data["domain"],
            code=snippet_data["code"],
        )
        session.add(snippet)

    await session.flush()


SEED_ENDPOINTS = [
    {
        "name": "Mock LLM Server",
        "endpoint_url": "http://lm-lens-mock:8000",
        "model_name": "mock-gpt",
        "inference_engine": "LM Lens Mock",
        "notes": "Built-in mock server for testing. Simulates streaming responses with configurable latency.",
    },
]


async def seed_endpoints(session: AsyncSession) -> None:
    """Seed built-in endpoints — only creates if none exist yet."""
    result = await session.execute(select(Endpoint))
    if result.scalars().first() is not None:
        logger.info("Endpoints already exist, skipping seed")
        return

    for ep_data in SEED_ENDPOINTS:
        endpoint = Endpoint(
            id=uuid.uuid4(),
            **ep_data,
        )
        session.add(endpoint)
        logger.info(f"Created seed endpoint: {ep_data['name']}")

    await session.flush()


async def run_seed(session: AsyncSession) -> None:
    """Run all seed operations."""
    logger.info("Starting seed...")
    await seed_profiles(session)
    await seed_code_snippets(session)
    await seed_endpoints(session)
    await session.commit()
    logger.info("Seed complete.")
