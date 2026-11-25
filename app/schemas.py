from typing import Literal
from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    identity: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Register(Input):
    username: str = Field(pattern=r"^\S{3,40}$")
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def lowered(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class ProfileEdit(Input):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None


class PasswordReset(Input):
    password: str = Field(min_length=10, max_length=128)


class AdminCreate(Input):
    username: str = Field(pattern=r"^\S{3,40}$")
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    permissions: list[Literal["studio", "characters", "workflows", "users", "generations", "codes", "servers", "audit"]] = Field(max_length=8)

    @field_validator("username", mode="before")
    @classmethod
    def lowered(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class AdminEdit(Input):
    name: str = Field(min_length=1, max_length=120)
    active: bool = True
    permissions: list[Literal["studio", "characters", "workflows", "users", "generations", "codes", "servers", "audit"]] = Field(max_length=8)
    password: str | None = Field(default=None, min_length=10, max_length=128)


class DeleteConfirm(Input):
    confirm: str = Field(min_length=1, max_length=64)


class RedeemInput(Input):
    code: str = Field(min_length=4, max_length=40)


class CodeInput(Input):
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{4,40}$")
    credits: int = Field(ge=1, le=100000)
    max_uses: int = Field(ge=1, le=100000)
    expires_at: datetime | None = None
    note: str = Field(default="", max_length=200)


class CodeUpdate(Input):
    active: bool
    max_uses: int = Field(ge=1, le=100000)
    expires_at: datetime | None = None
    note: str = Field(default="", max_length=200)


class PasswordChange(Input):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class Lora(Input):
    name: str = Field(min_length=1, max_length=200)
    strength: float = Field(default=1, ge=-2, le=2)


class ModelInput(Input):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    name: str = Field(min_length=1, max_length=120)
    character_prompt: str = Field(default="", max_length=4000)
    eye_prompt: str = Field(default="", max_length=1000)
    active: bool = True
    loras: list[Lora] = Field(default_factory=list, max_length=6)


class GpuInput(Input):
    name: str = Field(min_length=1, max_length=100)
    url: str | None = Field(default=None, max_length=1000)
    token: str | None = Field(default=None, max_length=2000)
    enabled: bool = True
    exclusive: bool = False
    workflow_ids: list[str] = Field(default_factory=lambda: ["generate", "reference"], max_length=20)


class UserAccess(Input):
    active: bool
    can_generate: bool


class CreditGrant(Input):
    amount: int = Field(ge=-100000, le=100000)
    reference: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,80}$")
    note: str = Field(min_length=1, max_length=200)


class JobParams(Input):
    model_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    prompt: str = Field(min_length=1, max_length=4000)
    seed: int | None = Field(default=None, ge=-1, le=9007199254740991)
    batch: int = Field(default=1, ge=1, le=2)
    ratio: Literal["1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9"] = "4:5"
    resolution: Literal[1280, 1920, 2560] = 1920
    upload_ids: list[UUID] = Field(default_factory=list, max_length=4)


class JobCreate(Input):
    workflow_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    params: JobParams


class GenerationSettings(Input):
    max_batch: int = Field(ge=1, le=2)
    ratios: list[Literal["1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9"]] = Field(min_length=1, max_length=10)

    @field_validator("ratios")
    @classmethod
    def unique_ratios(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Los formatos no pueden repetirse.")
        return values


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str | None
    name: str
    role: Literal["admin", "member"]
    active: bool
    can_generate: bool
    owner: bool = False
    permissions: list[str] = []


class SessionOut(BaseModel):
    user: UserOut | None
    csrf: str


class ModelPublic(BaseModel):
    id: str
    name: str


class WorkflowPublic(BaseModel):
    id: str
    name: str
    mode: Literal["generate", "reference"]
    cost: int
    version: int
    references: int = 0


class CatalogOut(BaseModel):
    models: list[ModelPublic]
    workflows: list[WorkflowPublic]
    credits: int
    can_generate: bool
    ratios: list[str]
    resolutions: list[int]
    max_batch: int


class OutputOut(BaseModel):
    id: UUID
    mime: str
    bytes: int


class JobOut(BaseModel):
    id: UUID
    workflow_id: str
    model_name: str
    status: Literal["queued", "running", "succeeded", "failed", "canceled"]
    progress: int
    cost: int
    params: dict[str, Any]
    error: str | None
    cancel_requested: bool
    created_at: datetime
    outputs: list[OutputOut]


class JobListOut(BaseModel):
    items: list[JobOut]
    next_offset: int | None


class GalleryItem(BaseModel):
    id: UUID
    name: str
    workflow_id: str
    ratio: str | None
    created_at: datetime


class GalleryOut(BaseModel):
    items: list[GalleryItem]
    next_offset: int | None


class SignedUrlOut(BaseModel):
    url: str
    expires_at: int
