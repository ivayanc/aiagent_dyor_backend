import requests
from typing import Dict, Any, Optional
from docx import Document
import logging
import re

logger = logging.getLogger(__name__)

class DYORParser:
    DEFAULT_LORE = """You are a DYOR (Do Your Own Research) report parser.
    Your task is to extract structured information from cryptocurrency project research reports.
    Parse the given text and return only the requested JSON structure with relevant URLs and data.
    If a field is not found, use null instead of leaving it empty."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, prompt: str, lore: Optional[str] = None) -> Dict[str, Any]:
        """
        Make API request to OpenAI with specific DYOR parsing instructions
        """
        if lore is None:
            lore = self.DEFAULT_LORE

        try:
            # Upload file first
            files = {
                'file': ('report.txt', prompt, 'text/plain'),
                'purpose': (None, 'assistants')
            }
            file_upload_response = requests.post(
                f"{self.base_url}/files",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files
            )
            file_upload_response.raise_for_status()
            file_id = file_upload_response.json()['id']

            # Make the chat completion request with file reference
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "messages": [
                        {"role": "system", "content": lore},
                        {"role": "user", "content": f"""
                            Parse the following DYOR report and extract information in this exact JSON structure:
                            {{
                                "token_name": string,
                                "token_symbol": string,
                                "token_address": string,
                                "token_chain": string,
                                "github": url or null,
                                "website": url or null,
                                "whitepaper": url or null,
                                "socials": {{
                                    "twitter": url or null,
                                    "telegram": url or null,
                                    "discord": url or null,
                                    "medium": url or null
                                }},
                                "contract_audit": {{
                                    "audited": boolean,
                                    "audit_link": url or null,
                                    "audit_company": string or null
                                }},
                                "team": {{
                                    "doxxed": boolean,
                                    "team_members": [
                                        {{
                                            "name": string,
                                            "role": string,
                                            "linkedin": url or null
                                        }}
                                    ]
                                }}
                            }}

                            DYOR Report text:
                            {prompt}
                        """}
                    ],
                    "model": "gpt-4",
                    "temperature": 0.3,
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
        Process and validate the JSON response
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
            # Attempt to parse the JSON response to ensure it's valid
            import json
            parsed_json = json.loads(content)
            return {
                "success": True,
                "error": None,
                "response": parsed_json,
                "raw_response": response
            }
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return {
                "success": False,
                "error": f"Failed to parse response: {str(e)}",
                "response": None,
                "raw_response": response
            }
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload file to OpenAI API
        """
        try:
            with open(file_path, 'rb') as file:
                response = requests.post(
                    "https://api.openai.com/v1/files",
                    headers={
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    files={
                        'file': file,
                        'purpose': 'assistants'
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
   
    def extract_urls_from_docx(self, file_path: str):
        """
        Extract all URLs from a .docx file
        
        Args:
            file_path (str): Path to the .docx file
        
        Returns:
            List[str]: List of URLs found in the document
        """
        logger.error(f"@@@@@Extracting URLs from {file_path}")
        try:
            # Open the docx file
            doc = Document(file_path)
            
            # Regular expression pattern for matching URLs
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            
            urls = []
            logger.error(f"!!!!!Found {len(doc.paragraphs)} paragraphs")
            # Iterate through all paragraphs
            for paragraph in doc.paragraphs:
                # Find all URLs in the paragraph text
                print(paragraph.text)
                found_urls = re.findall(url_pattern, paragraph.text)
                urls.extend(found_urls)
            
            # Remove duplicates while preserving order
            unique_urls = list(dict.fromkeys(urls))
            
            return unique_urls
            
        except Exception as e:
            logger.error(f"@@@@@Error extracting URLs from {file_path}: {str(e)}")
            return []