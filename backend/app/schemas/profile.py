from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Behavior config (reused in profiles and scenarios) ---

class BehaviorConfig(BaseModel):
    session_mode: str = Field("multi_turn", pattern="^(multi_turn|single_shot)$")
    turns_per_session: dict = Field(default_factory=lambda: {"min": 3, "max": 8})
    think_time_seconds: dict = Field(default_factory=lambda: {"min": 5, "max": 45})
    sessions_per_user: dict = Field(default_factory=lambda: {"min": 1, "max": 3})
    read_time_factor: float = Field(0.02, description="Seconds per output token to simulate reading")


# --- Follow-up prompts ---

class FollowUpPromptBase(BaseModel):
    content: str
    is_universal: bool = False
    template_id: UUID | None = None

class FollowUpPromptCreate(FollowUpPromptBase):
    pass

class FollowUpPromptRead(FollowUpPromptBase):
    id: UUID
    profile_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Conversation templates ---

class ConversationTemplateBase(BaseModel):
    category: str = "general"
    starter_prompt: str
    expected_response_tokens: dict = Field(default_factory=lambda: {"min": 50, "max": 500})

class ConversationTemplateCreate(ConversationTemplateBase):
    follow_ups: list[FollowUpPromptCreate] = []

class ConversationTemplateRead(ConversationTemplateBase):
    id: UUID
    profile_id: UUID
    created_at: datetime
    follow_ups: list[FollowUpPromptRead] = []

    model_config = {"from_attributes": True}


# --- Template variables ---

class TemplateVariableBase(BaseModel):
    name: str
    values: list[str] = []

class TemplateVariableCreate(TemplateVariableBase):
    pass

class TemplateVariableRead(TemplateVariableBase):
    id: UUID
    profile_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Code snippets ---

class CodeSnippetBase(BaseModel):
    language: str
    pattern: str
    domain: str
    code: str

class CodeSnippetCreate(CodeSnippetBase):
    pass

class CodeSnippetRead(CodeSnippetBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Profiles ---

class ProfileBase(BaseModel):
    name: str
    description: str = ""
    behavior_defaults: BehaviorConfig = Field(default_factory=BehaviorConfig)

class ProfileCreate(ProfileBase):
    conversation_templates: list[ConversationTemplateCreate] = []
    template_variables: list[TemplateVariableCreate] = []
    follow_up_prompts: list[FollowUpPromptCreate] = []

class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    behavior_defaults: BehaviorConfig | None = None
    conversation_templates: list[ConversationTemplateCreate] | None = None
    template_variables: list[TemplateVariableCreate] | None = None
    follow_up_prompts: list[FollowUpPromptCreate] | None = None

class ProfileRead(ProfileBase):
    id: UUID
    slug: str | None
    is_builtin: bool
    created_at: datetime
    updated_at: datetime
    conversation_templates: list[ConversationTemplateRead] = []
    follow_up_prompts: list[FollowUpPromptRead] = []
    template_variables: list[TemplateVariableRead] = []

    model_config = {"from_attributes": True}


class ProfileSummary(BaseModel):
    id: UUID
    slug: str | None
    name: str
    description: str
    is_builtin: bool
    template_count: int = 0
    follow_up_count: int = 0

    model_config = {"from_attributes": True}
