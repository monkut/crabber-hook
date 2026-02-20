import enum

from pydantic import BaseModel, ConfigDict, Field


class IssueState(enum.StrEnum):
    ON_GOING = "ON_GOING"
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"


class GithubProjectConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: int
    org_name: str
    assignee: str
    awaiting_task_column: str = Field(alias="awaiting-task-column")
    inprogress_task_column: str = Field(alias="inprogress-task-column")
    in_review_task_column: str = Field(alias="in-review-task-column")


class HookInput(BaseModel):
    session_id: str
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


class Checkpoint(BaseModel):
    last_issue_id: str | None = None
    last_issue_state: str | None = None
    last_updated_datetime: str | None = None


class IssueComment(BaseModel):
    body: str
    author: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default="", alias="createdAt")


class IssueDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    number: int
    title: str
    body: str
    url: str
    updated_at: str = Field(alias="updatedAt")
    comments: list[IssueComment] = Field(default_factory=list)
