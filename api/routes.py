from fastapi import APIRouter, UploadFile, File
from fastapi import FastAPI, Query, HTTPException, File, UploadFile
from utils.utils import get_ticker_decision, parse_dyor_report, update_dyor_report, chat_with_agent
from connectors.mongodb import MongoDBConnector,TokenAnalysis, DatabaseManager, Token, TokenResearchInput
from typing import List
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime
from utils.storage import LocalStorage
from connectors.mongodb import Attachment, DatabaseManager
import os
from typing import Optional

router = APIRouter()

storage = LocalStorage()
db_manager = DatabaseManager()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save file to local storage
    file_path = storage.save_file(file, file.filename)
    
    # Create attachment record
    attachment = Attachment(
        filename=file.filename,
        file_path=file_path,
        content_type=file.content_type,
        size=os.path.getsize(file_path)
    )
    
    # Save attachment metadata to MongoDB
    attachment_id = await db_manager.save_attachment(attachment)
    
    return {
        "success": True,
        "attachment_id": attachment_id,
        "filename": file.filename
    } 

@router.get("/token-analyses")
async def get_token_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    token: str = Query(None, description="Token address to filter by")
):
    skip = (page - 1) * per_page
    db_manager  = DatabaseManager()
    total_count = await db_manager.get_total_count("analysis")
    analyses = await db_manager.get_researches(
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
@router.get("/token/{chain}/{token_address}")
async def get_token(chain: str, token_address: str, include_research: bool = True):
    db_manager = DatabaseManager()
    analysis = await db_manager.get_token(token_address=token_address, chain=chain, include_research=include_research)
    if not analysis:
        raise HTTPException(status_code=404, detail="Token analysis not found")
    return {"status": "success", "data": analysis}


@router.get("/token-analysis/{chain}/{token_address}")
async def get_token_analysis(chain: str, token_address: str):
    db_manager = DatabaseManager()
    analysis = await db_manager.get_researches(token_address=token_address, chain=chain)
    if not analysis:
        raise HTTPException(status_code=404, detail="Token analysis not found")
    
    # Convert ObjectId to string before returning
    analysis['_id'] = str(analysis['_id'])
    
    return {"status": "success", "data": analysis}

@router.get("/token-decision/{chain}/{token_address}")
async def get_decision(chain: str, token_address: str):
    try:
        db_manager = DatabaseManager()
        
        # Get existing analysis first
        existing_analysis = await db_manager.get_researches(token_address=token_address, chain=chain)
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

@router.post("/analyze-dyor")
async def analyze_dyor(file: UploadFile = File(...)):
    try:
        #Verify file extension
        if not file.filename.endswith('.docx'):
            return {"status": "error", "message": "Invalid file format. Please upload a .docx file"}

        # Save uploaded file temporarily
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        result = await parse_dyor_report(temp_file_path)
        # Clean up temp file
        os.remove(temp_file_path)
        
        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/token-by-name/{token_name}")
async def get_token_by_name(token_name: str,
    chain: str = Query(None, description="Chain to filter by"),
    include_researches: bool = Query(True, description="Include research in response")
):
    db_manager = DatabaseManager()
    token = await db_manager.get_token_by_name(token_name=token_name, chain=chain)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "success", "data": Token(**token)}

@router.get("/tokens")
async def get_tokens(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    token_name: str = Query(None, description="Token name to filter by")
):
    skip = (page - 1) * per_page
    db_manager = DatabaseManager()
    total_count = await db_manager.get_total_count("tokens")
    
    analyses = await db_manager.get_tokens(
        skip=skip, 
        limit=per_page,
        include_research=True
    )
    
    # Convert MongoDB documents to dict and handle ObjectId serialization
    serialized_analyses = []
    for analysis in analyses:
        analysis['_id'] = str(analysis['_id'])
        
        # Extract the latest research input data if available
        if analysis.get('research_inputs') and len(analysis['research_inputs']) > 0:
            latest_input = analysis['research_inputs'][0]
            analysis['latest_data'] = latest_input.get('data', {})
        else:
            analysis['latest_data'] = {}
            
        # Extract the latest research if available
        if analysis.get('researches') and len(analysis['researches']) > 0:
            analysis['latest_research'] = analysis['researches'][0]
        else:
            analysis['latest_research'] = {}
            
        # Remove the full lists since we only need the latest entries
        analysis.pop('research_inputs', None)
        analysis.pop('researches', None)
        
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

@router.get("/update-report-by-name/{token_name}")
async def update_report_by_name(
    token_name: str,
    chain: str = Query(None, description="Chain to filter by")
):
    try:
        db_manager = DatabaseManager()
        
        # Get token and research inputs
        token_data = await db_manager.get_token_by_name(token_name=token_name, chain=chain)
        if not token_data:
            raise HTTPException(status_code=404, detail="Token not found")
            
        # Convert to Token model
        token = Token(**token_data)
        # Check if there are any research inputs
        if not token.research_inputs or len(token.research_inputs) == 0:
            raise HTTPException(status_code=404, detail="No research input data found for this token")
        
        # Get the latest research input and convert to TokenResearchInput model
        if token.ai_reports and len(token.ai_reports) > 0:
            last_ai_report = token.ai_reports[-1].get('data', None)
        else:
            last_ai_report = None
            
        data = await update_dyor_report(dyor_report=token.research_inputs[-1].get('data'), 
                                      token_address=token.token_address, 
                                      token_chain=token.token_chain, 
                                      last_ai_report=last_ai_report)
        
        # Update last_research_time
        tokens_coll = await MongoDBConnector.get_collection("tokens")
        await tokens_coll.update_one(
            {"_id": token_data["_id"]},
            {"$set": {"last_research_time": datetime.utcnow()}}
        )
        
        return {
            "status": "success", 
            "data": data
        }
        
    except HTTPException as he:
        raise he


from pydantic import BaseModel
class MessageModel(BaseModel):
    message: str
    attachment_ids: Optional[List[str]] = None
@router.post("/chat")
async def chat(message: MessageModel):
    response = await chat_with_agent(message.message, message.attachment_ids)
    return response