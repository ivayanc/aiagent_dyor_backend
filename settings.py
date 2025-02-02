from os import getenv

from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = getenv("GROK_API_KEY")
OPENAI_API_KEY = getenv("OPENAI_API_KEY")
MORALIS_API_KEY = getenv("MORALIS_API_KEY")
BITQUERY_API_KEY = getenv("BITQUERY_API_KEY")
