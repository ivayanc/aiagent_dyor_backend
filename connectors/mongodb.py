from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List
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

class MongoDBConnector:
    client: Optional[AsyncIOMotorClient] = None
    db_name: str = "token_analysis_db"
    collection_name: str = "token_analyses"

    @classmethod
    async def connect(cls, mongodb_url: str):
        cls.client = AsyncIOMotorClient(mongodb_url)
        cls.db = cls.client[cls.db_name]

    @classmethod
    async def close(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    async def update_analysis(cls, token_address: str, chain: str, analysis: TokenAnalysis) -> None:
        """
        Update an existing analysis document in MongoDB.
        If no document exists, it will be created.
        """
        update_data = analysis.dict()
        update_data['updated_at'] = datetime.utcnow()
        await cls.db[cls.collection_name].update_one(
            {"token_address": token_address, "token_chain": chain},
            {"$set": update_data},
            upsert=True
        )

    @classmethod
    async def add_analysis(cls, analysis: TokenAnalysis) -> None:
        """
        Add a new analysis document to MongoDB.
        This method is kept for backward compatibility.
        """
        await cls.update_analysis(
            analysis.token_address,
            analysis.token_chain,
            analysis
        )

    @classmethod
    async def get_analyses(cls, skip: int = 0, limit: int = 10, sort: List = None):
        cursor = cls.db[cls.collection_name].find({})
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    @classmethod
    async def get_total_count(cls):
        return await cls.db[cls.collection_name].count_documents({})

    @classmethod
    async def get_by_address_and_chain(cls, token_address: str, chain: str):
        return await cls.db[cls.collection_name].find_one({
            "token_address": token_address,
            "token_chain": chain
        }) 