import enum

from pydantic import BaseModel, Field


class IssueState(enum.StrEnum):
    ON_GOING = "ON_GOING"
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"


class GithubProjectConfig(BaseModel):
    project_id: int
    org_name: str
    assignee: str
    awaiting_task_column: str = Field(alias="awaiting-task-column")
    inprogress_task_column: str = Field(alias="inprogress-task-column")
    in_review_task_column: str = Field(alias="in-review-task-column")


class HookInput(BaseModel):
    session_id: str = Field(alias="session_id")
    cwd: str
    hook_event_name: str = ""


class NotificationHookInput(HookInput):
    title: str = ""
    message: str = ""


class StopHookInput(HookInput):
    stop_reason: str = Field(default="", alias="stopReason")


class ProjectItemContent(BaseModel):
    number: int
    title: str
    body: str
    url: str
    owner: str = ""
    repo: str = ""


class ProjectItem(BaseModel):
    status: str = ""
    assignees: list[str] = Field(default_factory=list)
    content: ProjectItemContent | None = None
    updated_at: str = ""
