from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..reasoning.metrics import calculate_metrics

router = APIRouter()

@router.get("/inventory")
def get_inventory(store_id: int = None, db: Session = Depends(get_db)):
    metrics = calculate_metrics(db, store_id)
    return metrics
