import requests
from typing import Dict, Any, Optional


class GrokAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.x.ai/v1"  # Example API endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, prompt: str) -> Dict[str, Any]:
        """
        Make API request to Grok AI
        """
        print(f"Making request to {self.base_url}/chat/completions")
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "messages": [
                        {"role": "system", 
                         "content": """
                         You are a ethereum trader.
                         You are professional psychologist.
                         You are analyze community of crypto token and provide details about the community.
                         You are analyze the toppest account that shilling that token. Do the doing it always for a lot of coins or only for that one.
                         Your response should contain psyhological analysis of the community.
                         Your response always should contain at the end return confident in procents about community will they rug token always in such format "Confidence in rugging token: your exepctection of rugging token in % ".
                         Your response should check if posts from community about this token is only shilling or they believe in this token.
                         Your response should analyze if community believe in this token.
                         Your task not to write steps what to check but provide analysis."""},
                        {"role": "user", "content": prompt}
                    ],
                    "model": "grok-2-1212"
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "success": False,
                "response": None
            }

    def process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and standardize the response format
        """
        if "error" in response:
            return {
                "success": False,
                "error": response["error"],
                "response": None,
                "raw_response": response
            }

        try:
            content = response["choices"][0]["message"]["content"]
            return {
                "success": True,
                "error": None,
                "response": content,
                "raw_response": response
            }
        except (KeyError, IndexError) as e:
            return {
                "success": False,
                "error": f"Failed to parse response: {str(e)}",
                "response": None,
                "raw_response": response
            }

    def generate_response(self, prompt: str) -> Dict[str, Any]:
        """
        Generate response from Grok AI with standardized output format
        """
        raw_response = self._make_request(prompt)
        return self.process_response(raw_response)

    def chat(self, prompt: str) -> str:
        """
        Simple chat interface that returns just the response text
        """
        result = self.generate_response(prompt)
        if result["success"]:
            return result["response"]
        else:
            return f"Error: {result['error']}"
