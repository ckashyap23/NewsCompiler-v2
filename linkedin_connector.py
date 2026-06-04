"""
LinkedIn Post Connector

Posts messages and newsletters to LinkedIn using OAuth2 API.

Requires authentication via linkedin_auth.py first:
    python linkedin_auth.py authenticate

Usage:
    from linkedin_connector import post_to_linkedin
    
    post_to_linkedin("Your message here")
    post_to_linkedin("Message", title="📰 Newsletter")
"""
import logging
import os
import requests
from typing import Optional
from dotenv import load_dotenv

from linkedin_auth import get_valid_access_token

load_dotenv()

logger = logging.getLogger(__name__)

LINKEDIN_API_BASE = "https://api.linkedin.com/rest"
LINKEDIN_API_VERSION = (os.getenv("LINKEDIN_API_VERSION") or "202506").strip()


def _build_headers(access_token: str, include_version: bool = True) -> dict:
    """Build LinkedIn API headers with optional version pinning."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    if include_version:
        headers["LinkedIn-Version"] = LINKEDIN_API_VERSION
    return headers


def _get_author_urn(access_token: str) -> Optional[str]:
    """Resolve the LinkedIn author URN required for posting."""
    configured_urn = (os.getenv("LINKEDIN_AUTHOR_URN") or "").strip()
    if configured_urn:
        return configured_urn

    # Preferred for apps with OpenID products enabled.
    try:
        userinfo_resp = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if userinfo_resp.status_code == 200:
            sub = (userinfo_resp.json() or {}).get("sub")
            if sub:
                return f"urn:li:person:{sub}"
    except requests.RequestException:
        pass

    return None


def post_to_linkedin(
    content: str,
    title: Optional[str] = None,
) -> bool:
    """
    Post content to LinkedIn using OAuth2 API.

    Args:
        content: The post content/body.
        title: Optional title for the post (prepended to content).

    Returns:
        True if successful, False otherwise.

    Raises:
        ValueError: If not authenticated (no valid token).
    """
    try:
        access_token = get_valid_access_token()
        author_urn = _get_author_urn(access_token)

        if not author_urn:
            logger.error(
                "Could not determine LinkedIn author URN.\n"
                "  1. Go to https://www.linkedin.com/developers/tools/oauth/token-inspector\n"
                "  2. Paste your access token to find your member ID\n"
                "  3. Set in .env:  LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_MEMBER_ID\n"
                "  Your token: %s...",
                (get_valid_access_token() or "")[:30],
            )
            return False
        
        post_text = content
        if title:
            post_text = f"{title}\n\n{content}"
        
        headers = _build_headers(access_token, include_version=True)
        
        payload = {
            "author": author_urn,
            "commentary": post_text,
            "lifecycleState": "PUBLISHED",
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "isReshareDisabledByAuthor": False,
        }
        
        url = f"{LINKEDIN_API_BASE}/posts"
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        # If requested API version is inactive, retry once without explicit version.
        if response.status_code == 426 and "NONEXISTENT_VERSION" in response.text:
            logger.warning(
                "LinkedIn API version '%s' is inactive. Retrying without LinkedIn-Version header.",
                LINKEDIN_API_VERSION,
            )
            response = requests.post(
                url,
                json=payload,
                headers=_build_headers(access_token, include_version=False),
                timeout=10,
            )
        
        if response.status_code in (201, 200, 202):
            logger.info("✓ Successfully posted to LinkedIn")
            return True
        else:
            logger.error(
                f"LinkedIn API error: {response.status_code} - {response.text}"
            )
            return False
        
    except ValueError as e:
        logger.error(f"Authentication required: {e}")
        return False
    except requests.RequestException as e:
        logger.error(f"Failed to post to LinkedIn: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error posting to LinkedIn: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("LinkedIn Post Connector Test")
    print("=" * 60)
    
    try:
        token = get_valid_access_token()
        print(f"✓ Valid access token found")
        print(f"  Token (first 20 chars): {token[:20]}...")
        
        success = post_to_linkedin("Test post from cnews-compiler. #testing")
        
        if success:
            print("✓ Successfully posted test content to LinkedIn")
        else:
            print("✗ Failed to post test content")
            
    except ValueError as e:
        print(f"✗ Authentication required: {e}")
        print("\nTo authenticate, run:")
        print("  python linkedin_auth.py authenticate")
