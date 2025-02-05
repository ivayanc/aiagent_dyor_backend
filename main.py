from fastapi import FastAPI, Query, HTTPException, File, UploadFile
from utils import get_ticker_decision, parse_dyor_report
from connectors.mongodb import MongoDBConnector,TokenAnalysis, TokenRepository, ResearchRepository
from typing import List
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import docx
import os
from datetime import datetime

from settings import MONGODB_URL, ALLOWED_ORIGINS

@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDBConnector.connect(MONGODB_URL)
    yield
    await MongoDBConnector.close()

app = FastAPI(lifespan=lifespan)

# Add this after creating the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/token-analyses")
async def get_token_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    token: str = Query(None, description="Token address to filter by")
):
    skip = (page - 1) * per_page
    research_repo = ResearchRepository()
    total_count = await research_repo.get_total_count("analysis")
    analyses = await research_repo.get_researches(
        token_address=token,
        skip=skip, 
        limit=per_page
    )
    
    # Convert MongoDB documents to dict and handle ObjectId serialization
    serialized_analyses = []
    for analysis in analyses:
        analysis['_id'] = str(analysis['_id'])  # Convert ObjectId to string
        # Convert price string to float and format using scientific notation
        price = float(analysis['current_price'][1:].replace(",", ""))
        analysis['current_price'] = f'${price:.2e}' if price < 0.01 else f'${price:.5f}'
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
@app.get("/token/{chain}/{token_address}")
async def get_token(chain: str, token_address: str, include_research: bool = True):
    token_repo = TokenRepository()
    analysis = await token_repo.get_token(token_address=token_address, chain=chain, include_research=include_research)
    if not analysis:
        raise HTTPException(status_code=404, detail="Token analysis not found")
    return {"status": "success", "data": analysis}


@app.get("/token-analysis/{chain}/{token_address}")
async def get_token_analysis(chain: str, token_address: str):
    research_repo = ResearchRepository()
    analysis = await research_repo.get_researches(token_address=token_address, chain=chain)
    if not analysis:
        raise HTTPException(status_code=404, detail="Token analysis not found")
    
    # Convert ObjectId to string before returning
    analysis['_id'] = str(analysis['_id'])
    
    return {"status": "success", "data": analysis}

@app.get("/token-decision/{chain}/{token_address}")
async def get_decision(chain: str, token_address: str):
    try:
        research_repo = ResearchRepository()
        token_repo = TokenRepository()
        
        # Get existing analysis first
        existing_analysis = await research_repo.get_researches(token_address=token_address, chain=chain)
        if existing_analysis:
            existing_analysis = existing_analysis[0]  # Get first analysis since it's sorted by latest
        
        # Get new decision
        decision = get_ticker_decision(token_address=token_address, chain=chain)
        decision_lines = decision.split("\n")
        parsed_decision = {}
        for line in decision_lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.split(". ", 1)[1] if ". " in key else key
                parsed_decision[key] = value

        # Calculate price and holder changes if previous analysis exists
        price_change = None
        holder_change = None
        if existing_analysis:
            try:
                # Extract numeric values from price strings
                current_price_str = parsed_decision.get("Current price", "").strip().replace("$", "")
                previous_price_str = existing_analysis["current_price"].replace("$", "")
                
                if current_price_str and previous_price_str:
                    current_price = float(current_price_str)
                    previous_price = float(previous_price_str)
                    price_diff = ((current_price - previous_price) / previous_price) * 100
                    price_change = f"{price_diff:+.2f}%"

                # Extract numeric values from holder counts
                current_holders = int(parsed_decision.get("Current holders count", "").strip().replace(",", ""))
                previous_holders = int(existing_analysis["current_holders_count"].replace(",", ""))
                holder_diff = current_holders - previous_holders
                holder_change = f"{holder_diff:+,d}"
            except (ValueError, TypeError):
                # If there's any error in conversion, keep the changes as None
                pass

        # Create analysis object with the new fields
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
            explanation=parsed_decision.get("Explanation", "").strip(),
            final_confident_level=parsed_decision.get("Final confident level", "").strip(),
            price_change=price_change,
            holder_change=holder_change
        )
        
        await research_repo.save_research(analysis)
        
        return {"status": "success", "data": analysis}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/analyze-dyor")
async def analyze_dyor(file: UploadFile = File(...)):
    try:
        # Verify file extension
        if not file.filename.endswith('.docx'):
            return {"status": "error", "message": "Invalid file format. Please upload a .docx file"}

        # Save uploaded file temporarily
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        result = parse_dyor_report(temp_file_path)
        # Clean up temp file
        os.remove(temp_file_path)
        
        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}