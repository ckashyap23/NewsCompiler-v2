"""
LinkedIn OAuth2 Authentication Module

Manages the complete OAuth2 authentication flow for LinkedIn including:
- Generating authorization URLs
- FastAPI callback server for handling redirects
- Exchanging auth codes for access tokens
- Refreshing expired tokens
- Storing/retrieving tokens securely

Environment Variables:
    LINKEDIN_CLIENT_ID - Your app's client ID
    LINKEDIN_CLIENT_SECRET - Your app's client secret (keep private!)
    LINKEDIN_REDIRECT_URI - OAuth2 redirect URL (default: http://localhost:8000/linkedin/callback)
    LINKEDIN_CALLBACK_PORT - Port for callback server (default: 8000)

Usage:
    # Authenticate with LinkedIn
    python linkedin_auth.py authenticate

    # Check token status
    python linkedin_auth.py status

    # Logout
    python linkedin_auth.py logout

    # Start callback server manually
    python linkedin_auth.py serve
"""
import os
import json
import logging
import webbrowser
import requests
import time
import threading
from typing import Optional
from pathlib import Path
from urllib.parse import urlencode, urlparse
from datetime import datetime, timedelta
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# LinkedIn OAuth2 endpoints
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Token storage
TOKEN_CACHE_FILE = Path.home() / ".cnews-compiler" / "linkedin_token.json"

# FastAPI app for callback handling
app = FastAPI(
    title="LinkedIn OAuth2 Callback Server",
    description="Handles OAuth2 callbacks from LinkedIn"
)


# ============================================================================
# Token Management Functions
# ============================================================================

def get_linkedin_credentials() -> tuple[str, str, str]:
    """
    Get LinkedIn OAuth2 credentials from environment.

    Returns:
        Tuple of (client_id, client_secret, redirect_uri).

    Raises:
        ValueError: If credentials are not set.
    """
    client_id = (os.getenv("LINKEDIN_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("LINKEDIN_CLIENT_SECRET") or "").strip()
    redirect_uri = (os.getenv("LINKEDIN_REDIRECT_URI") or "").strip()

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError(
            "LinkedIn OAuth2 credentials not configured. "
            "Set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, and LINKEDIN_REDIRECT_URI in .env"
        )

    return client_id, client_secret, redirect_uri


def generate_auth_url(state: str = "random123") -> str:
    """
    Generate LinkedIn OAuth2 authorization URL.

    Args:
        state: Random state string for security (cannot contain spaces).

    Returns:
        Authorization URL that user should visit.
    """
    client_id, _, redirect_uri = get_linkedin_credentials()
    scopes = (os.getenv("LINKEDIN_SCOPES") or "w_member_social").strip()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scopes,
    }

    url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    return url


def exchange_code_for_token(auth_code: str) -> dict:
    """
    Exchange authorization code for access token.

    Args:
        auth_code: The authorization code from LinkedIn callback.

    Returns:
        Token response dict with keys: access_token, expires_in, refresh_token, etc.

    Raises:
        requests.RequestException: If token exchange fails.
    """
    client_id, client_secret, redirect_uri = get_linkedin_credentials()

    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        
        # Add expiration timestamp
        token_data["obtained_at"] = datetime.utcnow().isoformat()
        
        logger.info("✓ Successfully obtained LinkedIn access token")
        return token_data
    except requests.RequestException as e:
        logger.error(f"Failed to exchange auth code for token: {e}")
        raise


def refresh_access_token(refresh_token: str) -> dict:
    """
    Refresh an expired access token using refresh token.

    Args:
        refresh_token: The refresh token from previous auth.

    Returns:
        New token response dict.

    Raises:
        requests.RequestException: If refresh fails.
    """
    client_id, client_secret, _ = get_linkedin_credentials()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(LINKEDIN_TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        token_data = response.json()
        token_data["obtained_at"] = datetime.utcnow().isoformat()
        
        logger.info("✓ Successfully refreshed LinkedIn access token")
        return token_data
    except requests.RequestException as e:
        logger.error(f"Failed to refresh access token: {e}")
        raise


def save_token(token_data: dict) -> None:
    """
    Save token to secure local cache.

    Args:
        token_data: The token response dict from LinkedIn.
    """
    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(TOKEN_CACHE_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    
    # Make file readable/writable only by owner (on Unix systems)
    if hasattr(os, "chmod"):
        os.chmod(TOKEN_CACHE_FILE, 0o600)
    
    logger.info(f"Token saved to {TOKEN_CACHE_FILE}")


def load_token() -> Optional[dict]:
    """
    Load token from local cache.

    Returns:
        Token dict if available, None otherwise.
    """
    if not TOKEN_CACHE_FILE.exists():
        return None

    try:
        with open(TOKEN_CACHE_FILE, "r") as f:
            token_data = json.load(f)
        logger.info("Loaded cached LinkedIn token")
        return token_data
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load cached token: {e}")
        return None


def is_token_expired(token_data: dict, buffer_seconds: int = 300) -> bool:
    """
    Check if token is expired (with safety buffer).

    Args:
        token_data: The token dict with obtained_at and expires_in.
        buffer_seconds: How many seconds before expiration to consider it expired (default 5 min).

    Returns:
        True if token is expired or will expire soon, False otherwise.
    """
    if not token_data:
        return True

    obtained_at_str = token_data.get("obtained_at")
    expires_in = token_data.get("expires_in")

    if not obtained_at_str or not expires_in:
        return True

    try:
        obtained_at = datetime.fromisoformat(obtained_at_str)
        expiration_time = obtained_at + timedelta(seconds=expires_in)
        now = datetime.utcnow()
        
        return now >= (expiration_time - timedelta(seconds=buffer_seconds))
    except (ValueError, TypeError):
        return True


def get_valid_access_token() -> str:
    """
    Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token string.

    Raises:
        ValueError: If no token is available and user hasn't authenticated.
        requests.RequestException: If token refresh fails.
    """
    # Headless / Render: use env var token directly (no file needed)
    env_token = (os.getenv("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if env_token:
        logger.info("Using LINKEDIN_ACCESS_TOKEN from environment.")
        return env_token

    token_data = load_token()
    if not token_data:
        raise ValueError(
            "No LinkedIn token found. Run: python linkedin_auth.py authenticate"
        )

    # Check if refresh token exists and use it if access token is expired
    if is_token_expired(token_data):
        refresh_token = token_data.get("refresh_token")
        
        if refresh_token:
            logger.info("Access token expired, refreshing...")
            token_data = refresh_access_token(refresh_token)
            save_token(token_data)
        else:
            raise ValueError(
                "Access token expired and no refresh token available. "
                "Re-authenticate: python linkedin_auth.py authenticate"
            )

    return token_data["access_token"]


# ============================================================================
# FastAPI Callback Server
# ============================================================================

def _get_success_html(token_data: dict) -> str:
    """Generate success page HTML."""
    expires_in_days = token_data.get("expires_in", 0) // 86400
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>✓ LinkedIn Authentication Successful</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                max-width: 500px;
                text-align: center;
            }}
            h1 {{
                color: #2ecc71;
                margin: 0 0 20px 0;
            }}
            .checkmark {{
                font-size: 60px;
                margin-bottom: 20px;
            }}
            .details {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                text-align: left;
                margin: 20px 0;
                font-size: 14px;
            }}
            .details dt {{
                font-weight: bold;
                color: #333;
            }}
            .details dd {{
                margin: 5px 0 15px 0;
                color: #666;
            }}
            .footer {{
                color: #666;
                font-size: 14px;
                margin-top: 20px;
            }}
            a {{
                color: #667eea;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark">✓</div>
            <h1>Authentication Successful!</h1>
            <p>Your LinkedIn account has been successfully authorized.</p>
            <div class="details">
                <dt>Status:</dt>
                <dd>✓ Authenticated and token saved</dd>
                <dt>Token Location:</dt>
                <dd>~/.cnews-compiler/linkedin_token.json</dd>
                <dt>Expires in:</dt>
                <dd>~{expires_in_days} days</dd>
                <dt>Auto-renewal:</dt>
                <dd>Enabled - token refreshes automatically</dd>
            </div>
            <p>You can now close this window and run:</p>
            <code style="background: #f5f5f5; padding: 10px; border-radius: 5px; display: inline-block;">python weekly_digest.py</code>
            <div class="footer">
                <p>To test the connection, run:</p>
                <code style="background: #f5f5f5; padding: 10px; border-radius: 5px; display: inline-block;">python linkedin_connector.py</code>
                <p><a href="https://www.linkedin.com/settings/applications">Manage app permissions</a></p>
            </div>
        </div>
    </body>
    </html>
    """


def _get_error_html(error_message: str, error_code: Optional[str] = None) -> str:
    """Generate error page HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>✗ LinkedIn Authentication Failed</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                max-width: 500px;
                text-align: center;
            }}
            h1 {{
                color: #e74c3c;
                margin: 0 0 20px 0;
            }}
            .cross {{
                font-size: 60px;
                margin-bottom: 20px;
            }}
            .error-box {{
                background: #ffe6e6;
                border: 2px solid #e74c3c;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
            }}
            .error-box dt {{
                font-weight: bold;
                color: #c0392b;
            }}
            .error-box dd {{
                color: #666;
                margin: 10px 0;
            }}
            .footer {{
                color: #666;
                font-size: 14px;
                margin-top: 20px;
            }}
            a {{
                color: #e74c3c;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="cross">✗</div>
            <h1>Authentication Failed</h1>
            <div class="error-box">
                <dt>Error:</dt>
                <dd>{error_message}</dd>
                {f'<dt>Code:</dt><dd>{error_code}</dd>' if error_code else ''}
            </div>
            <p>Try again by running:</p>
            <code style="background: #f5f5f5; padding: 10px; border-radius: 5px; display: inline-block;">python linkedin_auth.py authenticate</code>
            <div class="footer">
                <p>If the problem persists:</p>
                <ul style="text-align: left;">
                    <li>Check your app credentials in <code>.env</code></li>
                    <li>Verify redirect URI matches in <a href="https://www.linkedin.com/developers/apps">LinkedIn Portal</a></li>
                    <li>Ensure <code>w_member_social</code> scope is enabled</li>
                    <li>Check server logs for details</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/linkedin/callback", response_class=HTMLResponse)
async def linkedin_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
) -> str:
    """
    Handle LinkedIn OAuth2 callback.
    
    LinkedIn redirects here after user authorizes the app.
    Exchanges the authorization code for an access token.
    """
    logger.info(f"LinkedIn callback received - code:{code}, state:{state}, error:{error}")
    
    if error:
        error_msg = error_description or error
        logger.error(f"LinkedIn authorization error: {error_msg}")
        return _get_error_html(error_msg, error)
    
    if not code:
        logger.error("No authorization code in callback")
        return _get_error_html("No authorization code received from LinkedIn")
    
    try:
        logger.info("Exchanging authorization code for access token...")
        token_data = exchange_code_for_token(code)
        save_token(token_data)
        logger.info("✓ Successfully obtained and saved token")
        return _get_success_html(token_data)
    except Exception as e:
        logger.error(f"Failed to exchange code for token: {e}", exc_info=True)
        return _get_error_html(f"Token exchange failed: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root() -> str:
    """Root endpoint with server info."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LinkedIn OAuth2 Server</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #333; }
            code {
                background: #f5f5f5;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }
            pre {
                background: #333;
                color: #0f0;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }
            .status {
                display: inline-block;
                padding: 5px 10px;
                background: #2ecc71;
                color: white;
                border-radius: 5px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✓ LinkedIn OAuth2 Callback Server</h1>
            <p>Status: <span class="status">Running on port 8000</span></p>
            <h2>Usage</h2>
            <pre>python linkedin_auth.py authenticate</pre>
            <p>The server automatically starts during authentication and handles the OAuth2 callback.</p>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "LinkedIn OAuth2 Server"}


# ============================================================================
# Callback Server Management
# ============================================================================

def _is_callback_server_running(redirect_uri: str = None) -> bool:
    """Check if callback server is already running."""
    redirect_uri = redirect_uri or (os.getenv("LINKEDIN_REDIRECT_URI") or "").strip()
    parsed = urlparse(redirect_uri)
    if parsed.hostname not in {"localhost", "127.0.0.1"}:
        return False
    
    try:
        port = parsed.port or int(os.getenv("LINKEDIN_CALLBACK_PORT", 8000))
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def _start_callback_server(port: int):
    """Start callback server in background thread."""
    try:
        import uvicorn
        
        logger.info("Starting callback server on http://localhost:%s/ ...", port)
        logger.info("Callback endpoint: http://localhost:%s/linkedin/callback", port)
        
        def run_server():
            try:
                uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")
            except Exception as e:
                logger.warning(f"Callback server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)
        logger.info("✓ Callback server started")
        return True
    except Exception as e:
        logger.warning(f"Could not start callback server: {e}")
        return False


# ============================================================================
# Interactive Authentication
# ============================================================================

def authenticate_interactive() -> None:
    """
    Interactive OAuth2 authentication flow.
    
    Starts callback server, opens browser for user to authorize, then saves token.
    """
    print("\n" + "=" * 60)
    print("LinkedIn OAuth2 Authentication")
    print("=" * 60)

    redirect_uri = (os.getenv("LINKEDIN_REDIRECT_URI") or "").strip()
    parsed_redirect = urlparse(redirect_uri)
    callback_port = parsed_redirect.port or int(os.getenv("LINKEDIN_CALLBACK_PORT", 8000))
    
    if parsed_redirect.hostname in {"localhost", "127.0.0.1"}:
        if not _is_callback_server_running(redirect_uri):
            print(f"\n1. Starting callback server on port {callback_port}...")
            print(f"   Server URL: http://localhost:{callback_port}/")
            print(f"   Callback URL: http://localhost:{callback_port}/linkedin/callback")
            if not _start_callback_server(callback_port):
                print("   ⚠️  Could not start callback server internally")
                print("   Please run in another terminal: python linkedin_auth.py serve")
            else:
                print("   ✓ Callback server running")
    
    auth_url = generate_auth_url()
    
    print("\n2. Opening LinkedIn authorization in browser...")
    print(f"   URL: {auth_url}\n")

    try:
        webbrowser.open(auth_url)
        print("   ✓ Browser opened")
    except Exception as e:
        print(f"   Could not open browser automatically: {e}")
        print(f"   Please visit this URL manually: {auth_url}")

    print("\n3. Log in and authorize the app on LinkedIn")

    if parsed_redirect.hostname in {"localhost", "127.0.0.1"}:
        print(f"   The callback server will automatically receive your authorization")
        print(f"   and save the token. This may take a few seconds...")
        
        print("\n4. Waiting for authorization callback...")
        max_wait = 60
        for i in range(max_wait):
            time.sleep(1)
            token_data = load_token()
            if token_data and not is_token_expired(token_data):
                print("\n" + "=" * 60)
                print("✓ Authentication successful!")
                print("=" * 60)
                print(f"Token saved to: {TOKEN_CACHE_FILE}")
                print(f"Token expires in: {token_data.get('expires_in', 'unknown')} seconds")
                print("\nYou can now post to LinkedIn using: python weekly_digest.py")
                return
            
            if i % 5 == 0 and i > 0:
                print(f"   Still waiting... ({max_wait - i}s remaining)")
        
        print(f"   ❌ Timeout waiting for callback ({max_wait}s)")
        print("   Check the callback server logs for errors")
        print("   Or provide the auth code manually:\n")
    
    print(f"   You'll be redirected to: {redirect_uri}")
    print("\n5. Copy the 'code' parameter from the redirect URL")
    print("   Example: ...?code=HERE&state=...")

    auth_code = input("\nEnter the authorization code: ").strip()

    if not auth_code:
        print("❌ No code provided. Authentication cancelled.")
        return

    print("\n6. Exchanging code for access token...")
    try:
        token_data = exchange_code_for_token(auth_code)
        save_token(token_data)
        
        print("\n" + "=" * 60)
        print("✓ Authentication successful!")
        print("=" * 60)
        print(f"Token saved to: {TOKEN_CACHE_FILE}")
        print(f"Token expires in: {token_data.get('expires_in', 'unknown')} seconds")
        print("\nYou can now post to LinkedIn using: python weekly_digest.py")
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        logger.error(f"Auth failed: {e}", exc_info=True)


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI for OAuth2 authentication."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LinkedIn OAuth2 authentication")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("authenticate", help="Authenticate with LinkedIn")
    subparsers.add_parser("status", help="Show current authentication status")
    subparsers.add_parser("logout", help="Clear saved token")
    subparsers.add_parser("serve", help="Start callback server manually")
    
    args = parser.parse_args()
    
    if args.command == "authenticate":
        authenticate_interactive()
    elif args.command == "status":
        token_data = load_token()
        if token_data:
            expired = is_token_expired(token_data)
            status = "❌ EXPIRED" if expired else "✓ VALID"
            print(f"Token status: {status}")
            print(f"Obtained at: {token_data.get('obtained_at')}")
            print(f"Expires in: {token_data.get('expires_in')} seconds")
        else:
            print("No token saved. Run: python linkedin_auth.py authenticate")
    elif args.command == "logout":
        if TOKEN_CACHE_FILE.exists():
            TOKEN_CACHE_FILE.unlink()
            print(f"✓ Token removed: {TOKEN_CACHE_FILE}")
        else:
            print("No token to remove")
    elif args.command == "serve":
        import uvicorn
        redirect_uri = (os.getenv("LINKEDIN_REDIRECT_URI") or "").strip()
        parsed_redirect = urlparse(redirect_uri)
        port = parsed_redirect.port or int(os.getenv("LINKEDIN_CALLBACK_PORT", 8000))
        logger.info(f"Starting callback server on http://localhost:{port}/")
        logger.info(f"Callback endpoint: http://localhost:{port}/linkedin/callback")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
