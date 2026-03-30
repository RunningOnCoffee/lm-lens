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
from app.seed_data.code_snippets import CODE_SNIPPETS
from app.seed_data.profiles import PROFILES

logger = logging.getLogger(__name__)


async def seed_profiles(session: AsyncSession) -> None:
    """Upsert all built-in profiles."""
    for profile_data in PROFILES:
        slug = profile_data["slug"]

        # Check if profile exists
        result = await session.execute(
            select(Profile).where(Profile.slug == slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing profile
            existing.name = profile_data["name"]
            existing.description = profile_data["description"]
            existing.behavior_defaults = profile_data["behavior_defaults"]
            profile = existing
            logger.info(f"Updated built-in profile: {slug}")
        else:
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
            logger.info(f"Created built-in profile: {slug}")

        # Flush to get the profile ID
        await session.flush()

        # Clear and re-seed conversation templates + follow-ups
        # Delete existing templates (cascades to follow-ups linked to templates)
        result = await session.execute(
            select(ConversationTemplate).where(
                ConversationTemplate.profile_id == profile.id
            )
        )
        for tmpl in result.scalars().all():
            await session.delete(tmpl)

        # Delete existing universal follow-ups (those not linked to a template)
        result = await session.execute(
            select(FollowUpPrompt).where(
                FollowUpPrompt.profile_id == profile.id,
                FollowUpPrompt.is_universal == True,
            )
        )
        for fu in result.scalars().all():
            await session.delete(fu)

        # Delete existing template variables
        result = await session.execute(
            select(TemplateVariable).where(
                TemplateVariable.profile_id == profile.id
            )
        )
        for tv in result.scalars().all():
            await session.delete(tv)

        await session.flush()

        # Re-create conversation templates with their follow-ups
        for tmpl_data in profile_data.get("conversation_templates", []):
            template = ConversationTemplate(
                id=uuid.uuid4(),
                profile_id=profile.id,
                category=tmpl_data["category"],
                starter_prompt=tmpl_data["starter_prompt"],
                expected_response_tokens=tmpl_data.get(
                    "expected_response_tokens", {"min": 50, "max": 500}
                ),
            )
            session.add(template)
            await session.flush()

            for fu_data in tmpl_data.get("follow_ups", []):
                follow_up = FollowUpPrompt(
                    id=uuid.uuid4(),
                    profile_id=profile.id,
                    template_id=template.id,
                    content=fu_data["content"],
                    is_universal=False,
                )
                session.add(follow_up)

        # Add universal follow-ups
        for fu_content in profile_data.get("universal_follow_ups", []):
            follow_up = FollowUpPrompt(
                id=uuid.uuid4(),
                profile_id=profile.id,
                template_id=None,
                content=fu_content,
                is_universal=True,
            )
            session.add(follow_up)

        # Add template variables
        for var_data in profile_data.get("template_variables", []):
            variable = TemplateVariable(
                id=uuid.uuid4(),
                profile_id=profile.id,
                name=var_data["name"],
                values=var_data["values"],
            )
            session.add(variable)

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


async def run_seed(session: AsyncSession) -> None:
    """Run all seed operations."""
    logger.info("Starting seed...")
    await seed_profiles(session)
    await seed_code_snippets(session)
    await session.commit()
    logger.info("Seed complete.")
