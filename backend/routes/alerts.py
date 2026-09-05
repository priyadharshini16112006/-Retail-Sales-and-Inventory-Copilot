from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..reasoning.alert_engine import generate_alerts

router = APIRouter()

@router.get("/alerts")
def get_alerts(store_id: int = None, db: Session = Depends(get_db)):
    alerts = generate_alerts(db, store_id)
    return alerts
