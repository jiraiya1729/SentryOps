import logging
import re
from datetime import datetime
from typing import Optional

from github import Github, GithubException, UnknownObjectException
from pydantic import BaseModel

from app.integrations.github.auth import github_auth

logger = logging.getLogger(__name__)

SHA_PATTERNS = [
    r"^[a-f0-9]{40}$",
    r"^[a-f0-9]{7,12}$",
    r"[:-]([a-f0-9]{7,12})$",
    r"-(main|master|dev|prod)-([a-f0-9]{7,12})$",
]


def extract_git_sha_from_image(image: str) -> Optional[str]:
    """Extract git SHA from image tag if present."""
    if ":" not in image:
        return None

    tag = image.split(":")[-1]

    for pattern in SHA_PATTERNS:
        match = re.search(pattern, tag)
        if match:
            if match.groups():
                return match.group(match.lastindex)
            else:
                return match.group(0)

    return None


class GitCommit(BaseModel):
    sha: str
    message: str
    author: str
    author_email: str
    timestamp: datetime
    url: str
    files_changed: list[str]
    additions: int
    deletions: int


class GitPullRequest(BaseModel):
    number: int
    title: str
    url: str
    state: str
    merged: bool
    merged_at: Optional[datetime] = None
    author: str


class DeploymentContext(BaseModel):
    commit: GitCommit
    pull_request: Optional[GitPullRequest] = None
    repository: str
    branch: Optional[str] = None


class GitContextService:

    def __init__(self):
        self.github_auth = github_auth

    async def get_deployment_context(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
    ) -> Optional[DeploymentContext]:
        if not self.github_auth:
            logger.warning("GitHub auth not configured")
            return None

        try:
            installation_id = await self.github_auth.get_installation_id_for_repo(owner, repo)
            if not installation_id:
                logger.warning(f"No GitHub App installation for {owner}/{repo}")
                return None

            client = await self.github_auth.get_client_for_installation(installation_id)
            gh_repo = client.get_repo(f"{owner}/{repo}")

            try:
                commit = gh_repo.get_commit(commit_sha)
            except UnknownObjectException:
                logger.warning(f"Commit {commit_sha} not found in {owner}/{repo}")
                return None

            git_commit = GitCommit(
                sha=commit.sha,
                message=commit.commit.message,
                author=commit.commit.author.name,
                author_email=commit.commit.author.email,
                timestamp=commit.commit.author.date,
                url=commit.html_url,
                files_changed=[f.filename for f in commit.files],
                additions=commit.stats.additions,
                deletions=commit.stats.deletions,
            )

            pull_request = await self._find_pr_for_commit(gh_repo, commit.sha)

            return DeploymentContext(
                commit=git_commit,
                pull_request=pull_request,
                repository=f"{owner}/{repo}",
                branch=None,
            )

        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching git context: {e}")
            return None

    async def _find_pr_for_commit(self, repo, commit_sha: str) -> Optional[GitPullRequest]:
        try:
            prs = repo.get_pulls(state="closed", sort="updated", direction="desc")

            for pr in prs[:50]:
                commits = pr.get_commits()
                for pr_commit in commits:
                    if pr_commit.sha == commit_sha:
                        return GitPullRequest(
                            number=pr.number,
                            title=pr.title,
                            url=pr.html_url,
                            state=pr.state,
                            merged=pr.merged,
                            merged_at=pr.merged_at,
                            author=pr.user.login,
                        )

            return None
        except Exception as e:
            logger.error(f"Error finding PR for commit: {e}")
            return None

    async def get_commit_diff(
        self,
        owner: str,
        repo: str,
        commit_sha: str,
        file_path: Optional[str] = None,
    ) -> Optional[str]:
        if not self.github_auth:
            return None

        try:
            installation_id = await self.github_auth.get_installation_id_for_repo(owner, repo)
            if not installation_id:
                return None

            client = await self.github_auth.get_client_for_installation(installation_id)
            gh_repo = client.get_repo(f"{owner}/{repo}")
            commit = gh_repo.get_commit(commit_sha)

            if file_path:
                for file in commit.files:
                    if file.filename == file_path:
                        return file.patch
                return None
            else:
                diffs = []
                for file in commit.files:
                    if file.patch:
                        diffs.append(f"--- {file.filename}\n{file.patch}")
                return "\n\n".join(diffs)

        except Exception as e:
            logger.error(f"Error fetching diff: {e}")
            return None

    async def enrich_deployment_with_context(self, deployment_id: str):
        # TODO: implement after deployment schema is created
        pass


git_context_service = GitContextService()
