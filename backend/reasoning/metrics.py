from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..database import Inventory, Sale, Product, Store

def calculate_metrics(db: Session, store_id: int = None):
    # Base queries
    inv_query = db.query(Inventory, Product, Store).join(Product).join(Store)
    sales_query = db.query(Sale)
    
    if store_id:
        inv_query = inv_query.filter(Inventory.store_id == store_id)
        sales_query = sales_query.filter(Sale.store_id == store_id)

    inventory_items = inv_query.all()
    
    # Calculate 30-day sales for each product-store combo
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    
    metrics = []
    
    for inv, prod, store in inventory_items:
        # Sum units sold in last 30 days
        recent_sales_query = db.query(func.sum(Sale.units_sold)).filter(
            Sale.product_id == inv.product_id,
            Sale.store_id == inv.store_id,
            Sale.date >= thirty_days_ago
        )
        total_30d_sales = recent_sales_query.scalar() or 0
        
        # Also get previous 30 days for anomaly detection
        sixty_days_ago = thirty_days_ago - timedelta(days=30)
        prev_sales_query = db.query(func.sum(Sale.units_sold)).filter(
            Sale.product_id == inv.product_id,
            Sale.store_id == inv.store_id,
            Sale.date >= sixty_days_ago,
            Sale.date < thirty_days_ago
        )
        total_prev_30d_sales = prev_sales_query.scalar() or 0

        avg_daily_sales = total_30d_sales / 30.0
        prev_avg_daily_sales = total_prev_30d_sales / 30.0

        days_remaining = (inv.quantity / avg_daily_sales) if avg_daily_sales > 0 else float('inf')
        
        # --- Smart Reorder Logic ---
        if avg_daily_sales > 0:
            target_stock = avg_daily_sales * 14
            recommended_reorder = max(target_stock - inv.quantity, 0)
            recommended_reorder = round(recommended_reorder)
        else:
            recommended_reorder = 0

        reorder_priority = "LOW"
        if days_remaining <= 2:
            reorder_priority = "CRITICAL"
        elif days_remaining <= 5:
            reorder_priority = "HIGH"
        elif days_remaining <= 10:
            reorder_priority = "MEDIUM"

        # --- Inventory Risk Score Logic ---
        risk_score = 0
        
        if days_remaining <= 2:
            risk_score += 40
        elif days_remaining <= 5:
            risk_score += 30
        elif days_remaining <= 10:
            risk_score += 15
        elif days_remaining != float('inf'):
            risk_score += 5
            
        if inv.quantity < inv.reorder_level:
            risk_score += 30
            
        # Recent sales increase (e.g. over 20% growth)
        if prev_avg_daily_sales > 0 and (avg_daily_sales - prev_avg_daily_sales) / prev_avg_daily_sales > 0.2:
            risk_score += 20
            
        risk_score = min(risk_score, 100)
        
        risk_category = "Low"
        if risk_score >= 80:
            risk_category = "Critical"
        elif risk_score >= 60:
            risk_category = "High"
        elif risk_score >= 30:
            risk_category = "Medium"

        metrics.append({
            "product_id": prod.id,
            "product_name": prod.name,
            "store_id": store.id,
            "store_name": store.name,
            "current_stock": inv.quantity,
            "reorder_level": inv.reorder_level,
            "total_30d_sales": total_30d_sales,
            "avg_daily_sales": round(avg_daily_sales, 2),
            "prev_avg_daily_sales": round(prev_avg_daily_sales, 2),
            "days_remaining": round(days_remaining, 1) if days_remaining != float('inf') else 999.0,
            "recommended_reorder": recommended_reorder,
            "reorder_priority": reorder_priority,
            "risk_score": risk_score,
            "risk_category": risk_category
        })
        
    return metrics
