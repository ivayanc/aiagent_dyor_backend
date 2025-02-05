import requests
from typing import Dict, Optional

from settings import TWITTER_API_KEY


class TwitterConnector:
    # https://rapidapi.com/davethebeast/api/twitter241

    def __init__(self):
        self.base_url = "https://twitter241.p.rapidapi.com"
        self.headers = {
            "x-rapidapi-host": "twitter241.p.rapidapi.com",
            "x-rapidapi-key": TWITTER_API_KEY
        }

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        Make HTTP request to Twitter API
        
        Args:
            endpoint (str): API endpoint path
            params (dict): Query parameters
            
        Returns:
            dict: Response data if successful, None if failed
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(
                url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error making Twitter API request: {e}")
            return None

    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        Fetch user information from Twitter via RapidAPI
        
        Args:
            username (str): Twitter username without @ symbol
            
        Returns:
            dict: User information if successful, None if failed
        """
        return self._make_request("user", {"username": username})
