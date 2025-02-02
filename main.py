from fastapi import FastAPI, Query, HTTPException
from utils import get_ticker_decision
from connectors.mongodb import MongoDBConnector, TokenAnalysis
import os
from typing import List
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017/")
    mongodb_user = os.getenv("MONGODB_USER")
    mongodb_password = os.getenv("MONGODB_PASSWORD")
    
    if mongodb_user and mongodb_password:
        mongodb_url = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_url.split('://')[1]}"
    
    await MongoDBConnector.connect(mongodb_url)
    yield
    await MongoDBConnector.close()

app = FastAPI(lifespan=lifespan)

@app.get("/token-analyses")
async def get_token_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    skip = (page - 1) * per_page
    total_count = await MongoDBConnector.get_total_count()
    analyses = await MongoDBConnector.get_analyses(skip=skip, limit=per_page)
    
    # Convert MongoDB documents to dict and handle ObjectId serialization
    serialized_analyses = []
    for analysis in analyses:
        analysis['_id'] = str(analysis['_id'])  # Convert ObjectId to string
        serialized_analyses.append(analysis)
    
    return {
        "status": "success",
        "data": serialized_analyses,
        "pagination": {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page
        }
    }

@app.get("/token-analysis/{chain}/{token_address}")
async def get_token_analysis(chain: str, token_address: str):
    analysis = await MongoDBConnector.get_by_address_and_chain(token_address, chain)
    if not analysis:
        raise HTTPException(status_code=404, detail="Token analysis not found")
    
    # Convert ObjectId to string before returning
    analysis['_id'] = str(analysis['_id'])
    
    return {"status": "success", "data": analysis}

@app.get("/token-decision/{chain}/{token_address}")
async def get_decision(chain: str, token_address: str):
    try:
        decision = get_ticker_decision(token_address=token_address, chain=chain)
        decision_lines = decision.split("\n")
        parsed_decision = {}
        for line in decision_lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.split(". ", 1)[1] if ". " in key else key
                parsed_decision[key] = value

        # Create analysis object
        analysis = TokenAnalysis(
            token_name=parsed_decision.get("Token name", "").strip(),
            token_symbol=parsed_decision.get("Token symbol", "").strip("$").strip(),
            token_address=token_address.strip(),
            token_chain=chain.strip(),
            current_price=parsed_decision.get("Current price", "").strip(),
            current_holders_count=parsed_decision.get("Current holders count", "").strip(),
            technical_analysis=parsed_decision.get("Brief technical side analysis", "").strip(),
            community_analysis=parsed_decision.get("Brief community side analysis", "").strip(),
            final_decision=parsed_decision.get("Final decision", "").strip(),
            explanation=parsed_decision.get("Explanation", "").strip()
        )
        
        existing_analysis = await MongoDBConnector.get_by_address_and_chain(token_address, chain)
        if existing_analysis:
            await MongoDBConnector.update_analysis(token_address, chain, analysis)
        else:
            await MongoDBConnector.add_analysis(analysis)
        
        return {"status": "success", "data": analysis}
    except Exception as e:
        return {"status": "error", "message": str(e)}
