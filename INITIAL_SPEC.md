crabber/cli.py is to be run as a shell command accepting JSON formatted STDIN and responding with an exit code and optionally stdout/stderr response.

## Development

Use github projects V2 graphql api, with httpx

Suggest the most appropriate auth method for a process that is initiated via cron and cannot accept user input/interaction.

## `github_project_config.json` schema

github org projects v2 url structure: https://github.com/orgs/ORG_NAME/projects/NODE_ID

:: 
    {
        "project_id": {NODE_ID},
        "assignee": "{GITHUB_USERNAME}",
        "awaiting-task-column": "{COLUMN_NAME}", 
        "inprogress-task-column": "{COLUMN_NAME}",
        "in-review-task-column": "{COLUMN_NAME}",
    }

## CURRENT_PROJECT_STATE.md format

The CURRENT_PROJECT_STATE.md is a free form format.  Do a regex search for a pattern meeting the expected fields.


## Hooks
The following hooks are handled with the described actions.

### SessionStart

crabber takes the stderr and parses JSON using the python json module.
Using the `cwd` value, crabber looks for the `github_project_config.json` in the directory.

> LAST_ISSUE_STATE=(ON_GOING|COMPLETED|PENDING)

If `github_project_config.json` is found, it is loaded, and the following is performed:
- `CURRENT_PROJECT_STATE.md` is searched for LAST_ISSUE_ID and LAST_ISSUE_STATE.
    - if LAST_ISSUE_ID found AND LAST_ISSUE_STATE is ON_GOING or PENDING, get latest status of the related issue and compare to the LAST_UPDATED_DATETIME value.  IF current ISSUE updated datetime is newer, summurize the  full issue content, and add the lastest comment using the following template, return exit code 0:
    
        ```
        Here is a summury of the current issue:

            {{SUMMARY OUTPUT}}

        Review the latest comment below and address the comments, when complete run the `/checkpoint` command, then respond to the comments in the issue.
            {{LATEST COMMENT}}

        ```

    - If NO LAST_ISSUE_ID, retrieve the content of the top-most  (smallest index value) issue in awaiting-task-column that is assigned to the 'assignee' defined in the github_project_config.json data.  Return the following template to stdout and return exit code 0.

        ```
        Review the following and address the issue:
        
            {{ISSUE CONTENT}}
        ```
        
    - If not new updates, return exit code 0.

If no `github_project_config.json` is found, return exit code 0.

### Notification

> check claude code docs for Notification JSON structure.

Provide stdin parsed JSON input to the related github issue as a comment, with the following template:

    ```
    {{ JSON_MESSAGE }}: {{ JSON_TITLE }}
   
    Which should we do: 
    0: Continue
    2: <SOMETHING ELSE>
    ```

TODO: need to have a while loop and webhook detection function to handle issue commend response.
TODO: provide webhook for issue comment,

### Stop

> refer to claude code Stop message structure in docs.

Comment the input JSON `stopReason` to the related issue.

return exit code 0, then after returning the response a set STOP_SLEEP_SECONDS find the related claude process and kill it.
(Consider spawning a separate kill process)

TODO: Determine how to get the PID for the claude code process instance (mutiple may be running)

> STOP_SLEEP_SECONDS should be an envar configurable variable in settings.py.

## Exit Codes

- Exit 0: the action proceeds. For UserPromptSubmit and SessionStart hooks, anything you write to stdout is added to Claude’s context.
- Exit 2: the action is blocked. Write a reason to stderr, and Claude receives it as feedback so it can adjust.
- Any other exit code: the action proceeds. Stderr is logged but not shown to Claude. Toggle verbose mode with Ctrl+O to see these messages in the transcript.


