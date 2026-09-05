from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from ..database import get_db, Product, Sale, Inventory, Store

router = APIRouter()

# --- Pydantic Schemas ---

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    store_id: int
    price: float = Field(..., ge=0)
    current_stock: int = Field(..., ge=0)
    reorder_level: int = Field(..., ge=0)
    supplier: str = "Manual Entry"
    cost: float = 0.0
    description: str = ""

class SaleCreate(BaseModel):
    product_id: int
    store_id: int
    date: date
    units_sold: int = Field(..., gt=0)
    revenue: float = Field(..., ge=0)

class InventoryUpdate(BaseModel):
    product_id: int
    store_id: int
    quantity: int = Field(..., ge=0)
    reorder_level: int = Field(..., ge=0)

# --- Endpoints ---

@router.post("/products")
def create_product(prod_data: ProductCreate, db: Session = Depends(get_db)):
    # 1. Create the product
    new_product = Product(
        name=prod_data.name,
        category=prod_data.category,
        price=prod_data.price,
        cost=prod_data.cost,
        description=prod_data.description,
        supplier=prod_data.supplier
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # 2. Create the initial inventory record for the specified store
    new_inventory = Inventory(
        product_id=new_product.id,
        store_id=prod_data.store_id,
        quantity=prod_data.current_stock,
        reorder_level=prod_data.reorder_level,
        last_updated=datetime.utcnow()
    )
    db.add(new_inventory)
    db.commit()

    return {"message": "Product created successfully", "product_id": new_product.id}


@router.post("/sales")
def create_sale(sale_data: SaleCreate, db: Session = Depends(get_db)):
    # Verify product and store exist
    if not db.query(Product).filter(Product.id == sale_data.product_id).first():
        raise HTTPException(status_code=404, detail="Product not found")
    if not db.query(Store).filter(Store.id == sale_data.store_id).first():
        raise HTTPException(status_code=404, detail="Store not found")

    new_sale = Sale(
        date=sale_data.date,
        product_id=sale_data.product_id,
        store_id=sale_data.store_id,
        units_sold=sale_data.units_sold,
        revenue=sale_data.revenue
    )
    db.add(new_sale)
    
    # Also deduct from inventory if we are making a sale (simple logic for now)
    inv = db.query(Inventory).filter(
        Inventory.product_id == sale_data.product_id,
        Inventory.store_id == sale_data.store_id
    ).first()
    
    if inv:
        inv.quantity = max(0, inv.quantity - sale_data.units_sold)
        inv.last_updated = datetime.utcnow()

    db.commit()
    return {"message": "Sale record added successfully"}


@router.post("/inventory")
def update_inventory(inv_data: InventoryUpdate, db: Session = Depends(get_db)):
    if not db.query(Product).filter(Product.id == inv_data.product_id).first():
        raise HTTPException(status_code=404, detail="Product not found")
    if not db.query(Store).filter(Store.id == inv_data.store_id).first():
        raise HTTPException(status_code=404, detail="Store not found")

    inv = db.query(Inventory).filter(
        Inventory.product_id == inv_data.product_id,
        Inventory.store_id == inv_data.store_id
    ).first()

    if inv:
        inv.quantity = inv_data.quantity
        inv.reorder_level = inv_data.reorder_level
        inv.last_updated = datetime.utcnow()
    else:
        inv = Inventory(
            product_id=inv_data.product_id,
            store_id=inv_data.store_id,
            quantity=inv_data.quantity,
            reorder_level=inv_data.reorder_level,
            last_updated=datetime.utcnow()
        )
        db.add(inv)

    db.commit()
    return {"message": "Inventory updated successfully"}

# Also provide an endpoint to list products for the dropdowns
@router.get("/products/list")
def get_products_list(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [{"id": p.id, "name": p.name} for p in products]
