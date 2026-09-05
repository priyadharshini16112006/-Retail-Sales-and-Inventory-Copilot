from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db, Store

router = APIRouter()

@router.get("/stores")
def get_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).all()
    return [{"id": s.id, "name": s.name, "city": s.city} for s in stores]
