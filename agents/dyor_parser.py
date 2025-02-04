import requests
from typing import Dict, Any, Optional
from docx import Document
import logging
import re

from agents.openai import OpenAI


logger = logging.getLogger(__name__)
logger.addFilter(lambda record: setattr(record, 'msg', f'ReportParser: {record.msg}') or True)



class DYORParser(OpenAI):
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

    def parse_document(self, file_path: str) -> str:
        """
        Parse a DOCX document into text with hyperlinks formatted as HyperText.
        Links are only processed within their original paragraphs.
        
        Args:
            file_path (str): Path to the DOCX file
            
        Returns:
            str: Document text with hyperlinks formatted as text(url)
        """
        doc = Document(file_path)
        processed_paragraphs = []
        for paragraph in doc.paragraphs:
            text = paragraph.text
            for hyperlink in paragraph.hyperlinks:
                link_text = hyperlink.text
                url = hyperlink.url
                if link_text in text:
                    start = text.find(link_text)
                    if start >= 0:
                        before = text[:start]
                        after = text[start + len(link_text):]
                        text = before + f"{link_text}({url})" + after
                else:
                    text = text + f"{link_text}({url})"
            processed_paragraphs.append(text)
                
        return "\n".join(processed_paragraphs)

    def parse_document_with_openai(self, file_path: str) -> str:
        parsed_text = self.parse_document(file_path)
        prompt = (f"Parse the following DOCX document and return only the requested JSON structure with relevant URLs and data. "
                  f"If a field is not found, use null instead of leaving it empty.\n\n{parsed_text}")
        return self.chat(prompt)
