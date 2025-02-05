
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

class Token(BaseModel):
    token_name: str
    token_address: str
    token_chain: str
    last_research_time: datetime = datetime.utcnow()
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

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

class BaseTokenRepository:
    def __init__(self):
        self.tokens_collection = "tokens"
        self.research_collection = "analysis"
        
    async def ensure_indexes(self):
        indexes = {
            self.tokens_collection: [
                ('address', 1),
                ('chain', 1), 
                ('last_research_time', -1)
            ],
            self.research_collection: [
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

class TokenRepository(BaseTokenRepository):
    async def save_token(self, token: Token) -> None:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        await coll.insert_one(token.dict())

    async def get_token(self, token_address: str, chain: str, include_research: bool = False) -> Optional[Token]:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        token = await coll.find_one({"token_address": token_address, "chain": chain})
        if not token:
            return None
        if include_research:
            token["researches"] = await self.get_researches(token_address=token_address, chain=chain)
        return token


class ResearchRepository(BaseTokenRepository):
    async def save_research(self, research: TokenAnalysis) -> None:
        coll = await MongoDBConnector.get_collection(self.research_collection)
        await coll.insert_one(research.dict())
        await self._update_token_research_time(research.token_address, research.token_chain)
    
    async def _update_token_research_time(self, token_address: str, chain: str) -> None:
        coll = await MongoDBConnector.get_collection(self.tokens_collection)
        await coll.update_one(
            {"token_address": token_address},
            {
                "$set": {
                    "token_address": token_address,
                    "token_chain": chain,
                    "last_research_time": datetime.utcnow()
                }
            },
            upsert=True
        )
    async def get_researches(
        self,
        token_address: Optional[str] = None,
        chain: Optional[str] = None,    
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        coll = await MongoDBConnector.get_collection(self.research_collection)
        
        query = {}
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
