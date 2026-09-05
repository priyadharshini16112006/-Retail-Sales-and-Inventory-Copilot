from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..reasoning.metrics import calculate_metrics
from ..reasoning.alert_engine import generate_alerts
from ..reasoning.recommendation_engine import get_recommendation_for_alert
from ..llm.gemini_client import ask_gemini
from ..llm.prompts import COPILOT_SYSTEM_PROMPT

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    store_id: Optional[int] = None

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    msg = request.message.lower()
    
    # Deterministic intent detection
    intent = "general"
    if "run out" in msg or "stockout" in msg or "reorder" in msg:
        intent = "stockout"
    elif "overstock" in msg or "too much" in msg:
        intent = "overstock"
    elif "top" in msg or "best" in msg or "selling" in msg:
        intent = "top_products"
    elif "spike" in msg or "increase" in msg or "jump" in msg:
        intent = "sales_spike"
    elif "drop" in msg or "decrease" in msg or "fall" in msg or "why did" in msg:
        intent = "sales_drop"
    elif "store" in msg:
        intent = "store"

    # Context retrieval based on intent
    context_data = {}
    
    metrics = calculate_metrics(db, request.store_id)
    
    if intent in ["stockout", "overstock", "sales_spike", "sales_drop", "general"]:
        alerts = generate_alerts(db, request.store_id)
        if intent == "stockout":
            alerts = [a for a in alerts if "Stockout" in a['type']]
        elif intent == "overstock":
            alerts = [a for a in alerts if a['type'] == "Overstock"]
        elif intent == "sales_spike":
            alerts = [a for a in alerts if a['type'] == "Sales Spike"]
        elif intent == "sales_drop":
            alerts = [a for a in alerts if a['type'] == "Sales Drop"]
        
        # Limit context to avoid huge payloads
        context_data["relevant_alerts"] = alerts[:10]
        
        # Also include products with high risk scores or critical reorder priority for stockout intent
        if intent == "stockout" or intent == "general":
            high_risk_products = [m for m in metrics if m.get('risk_score', 0) >= 60 or m.get('reorder_priority') in ["CRITICAL", "HIGH"]]
            context_data["high_risk_products"] = sorted(high_risk_products, key=lambda x: x.get('risk_score', 0), reverse=True)[:10]
        
    elif intent == "top_products":
        sorted_metrics = sorted(metrics, key=lambda x: x['total_30d_sales'], reverse=True)
        context_data["top_products"] = sorted_metrics[:10]

    # Call LLM with the deterministic context
    response = ask_gemini(COPILOT_SYSTEM_PROMPT, request.message, context_data)
    
    return response
