
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class TokenAnalysis(BaseModel):
    token_name: str
    token_symbol: str
    token_address: str
    token_chain: str
    current_price: str
    current_holders_count: str
    technical_analysis: str
    community_analysis: str
    final_decision: str
    final_confident_level: str
    explanation: str
    price_change: Optional[str] = None
    holder_change: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

class TokenResearchInput(BaseModel):
    token_name: str
    token_address: Optional[str] = None
    token_chain: Optional[str] = None
    last_research_time: datetime = datetime.utcnow()
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class Token(BaseModel):
    token_name: str
    token_address: Optional[str] = None
    token_chain: Optional[str] = None
    last_research_time: datetime = datetime.utcnow()
    metadata: Optional[Dict[str, Any]] = None
    researches: Optional[List[Any]] = None
    research_inputs: Optional[List[Any]] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    
    

class MongoDBConnector:
    client: Optional[AsyncIOMotorClient] = None
    db_name: str = "DYOR"

    @classmethod
    async def connect(cls, mongodb_url: str):
        cls.client = AsyncIOMotorClient(mongodb_url)
        cls.db = cls.client[cls.db_name]

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    async def get_collection(cls, collection_name: str):
        return cls.db[collection_name]

class DatabaseManager:
    def __init__(self):
        self.tokens_collection = "tokens"
        self.research_collection = "analysis"
        self.research_input_collection = "research_input"
        
    async def ensure_indexes(self):
        indexes = {
            self.tokens_collection: [
                ('address', 1),
                ('chain', 1), 
                ('last_research_time', -1)
            ],
            self.research_collection: [
                ('token_name', 1),
                ('token_address', 1),
                ('token_chain', 1),
                ('created_at', -1)
            ],
            self.research_input_collection: [
                ('token_name', 1),
                ('token_address', 1),
                ('token_chain', 1),
                ('created_at', -1)
            ]
        }
        for coll_name, coll_indexes in indexes.items():
            coll = await MongoDBConnector.get_collection(coll_name)
            for idx in coll_indexes:
                await coll.create_index([idx])

    async def get_total_count(self, collection_name: str) -> int:
        coll = await MongoDBConnector.get_collection(collection_name)
        return await coll.count_documents({})

    async def save_token(self, token: Token) -> None:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        await coll.insert_one(token.dict())

    async def _include_researches(self, token: dict, token_name: str) -> dict:
        if not token:
            return None
        token["researches"] = await self.get_researches(token_name=token_name)
        return token

    async def _include_research_input(self, token: dict, token_name: str) -> dict:
        if not token:
            return None        
        token["research_inputs"] = await self.get_research_inputs(token_name=token_name)
        for research_input in token["research_inputs"]:
            research_input["_id"] = str(research_input["_id"])
        return token
    
    async def get_token(self, token_address: str, chain: str, include_research: bool = False) -> Optional[Token]:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        token = await coll.find_one({"token_address": token_address, "chain": chain})
        if include_research:
            token = await self._include_researches(token, token["token_name"])
            token = await self._include_research_input(token, token["token_name"])
        return token

    async def get_token_by_name(self, token_name: str, chain: str = None, include_research: bool = True) -> Optional[Token]:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        token = await coll.find_one({"token_name": token_name, "chain": chain})
        if include_research:
            token = await self._include_researches(token, token_name)
            token = await self._include_research_input(token, token_name)
        return token

    async def save_research(self, research: TokenAnalysis) -> None:
        coll = await MongoDBConnector.get_collection(self.research_collection)
        await coll.insert_one(research.dict())
        await self._update_token_research_time(research.token_address, research.token_chain)
    
    async def _update_token_research_time(self, token_address: str, chain: str) -> None:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        await coll.update_one(
            {"token_name": research_input.token_name},
            {
                "$set": {
                    "token_name": research_input.token_name,
                    "token_address": token_address,
                    "token_chain": chain,
                    "last_research_time": datetime.utcnow()
                }
            },
            upsert=True
        )

    async def get_researches(
        self,
        token_name: Optional[str] = None,
        token_address: Optional[str] = None,
        chain: Optional[str] = None,    
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        coll = await MongoDBConnector.get_collection(self.research_collection)
        
        query = {}
        if token_name:
            query["token_name"] = token_name
        if token_address:
            query["token_address"] = token_address
        if chain:
            query["token_chain"] = chain
        if start_date or end_date:
            query["research_time"] = {}
            if start_date:
                query["research_time"]["$gte"] = start_date
            if end_date:
                query["research_time"]["$lte"] = end_date

        return await coll.find(query).sort("research_time", -1).skip(skip).limit(limit).to_list(limit)

    async def get_research_inputs(
        self,
        token_name: Optional[str] = None,
        token_address: Optional[str] = None,
        chain: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        coll = await MongoDBConnector.get_collection(self.research_input_collection)
        
        query = {}
        if token_name:
            query["token_name"] = token_name
        if token_address:
            query["token_address"] = token_address 
        if chain:
            query["token_chain"] = chain
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date

        return await coll.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    async def save_research_input(self, research_input: TokenResearchInput) -> None:
        coll = await MongoDBConnector.get_collection(self.research_input_collection)
        await coll.insert_one(research_input.dict())

        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        await coll.update_one(
            {"token_name": research_input.token_name},
            {
                "$set": {
                    "token_name": research_input.token_name,
                    "token_address": research_input.token_address,
                    "token_chain": research_input.token_chain,
                }
            },
            upsert=True
        )
