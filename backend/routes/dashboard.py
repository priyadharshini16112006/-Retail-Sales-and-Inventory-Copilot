from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db, Sale, Product
from ..reasoning.metrics import calculate_metrics
from ..reasoning.alert_engine import generate_alerts

router = APIRouter()

@router.get("/dashboard")
def get_dashboard(store_id: int = None, db: Session = Depends(get_db)):
    # Calculate global metrics
    sales_query = db.query(func.sum(Sale.revenue).label('total_revenue'), func.sum(Sale.units_sold).label('total_units'))
    
    if store_id:
        sales_query = sales_query.filter(Sale.store_id == store_id)
        
    sales_totals = sales_query.first()
    
    total_revenue = sales_totals.total_revenue or 0
    total_units = sales_totals.total_units or 0
    
    # Calculate detailed metrics
    metrics = calculate_metrics(db, store_id)
    
    total_products = len(metrics)
    
    alerts = generate_alerts(db, store_id)
    
    stockout_risks = len([a for a in alerts if a['type'] in ["Critical Stockout", "Stockout Risk"]])
    overstock_count = len([a for a in alerts if a['type'] == "Overstock"])
    sales_spikes = len([a for a in alerts if a['type'] == "Sales Spike"])
    sales_drops = len([a for a in alerts if a['type'] == "Sales Drop"])
    
    # Top products by sales in last 30 days
    sorted_metrics = sorted(metrics, key=lambda x: x['total_30d_sales'], reverse=True)
    top_products = sorted_metrics[:5]
    
    # Smart Reorder & Risk Score Aggregation
    smart_reorder_count = len([m for m in metrics if m.get('reorder_priority') in ["CRITICAL", "HIGH"]])
    avg_risk_score = sum(m.get('risk_score', 0) for m in metrics) / total_products if total_products > 0 else 0
    
    return {
        "total_revenue": total_revenue,
        "units_sold": total_units,
        "total_products": total_products,
        "stockout_risks": stockout_risks,
        "overstock_count": overstock_count,
        "sales_spikes": sales_spikes,
        "sales_drops": sales_drops,
        "smart_reorder_count": smart_reorder_count,
        "avg_risk_score": round(avg_risk_score, 1),
        "top_products": top_products,
        "priority_alerts": alerts[:10]
    }

@router.get("/sales/trend")
def get_sales_trend(store_id: int = None, product_id: int = None, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    sixty_days_ago = thirty_days_ago - timedelta(days=30)
    
    query = db.query(Sale.date, func.sum(Sale.revenue).label('revenue'), func.sum(Sale.units_sold).label('units'))
    
    if store_id:
        query = query.filter(Sale.store_id == store_id)
    if product_id:
        query = query.filter(Sale.product_id == product_id)
        
    trend_data = query.filter(Sale.date >= sixty_days_ago).group_by(Sale.date).order_by(Sale.date).all()
    
    result = []
    current_period_revenue = 0
    prev_period_revenue = 0
    
    for row in trend_data:
        date_str = row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date)
        result.append({
            "date": date_str,
            "revenue": row.revenue,
            "units": row.units
        })
        
        if row.date >= thirty_days_ago:
            current_period_revenue += row.revenue
        else:
            prev_period_revenue += row.revenue
            
    pct_change = 0
    if prev_period_revenue > 0:
        pct_change = ((current_period_revenue - prev_period_revenue) / prev_period_revenue) * 100
        
    return {
        "trend": result,
        "current_period_revenue": current_period_revenue,
        "prev_period_revenue": prev_period_revenue,
        "pct_change": round(pct_change, 1)
    }
