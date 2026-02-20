---
description: Write a hand-off document capturing current project state for session continuity
disable-model-invocation: true
user-invocable: true
---

Write a hand-off document, `CHECKPOINT.md`, in the project's root directory so that work can be continued from the current point. Overwrite if it already exists.

The document MUST include:

- Key themes of tasks performed and their purpose
- Decisions made
- Open questions
- Current state of the project or task
- Remaining tasks
- Current git branch and commit (if in a git repository)
- GitHub issues being addressed, formatted as:

```
LAST_UPDATED_DATETIME=<issue last updated datetime>
LAST_ISSUE_ID=<comma-separated GitHub issue IDs>
LAST_ISSUE_STATE=ON_GOING|COMPLETED|PENDING
```

Include any additional context deemed necessary for a smooth hand-off.
