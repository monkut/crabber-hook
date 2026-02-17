import logging
from typing import TYPE_CHECKING, Self

import httpx

from crabber.definitions import IssueComment, IssueDetails, ProjectItem, ProjectItemContent
from crabber.settings import GITHUB_GRAPHQL_URL, GITHUB_TOKEN

if TYPE_CHECKING:
    from types import TracebackType

logger = logging.getLogger(__name__)

PROJECT_ITEMS_QUERY = """
query($org: String!, $projectNumber: Int!, $cursor: String) {
  organization(login: $org) {
    projectV2(number: $projectNumber) {
      items(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue {
              name
            }
          }
          content {
            ... on Issue {
              number
              title
              body
              url
              updatedAt
              repository {
                name
                owner {
                  login
                }
              }
              assignees(first: 20) {
                nodes {
                  login
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

ISSUE_DETAILS_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      number
      title
      body
      url
      updatedAt
      comments(last: 1) {
        nodes {
          body
          author {
            login
          }
          createdAt
        }
      }
    }
  }
}
"""

ADD_COMMENT_MUTATION = """
mutation($subjectId: ID!, $body: String!) {
  addComment(input: {subjectId: $subjectId, body: $body}) {
    commentEdge {
      node {
        id
      }
    }
  }
}
"""

ISSUE_NODE_ID_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
    }
  }
}
"""


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token or GITHUB_TOKEN
        if not self._token:
            msg = "GITHUB_TOKEN is required"
            raise ValueError(msg)
        self._headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(headers=self._headers, timeout=30.0)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def _execute_query(self, query: str, variables: dict) -> dict:
        response = self._client.post(
            GITHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        result = response.json()
        if "errors" in result:
            msg = f"GraphQL errors: {result['errors']}"
            raise RuntimeError(msg)
        return result["data"]

    def get_project_items(self, org: str, project_number: int) -> list[ProjectItem]:
        items: list[ProjectItem] = []
        cursor: str | None = None

        while True:
            variables: dict = {"org": org, "projectNumber": project_number, "cursor": cursor}
            data = self._execute_query(PROJECT_ITEMS_QUERY, variables)

            project_data = data["organization"]["projectV2"]["items"]
            for node in project_data["nodes"]:
                content_data = node.get("content")
                if not content_data or "number" not in content_data:
                    continue

                repo_data = content_data.get("repository", {})
                assignee_nodes = content_data.get("assignees", {}).get("nodes", [])
                assignees = [a["login"] for a in assignee_nodes]

                status_field = node.get("fieldValueByName")
                status = status_field["name"] if status_field else ""

                content = ProjectItemContent(
                    number=content_data["number"],
                    title=content_data["title"],
                    body=content_data.get("body", ""),
                    url=content_data["url"],
                    owner=repo_data.get("owner", {}).get("login", ""),
                    repo=repo_data.get("name", ""),
                )

                items.append(
                    ProjectItem(
                        status=status,
                        assignees=assignees,
                        content=content,
                        updated_at=content_data.get("updatedAt", ""),
                    )
                )

            page_info = project_data["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

        return items

    def get_issue_details(self, owner: str, repo: str, issue_number: int) -> IssueDetails:
        variables = {"owner": owner, "repo": repo, "number": issue_number}
        data = self._execute_query(ISSUE_DETAILS_QUERY, variables)
        issue_data = data["repository"]["issue"]
        comment_nodes = issue_data.get("comments", {}).get("nodes", [])
        return IssueDetails(
            number=issue_data["number"],
            title=issue_data["title"],
            body=issue_data.get("body", ""),
            url=issue_data["url"],
            updatedAt=issue_data["updatedAt"],
            comments=[IssueComment(**c) for c in comment_nodes],
        )

    def get_issue_node_id(self, owner: str, repo: str, issue_number: int) -> str:
        variables = {"owner": owner, "repo": repo, "number": issue_number}
        data = self._execute_query(ISSUE_NODE_ID_QUERY, variables)
        return data["repository"]["issue"]["id"]

    def post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> None:
        node_id = self.get_issue_node_id(owner, repo, issue_number)
        variables = {"subjectId": node_id, "body": body}
        self._execute_query(ADD_COMMENT_MUTATION, variables)

    def get_items_for_column(
        self,
        org: str,
        project_number: int,
        column_name: str,
        assignee: str,
    ) -> list[ProjectItem]:
        all_items = self.get_project_items(org, project_number)
        return [item for item in all_items if item.status == column_name and assignee in item.assignees]
