import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt
from github import Github, GithubIntegration, Auth
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
      
class GitHubAppConfig(BaseModel):
    app_id: int
    private_key: str
    webhook_secret: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

class GithubAppAuth:
    def __init__(self, config: GitHubAppConfig):
        self.config = config
        self.integration = GithubIntegration(integration_id=config.app_id, private_key = config.private_key)

        self._token_cache: dict[int, tuple[str, datetime]] = {}

    def generate_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - 60,  
            "exp": now + (10 * 60), 
            "iss": self.config.app_id,
        }

        encoded = jwt.encode(
            payload,
            self.config.private_key,
            algorithm="RS256"
        )

        return encoded

    async def get_installation_token(self, installation_id: int) -> str:
        if installation_id in self._token_cache:
            token, expires_at = self._token_cache[installation_id]

            if datetime.utcnow() < expires_at - timedelta(minutes=5):
                logger.debug(f"Using cached token for installation {installation_id}")
                return token

        logger.info(f"Generating new installation token for {installation_id}")
        auth = Auth.AppAuth(self.config.app_id, self.config.private_key)
        gi = GithubIntegration(auth=auth)

        token_response = gi.get_access_token(installation_id)
        token = token_response.token

        expires_at = datetime.utcnow() + timedelta(hours=1)
        self._token_cache[installation_id] = (token, expires_at)

        return token

    async def get_client_for_installation(self, installation_id: int) -> Github:
        token = await self.get_installation_token(installation_id=installation_id)
        return Github(token)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not signature:
            return False

        if not signature.startswith("sha256="):
            return False

        expected_sig = signature[7:]

        mac = hmac.new(self.config.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256,)
        computed_sig = mac.hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)

    async def get_installation_id_for_repo(self, owner: str, repo: str) -> Optional[int]:
        jwt_token = self.generate_jwt()
        g = Github(jwt=jwt_token)

        try:
            app = g.get_app()
            installations = app.get_installations()

            for installation in installations:
                repos = installation.get_repos()
                for r in repos:
                    if r.owner.login == owner and r.name == repo:
                        return installation.id
            return None

        except Exception as e:
            logger.error(f"Failed to get installation ID for {owner}/{repo}: {e}")
            return None


def get_github_auth() -> Optional[GithubAppAuth]:
    if not all([settings.GITHUB_APP_ID, settings.GITHUB_APP_PRIVATE_KEY, settings.GITHUB_WEBHOOK_SECRET]):
        logger.warning("Github app not configured - integration disabled")
        return None
    config = GitHubAppConfig(
        app_id=settings.GITHUB_APP_ID,
        private_key=settings.GITHUB_APP_PRIVATE_KEY,
        webhook_secret=settings.GITHUB_WEBHOOK_SECRET,
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
    )

    return GithubAppAuth(config)

github_auth = get_github_auth()