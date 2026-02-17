from unittest import TestCase
from unittest.mock import MagicMock, patch

from crabber.github_client import GitHubClient

MOCK_PROJECT_ITEMS_RESPONSE = {
    "data": {
        "organization": {
            "projectV2": {
                "items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "fieldValueByName": {"name": "Awaiting"},
                            "content": {
                                "number": 1,
                                "title": "First Issue",
                                "body": "Issue body 1",
                                "url": "https://github.com/org/repo/issues/1",
                                "updatedAt": "2025-06-01T00:00:00Z",
                                "repository": {
                                    "name": "repo",
                                    "owner": {"login": "org"},
                                },
                                "assignees": {"nodes": [{"login": "testuser"}]},
                            },
                        },
                        {
                            "fieldValueByName": {"name": "In Progress"},
                            "content": {
                                "number": 2,
                                "title": "Second Issue",
                                "body": "Issue body 2",
                                "url": "https://github.com/org/repo/issues/2",
                                "updatedAt": "2025-05-01T00:00:00Z",
                                "repository": {
                                    "name": "repo",
                                    "owner": {"login": "org"},
                                },
                                "assignees": {"nodes": [{"login": "otheruser"}]},
                            },
                        },
                    ],
                }
            }
        }
    }
}

MOCK_ISSUE_DETAILS_RESPONSE = {
    "data": {
        "repository": {
            "issue": {
                "number": 1,
                "title": "First Issue",
                "body": "Issue body",
                "url": "https://github.com/org/repo/issues/1",
                "updatedAt": "2025-06-01T00:00:00Z",
                "comments": {
                    "nodes": [
                        {
                            "body": "Latest comment text",
                            "author": {"login": "commenter"},
                            "createdAt": "2025-06-01T00:00:00Z",
                        }
                    ]
                },
            }
        }
    }
}

MOCK_ISSUE_NODE_ID_RESPONSE = {"data": {"repository": {"issue": {"id": "I_abc123"}}}}

MOCK_ADD_COMMENT_RESPONSE = {"data": {"addComment": {"commentEdge": {"node": {"id": "IC_xyz"}}}}}


class TestGitHubClient(TestCase):
    def test_init_requires_token(self):
        with patch("crabber.github_client.GITHUB_TOKEN", None):
            with self.assertRaises(ValueError, msg="GITHUB_TOKEN is required"):
                GitHubClient()

    def test_init_with_explicit_token(self):
        client = GitHubClient(token="test-token")
        assert client._token == "test-token"

    @patch("httpx.Client")
    def test_get_project_items(self, mock_httpx_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PROJECT_ITEMS_RESPONSE
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_client_instance

        client = GitHubClient(token="test-token")
        items = client.get_project_items("org", 42)

        assert len(items) == 2
        assert items[0].status == "Awaiting"
        assert items[0].content.title == "First Issue"
        assert items[0].assignees == ["testuser"]
        assert items[1].status == "In Progress"

    @patch("httpx.Client")
    def test_get_issue_details(self, mock_httpx_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_ISSUE_DETAILS_RESPONSE
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_client_instance

        client = GitHubClient(token="test-token")
        issue = client.get_issue_details("org", "repo", 1)

        assert issue.title == "First Issue"
        assert issue.comments[0].body == "Latest comment text"

    @patch("httpx.Client")
    def test_post_issue_comment(self, mock_httpx_client_cls):
        mock_response_node_id = MagicMock()
        mock_response_node_id.json.return_value = MOCK_ISSUE_NODE_ID_RESPONSE
        mock_response_node_id.raise_for_status.return_value = None

        mock_response_comment = MagicMock()
        mock_response_comment.json.return_value = MOCK_ADD_COMMENT_RESPONSE
        mock_response_comment.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.side_effect = [mock_response_node_id, mock_response_comment]
        mock_httpx_client_cls.return_value = mock_client_instance

        client = GitHubClient(token="test-token")
        client.post_issue_comment("org", "repo", 1, "Test comment")

        assert mock_client_instance.post.call_count == 2

    @patch("httpx.Client")
    def test_get_items_for_column(self, mock_httpx_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_PROJECT_ITEMS_RESPONSE
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_client_instance

        client = GitHubClient(token="test-token")
        items = client.get_items_for_column("org", 42, "Awaiting", "testuser")

        assert len(items) == 1
        assert items[0].content.title == "First Issue"

    @patch("httpx.Client")
    def test_graphql_error_raises(self, mock_httpx_client_cls):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errors": [{"message": "Bad query"}]}
        mock_response.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_httpx_client_cls.return_value = mock_client_instance

        client = GitHubClient(token="test-token")
        with self.assertRaises(RuntimeError):
            client.get_project_items("org", 42)
