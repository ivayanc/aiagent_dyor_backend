import requests
from typing import Dict, Any, Optional


class OpenAI:
    DEFAULT_LORE = "You are a helpful assistant."

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, prompt: str, lore: Optional[str] = None) -> Dict[str, Any]:
        """
        Make API request to OpenAI
        """
        if lore is None:
            lore = self.DEFAULT_LORE
        print(f"Making request to {self.base_url}/chat/completions")
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "messages": [
                        {"role": "system", 
                         "content": lore},
                        {"role": "user", "content": prompt}
                    ],
                    "model": "gpt-4o-mini",
                    "temperature": 0.7,
                    "max_tokens": 8000
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

    def generate_response(self, prompt: str, lore: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate response from OpenAI with standardized output format
        """
        raw_response = self._make_request(prompt, lore)
        return self.process_response(raw_response)

    def chat(self, prompt: str, lore: Optional[str] = None) -> str:
        """
        Simple chat interface that returns just the response text
        """
        result = self.generate_response(prompt, lore)
        if result["success"]:
            return result["response"]
        else:
            return f"Error: {result['error']}"
