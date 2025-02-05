import requests
from bs4 import BeautifulSoup
import re
from typing import Optional

class TelegramScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.base_url = "https://t.me"

    def get_channel_followers(self, channel_name: str) -> int:
        """
        Get the number of followers for a Telegram channel
        
        Args:
            channel_name (str): Channel name without @ symbol (e.g. 'HyperliquidXofficial')
            
        Returns:
            int: Number of followers/members, or 0 if unable to fetch
        """
        url = f"{self.base_url}/{channel_name.strip('@')}"
        return self._parse_followers_count(self._fetch_channel_page(url))

    def _fetch_channel_page(self, url: str) -> Optional[str]:
        """
        Fetch the channel page HTML content
        
        Args:
            url (str): Channel URL
            
        Returns:
            Optional[str]: HTML content if successful, None otherwise
        """
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching Telegram channel: {e}")
            return None

    def _parse_followers_count(self, html_content: Optional[str]) -> int:
        """
        Parse the HTML content to extract followers count
        
        Args:
            html_content (Optional[str]): HTML content of the channel page
            
        Returns:
            int: Number of followers/members, or 0 if unable to parse
        """
        if not html_content:
            return 0

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            members_element = soup.find('div', class_='tgme_page_extra')
            
            if members_element:
                members_text = members_element.text.strip()
                members_count = re.search(r'([\d\s]+)\s+members?', members_text)
                if members_count:
                    return int(members_count.group(1).replace(' ', ''))
            
            return 0
            
        except Exception as e:
            print(f"Error parsing followers count: {e}")
            return 0
