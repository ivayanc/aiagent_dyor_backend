import requests
from typing import Dict, Optional

class DiscordConnector:
    def __init__(self):
        self.base_url = "http://discord.com/api/v9"

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """
        Make HTTP request to Discord API
        
        Args:
            endpoint (str): API endpoint path
            
        Returns:
            dict: Response data if successful, None if failed
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(
                url,
                params={"with_counts": "true"}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error making Discord API request: {e}")
            return None

    def get_followers(self, username: str) -> Optional[int]:
        """
        Get approximate member count for a Discord server
        
        Args:
            username (str): Discord vanity URL code/username
            
        Returns:
            int: Approximate member count if successful, None if failed
        """
        response = self._make_request(f"invites/{username}")
        if response and "approximate_member_count" in response:
            return response["approximate_member_count"]
        return None
