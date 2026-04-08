import random
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    ConversationTemplate,
    FollowUpPrompt,
    Profile,
    TemplateVariable,
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileRead,
    ProfileSummary,
    ProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _slugify(name: str) -> str:
    """Generate a base slug from a name (no uniqueness check)."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "custom-profile"


async def _unique_slug(name: str, db: AsyncSession) -> str:
    """Generate a slug that doesn't collide with existing ones."""
    base = _slugify(name)
    slug = base
    n = 1
    while True:
        exists = await db.execute(
            select(Profile.id).where(Profile.slug == slug).limit(1)
        )
        if not exists.scalar_one_or_none():
            return slug
        n += 1
        slug = f"{base}-{n}"


async def _next_clone_name(source_name: str, db: AsyncSession) -> str:
    """Find the next available numbered clone name.

    'Casual User' -> 'Casual User (1)', then '(2)', etc.
    'Casual User (3)' -> strips suffix, starts from next available.
    """
    base = re.sub(r"\s*\(\d+\)\s*$", "", source_name).strip()
    # Find all existing names that match "base (N)"
    pattern = f"{base} (%"
    result = await db.execute(
        select(Profile.name).where(Profile.name.like(pattern))
    )
    existing = {row[0] for row in result.all()}
    n = 1
    while f"{base} ({n})" in existing:
        n += 1
    return f"{base} ({n})"


async def _get_profile_or_404(
    profile_id: UUID, db: AsyncSession, *, eager: bool = False
) -> Profile:
    stmt = select(Profile).where(Profile.id == profile_id)
    if eager:
        stmt = stmt.options(
            selectinload(Profile.conversation_templates).selectinload(
                ConversationTemplate.follow_ups
            ),
            selectinload(Profile.follow_up_prompts),
            selectinload(Profile.template_variables),
        )
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
async def list_profiles(db: AsyncSession = Depends(get_db)) -> dict:
    tmpl_count_sub = (
        select(func.count())
        .where(ConversationTemplate.profile_id == Profile.id)
        .correlate(Profile)
        .scalar_subquery()
    )
    fu_count_sub = (
        select(func.count())
        .where(FollowUpPrompt.profile_id == Profile.id)
        .correlate(Profile)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Profile, tmpl_count_sub.label("tmpl_count"), fu_count_sub.label("fu_count"))
        .order_by(Profile.is_builtin.desc(), Profile.name)
    )
    rows = result.all()

    summaries = [
        ProfileSummary(
            id=p.id,
            slug=p.slug,
            name=p.name,
            description=p.description,
            is_builtin=p.is_builtin,
            template_count=tmpl_count or 0,
            follow_up_count=fu_count or 0,
        ).model_dump()
        for p, tmpl_count, fu_count in rows
    ]

    return {"data": summaries, "meta": {"total": len(summaries)}}


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------

@router.get("/{profile_id}", response_model=dict)
async def get_profile(profile_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    profile = await _get_profile_or_404(profile_id, db, eager=True)
    return {"data": ProfileRead.model_validate(profile).model_dump()}


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@router.post("", response_model=dict, status_code=201)
async def create_profile(
    body: ProfileCreate, db: AsyncSession = Depends(get_db)
) -> dict:
    profile = Profile(
        name=body.name,
        description=body.description,
        behavior_defaults=body.behavior_defaults.model_dump(),
        is_builtin=False,
        slug=await _unique_slug(body.name, db),
    )
    db.add(profile)
    await db.flush()

    for tmpl_data in body.conversation_templates:
        tmpl = ConversationTemplate(
            profile_id=profile.id,
            category=tmpl_data.category,
            starter_prompt=tmpl_data.starter_prompt,
            expected_response_tokens=tmpl_data.expected_response_tokens,
        )
        db.add(tmpl)
        await db.flush()
        for fu in tmpl_data.follow_ups:
            db.add(
                FollowUpPrompt(
                    profile_id=profile.id,
                    template_id=tmpl.id,
                    content=fu.content,
                    is_universal=False,
                )
            )

    for fu_data in body.follow_up_prompts:
        db.add(
            FollowUpPrompt(
                profile_id=profile.id,
                content=fu_data.content,
                is_universal=fu_data.is_universal,
            )
        )

    for var_data in body.template_variables:
        db.add(
            TemplateVariable(
                profile_id=profile.id,
                name=var_data.name,
                values=var_data.values,
            )
        )

    await db.commit()

    # Reload with eager loading
    profile = await _get_profile_or_404(profile.id, db, eager=True)
    return {"data": ProfileRead.model_validate(profile).model_dump()}


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@router.put("/{profile_id}", response_model=dict)
async def update_profile(
    profile_id: UUID,
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile = await _get_profile_or_404(profile_id, db)

    if body.name is not None:
        profile.name = body.name
        # Preserve slug for built-in profiles (needed for reset-to-defaults)
        if not profile.is_builtin:
            profile.slug = await _unique_slug(body.name, db)
    if body.description is not None:
        profile.description = body.description
    if body.behavior_defaults is not None:
        profile.behavior_defaults = body.behavior_defaults.model_dump()

    # Replace conversation templates if provided
    if body.conversation_templates is not None:
        await db.execute(
            delete(ConversationTemplate).where(
                ConversationTemplate.profile_id == profile.id
            )
        )
        await db.flush()
        for tmpl_data in body.conversation_templates:
            tmpl = ConversationTemplate(
                profile_id=profile.id,
                category=tmpl_data.category,
                starter_prompt=tmpl_data.starter_prompt,
                expected_response_tokens=tmpl_data.expected_response_tokens,
            )
            db.add(tmpl)
            await db.flush()
            for fu in tmpl_data.follow_ups:
                db.add(
                    FollowUpPrompt(
                        profile_id=profile.id,
                        template_id=tmpl.id,
                        content=fu.content,
                        is_universal=False,
                    )
                )

    # Replace follow-up prompts (universal ones) if provided
    if body.follow_up_prompts is not None:
        # Only delete follow-ups not tied to templates
        await db.execute(
            delete(FollowUpPrompt).where(
                FollowUpPrompt.profile_id == profile.id,
                FollowUpPrompt.template_id.is_(None),
            )
        )
        for fu_data in body.follow_up_prompts:
            db.add(
                FollowUpPrompt(
                    profile_id=profile.id,
                    content=fu_data.content,
                    is_universal=fu_data.is_universal,
                )
            )

    # Replace template variables if provided
    if body.template_variables is not None:
        await db.execute(
            delete(TemplateVariable).where(
                TemplateVariable.profile_id == profile.id
            )
        )
        for var_data in body.template_variables:
            db.add(
                TemplateVariable(
                    profile_id=profile.id,
                    name=var_data.name,
                    values=var_data.values,
                )
            )

    await db.commit()

    profile = await _get_profile_or_404(profile.id, db, eager=True)
    return {"data": ProfileRead.model_validate(profile).model_dump()}


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{profile_id}", response_model=dict)
async def delete_profile(
    profile_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    profile = await _get_profile_or_404(profile_id, db)

    if profile.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in profiles")

    await db.delete(profile)
    await db.commit()
    return {"data": {"deleted": True}}


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

@router.post("/{profile_id}/clone", response_model=dict, status_code=201)
async def clone_profile(
    profile_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    source = await _get_profile_or_404(profile_id, db, eager=True)

    clone_name = await _next_clone_name(source.name, db)
    clone = Profile(
        name=clone_name,
        description=source.description,
        behavior_defaults=dict(source.behavior_defaults),
        is_builtin=False,
        slug=await _unique_slug(clone_name, db),
    )
    db.add(clone)
    await db.flush()

    for tmpl in source.conversation_templates:
        new_tmpl = ConversationTemplate(
            profile_id=clone.id,
            category=tmpl.category,
            starter_prompt=tmpl.starter_prompt,
            expected_response_tokens=dict(tmpl.expected_response_tokens),
        )
        db.add(new_tmpl)
        await db.flush()
        for fu in tmpl.follow_ups:
            db.add(
                FollowUpPrompt(
                    profile_id=clone.id,
                    template_id=new_tmpl.id,
                    content=fu.content,
                    is_universal=False,
                )
            )

    for fu in source.follow_up_prompts:
        if fu.template_id is None:
            db.add(
                FollowUpPrompt(
                    profile_id=clone.id,
                    content=fu.content,
                    is_universal=fu.is_universal,
                )
            )

    for var in source.template_variables:
        db.add(
            TemplateVariable(
                profile_id=clone.id,
                name=var.name,
                values=list(var.values),
            )
        )

    await db.commit()

    clone = await _get_profile_or_404(clone.id, db, eager=True)
    return {"data": ProfileRead.model_validate(clone).model_dump()}


@router.post("/{profile_id}/reset", response_model=dict)
async def reset_profile(
    profile_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    """Reset a built-in profile to its original default values."""
    from app.seed_data.runner import reset_profile_to_defaults

    profile = await _get_profile_or_404(profile_id, db)

    if not profile.is_builtin:
        raise HTTPException(status_code=400, detail="Only built-in profiles can be reset")

    await reset_profile_to_defaults(db, profile)
    await db.commit()

    profile = await _get_profile_or_404(profile_id, db, eager=True)
    return {"data": ProfileRead.model_validate(profile).model_dump()}


# ---------------------------------------------------------------------------
# Conversation Preview
# ---------------------------------------------------------------------------

def _substitute_variables(text: str, variables: dict[str, list[str]]) -> str:
    """Replace $VAR_NAME placeholders with random values from the variable's pool."""
    def _replace(match: re.Match) -> str:
        name = match.group(1)
        values = variables.get(name)
        if values:
            return random.choice(values)
        return match.group(0)  # leave unchanged if no values

    return re.sub(r"\$([A-Z][A-Z0-9_]*)", _replace, text)


@router.post("/{profile_id}/preview", response_model=dict)
async def preview_conversation(
    profile_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    """Generate a sample multi-turn conversation from the profile's templates."""
    profile = await _get_profile_or_404(profile_id, db, eager=True)
    behavior = profile.behavior_defaults or {}

    # Build variable lookup
    variables: dict[str, list[str]] = {}
    for var in profile.template_variables:
        variables[var.name] = list(var.values)

    # Pick a random template
    templates = profile.conversation_templates
    if not templates:
        return {"data": {"turns": [], "template_category": None, "profile_name": profile.name}}

    tmpl = random.choice(templates)

    # Determine number of turns
    turns_cfg = behavior.get("turns_per_session", {"min": 1, "max": 3})
    num_turns = random.randint(turns_cfg["min"], turns_cfg["max"])

    turns: list[dict] = []

    # Turn 1: starter prompt
    turns.append({
        "turn": 1,
        "role": "user",
        "content": _substitute_variables(tmpl.starter_prompt, variables),
    })

    # Collect available follow-ups: template-specific + universal
    follow_ups = [fu.content for fu in tmpl.follow_ups]
    universal = [
        fu.content for fu in profile.follow_up_prompts if fu.is_universal
    ]
    all_follow_ups = follow_ups + universal

    # Subsequent turns
    for i in range(2, num_turns + 1):
        if all_follow_ups:
            content = random.choice(all_follow_ups)
        else:
            content = "Can you tell me more about that?"
        turns.append({
            "turn": i,
            "role": "user",
            "content": _substitute_variables(content, variables),
        })

    return {
        "data": {
            "profile_name": profile.name,
            "template_category": tmpl.category,
            "session_mode": behavior.get("session_mode", "multi_turn"),
            "turns": turns,
        }
    }
