import hmac
import hashlib
import logging
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("codeguard.github_service")

class GitHubService:
    """Service to interact with GitHub REST API, Webhooks, OAuth, and PR comments."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "CodeGuard-AI"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    @staticmethod
    def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
        """Verifies HMAC SHA256 signature from GitHub webhook events."""
        if not signature_header or not settings.GITHUB_WEBHOOK_SECRET:
            return True # Allow for development/testing if secret not configured

        hash_object = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)

    async def post_review_comment(self, repo_full_name: str, pr_number: int, comment_text: str, file_path: str = None, line_number: int = None) -> bool:
        """Posts AI review comment back to GitHub Pull Request."""
        if not self.token:
            logger.info(f"[Mock GitHub API] Posted review comment to {repo_full_name} PR #{pr_number}")
            return True

        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        payload = {"body": comment_text}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                return response.status_code in (200, 201)
            except Exception as e:
                logger.error(f"Failed to post GitHub comment: {e}")
                return False

    async def update_commit_status(self, repo_full_name: str, sha: str, state: str, description: str, target_url: str = None) -> bool:
        """Updates commit status on GitHub (pending, success, failure)."""
        if not self.token:
            logger.info(f"[Mock GitHub Status Check] {repo_full_name} @ {sha}: {state} - {description}")
            return True

        url = f"https://api.github.com/repos/{repo_full_name}/statuses/{sha}"
        payload = {
            "state": state, # pending, success, failure, error
            "target_url": target_url or "https://codeguard-ai.com",
            "description": description[:140],
            "context": "CodeGuard AI / Security & Quality Audit"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                return response.status_code in (200, 201)
            except Exception as e:
                logger.error(f"Failed to update GitHub status check: {e}")
                return False
