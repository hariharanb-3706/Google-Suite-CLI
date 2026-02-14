"""
OAuth 2.0 authentication handler for Google APIs
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# OAuth scopes for different Google services
SCOPES = {
    'calendar': ['https://www.googleapis.com/auth/calendar'],
    'gmail': ['https://www.googleapis.com/auth/gmail.modify'],
    'sheets': ['https://www.googleapis.com/auth/spreadsheets'],
    'drive': ['https://www.googleapis.com/auth/drive'],
    'tasks': ['https://www.googleapis.com/auth/tasks'],
    'documents': ['https://www.googleapis.com/auth/documents'],
}

# Combined scopes for all services
ALL_SCOPES = list(set(scope for scopes in SCOPES.values() for scope in scopes))


class OAuthManager:
    """Manages OAuth 2.0 authentication for Google APIs"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / '.config' / 'gsuite-cli'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.config_dir / 'token.json'
        self.credentials_file = self.config_dir / 'credentials.json'
        
    def get_credentials(self, scopes: Optional[list] = None) -> Optional[Credentials]:
        """
        Get valid user credentials from storage or initiate OAuth flow
        
        Args:
            scopes: List of OAuth scopes. If None, uses all available scopes.
            
        Returns:
            Credentials object or None if authentication fails
        """
        scopes = scopes or ALL_SCOPES
        creds = None
        
        # Load existing credentials
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), scopes)
                logger.debug("Loaded existing credentials")
            except Exception as e:
                logger.warning(f"Failed to load credentials: {e}")
                self.token_file.unlink(missing_ok=True)
        
        # If credentials are invalid or missing, initiate OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.debug("Refreshed expired credentials")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                creds = self._run_oauth_flow(scopes)
                if not creds:
                    return None
        
        # Save credentials for future use
        self._save_credentials(creds)
        return creds
    
    def _run_oauth_flow(self, scopes: list) -> Optional[Credentials]:
        """
        Run the OAuth 2.0 authorization flow
        
        Args:
            scopes: List of OAuth scopes
            
        Returns:
            Credentials object or None if user cancels
        """
        if not self.credentials_file.exists():
            logger.error(f"Credentials file not found: {self.credentials_file}")
            logger.error("Please download credentials.json from Google Cloud Console")
            logger.error("And place it in: ~/.config/gsuite-cli/credentials.json")
            return None
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), scopes
            )
            creds = flow.run_local_server(port=0)
            logger.info("Authentication successful")
            return creds
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file"""
        try:
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
            logger.debug("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def revoke_credentials(self) -> bool:
        """Revoke stored credentials"""
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Credentials revoked successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if not self.token_file.exists():
            return False
        
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), ALL_SCOPES)
            return creds.valid
        except Exception:
            return False
    
    def get_auth_info(self) -> Dict[str, Any]:
        """Get authentication information"""
        if not self.is_authenticated():
            return {"authenticated": False}
        
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_file), ALL_SCOPES)
            return {
                "authenticated": True,
                "valid": creds.valid,
                "expired": creds.expired,
                "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
                "refresh_token": bool(creds.refresh_token),
            }
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
    
    def build_service(self, service_name: str, version: str = 'v3'):
        """
        Build a Google API service client
        
        Args:
            service_name: Name of the Google service (e.g., 'calendar', 'gmail')
            version: API version
            
        Returns:
            Service resource object or None if authentication fails
        """
        creds = self.get_credentials(SCOPES.get(service_name, ALL_SCOPES))
        if not creds:
            return None
        
        try:
            service = build(service_name, version, credentials=creds)
            logger.debug(f"Built {service_name} service client")
            return service
        except Exception as e:
            logger.error(f"Failed to build {service_name} service: {e}")
            return None
