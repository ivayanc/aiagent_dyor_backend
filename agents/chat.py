from typing import Dict, Any, Optional
from .openai import OpenAI

class ChatAgent(OpenAI):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.chat_history = []
        self.default_lore = """
        You are an AI assistant specialized in cryptocurrency research and analysis.
        You can help users understand crypto projects, analyze market data, and provide 
        insights based on available information. If a user requests detailed research
        about a specific token, you should suggest using the DYOR (Do Your Own Research) agent.
        """

    async def chat_response(self, user_message: str, lore: Optional[str] = None) -> Dict[str, Any]:
        """
        Process user message and generate appropriate response
        """
        # Add user message to chat history
        self.chat_history.append({"role": "user", "content": user_message})
        
        # Use custom lore if provided, otherwise use default
        chat_lore = lore if lore else self.default_lore
        
        # Check if message contains DYOR request
        if self._is_dyor_request(user_message):
            response = self._suggest_dyor_agent(user_message)
        else:
            response = self.chat(user_message, chat_lore)
        
        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        
        return {
            "success": True,
            "response": response,
            "requires_dyor": self._is_dyor_request(user_message)
        }

    def _is_dyor_request(self, message: str) -> bool:
        """
        Check if user message indicates need for detailed token research
        """
        keywords = ["research", "analyze token", "dyor", "token analysis", 
                   "investigate project", "token research"]
        return any(keyword in message.lower() for keyword in keywords)

    def _suggest_dyor_agent(self, message: str) -> str:
        """
        Generate response suggesting use of DYOR agent
        """
        return ("I notice you're interested in detailed token research. "
                "I recommend using our specialized DYOR agent for in-depth analysis. "
                "Would you like me to initiate a DYOR report for this token?")

    def clear_history(self) -> None:
        """
        Clear chat history
        """
        self.chat_history = []
