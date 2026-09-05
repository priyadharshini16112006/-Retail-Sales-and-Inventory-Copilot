from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..database import get_db, Product, Inventory, Sale, Store

router = APIRouter()

# Map of scenario slug -> product name
SCENARIO_MAP = {
    "wireless-mouse":    {"product": "Wireless Mouse",    "type": "stockout"},
    "premium-detergent": {"product": "Premium Detergent", "type": "overstock"},
    "chocolate-box":     {"product": "Chocolate Box",     "type": "spike"},
    "coffee-pack":       {"product": "Coffee Pack",       "type": "drop"},
}

@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, db: Session = Depends(get_db)):
    if scenario_id not in SCENARIO_MAP:
        raise HTTPException(status_code=404, detail="Scenario not found")

    cfg = SCENARIO_MAP[scenario_id]
    product_name = cfg["product"]
    scenario_type = cfg["type"]

    # Look up product
    product = db.query(Product).filter(Product.name == product_name).first()
    if not product:
        return {"error": f"Product '{product_name}' not found in database", "scenario_id": scenario_id}

    thirty_days_ago   = datetime.now().date() - timedelta(days=30)
    sixty_days_ago    = thirty_days_ago - timedelta(days=30)
    ten_days_ago      = datetime.now().date() - timedelta(days=10)

    # Per-store breakdown
    stores = db.query(Store).all()
    store_records = []

    for store in stores:
        inv = db.query(Inventory).filter(
            Inventory.product_id == product.id,
            Inventory.store_id == store.id
        ).first()

        total_30d = db.query(func.sum(Sale.units_sold)).filter(
            Sale.product_id == product.id,
            Sale.store_id == store.id,
            Sale.date >= thirty_days_ago
        ).scalar() or 0

        total_prev_30d = db.query(func.sum(Sale.units_sold)).filter(
            Sale.product_id == product.id,
            Sale.store_id == store.id,
            Sale.date >= sixty_days_ago,
            Sale.date < thirty_days_ago
        ).scalar() or 0

        # Recent 10-day sales for spike/drop detection
        total_10d = db.query(func.sum(Sale.units_sold)).filter(
            Sale.product_id == product.id,
            Sale.store_id == store.id,
            Sale.date >= ten_days_ago
        ).scalar() or 0

        avg_daily     = total_30d / 30.0
        prev_avg      = total_prev_30d / 30.0
        avg_10d_daily = total_10d / 10.0
        current_stock = inv.quantity if inv else 0
        reorder_level = inv.reorder_level if inv else 0

        days_remaining = round(current_stock / avg_daily, 1) if avg_daily > 0 else 999.0

        # Compute change %
        if prev_avg > 0:
            change_pct = round(((avg_daily - prev_avg) / prev_avg) * 100, 1)
        else:
            change_pct = None

        store_records.append({
            "store_name":        store.name,
            "store_city":        store.city,
            "current_stock":     current_stock,
            "reorder_level":     reorder_level,
            "avg_daily_sales":   round(avg_daily, 2),
            "prev_avg_daily":    round(prev_avg, 2),
            "recent_10d_daily":  round(avg_10d_daily, 2),
            "total_30d_sales":   total_30d,
            "total_prev_30d":    total_prev_30d,
            "days_remaining":    days_remaining,
            "change_pct":        change_pct,
        })

    # Aggregate summary across all stores
    total_stock    = sum(r["current_stock"] for r in store_records)
    total_30d_all  = sum(r["total_30d_sales"] for r in store_records)
    avg_daily_all  = round(total_30d_all / 30.0, 2)
    total_prev_all = sum(r["total_prev_30d"] for r in store_records)
    prev_daily_all = round(total_prev_all / 30.0, 2)
    overall_days   = round(total_stock / avg_daily_all, 1) if avg_daily_all > 0 else 999.0

    # Deterministic recommendation based on scenario type
    recommendation = _build_recommendation(scenario_type, {
        "product_name":   product_name,
        "total_stock":    total_stock,
        "avg_daily":      avg_daily_all,
        "days_remaining": overall_days,
        "prev_daily":     prev_daily_all,
    })

    return {
        "scenario_id":   scenario_id,
        "scenario_type": scenario_type,
        "product_name":  product_name,
        "category":      product.category,
        "price":         product.price,
        "supplier":      product.supplier,
        "summary": {
            "total_stock":       total_stock,
            "avg_daily_sales":   avg_daily_all,
            "prev_avg_daily":    prev_daily_all,
            "days_remaining":    overall_days,
            "total_30d_sales":   total_30d_all,
        },
        "store_breakdown": store_records,
        "recommendation":  recommendation,
    }

def _build_recommendation(scenario_type: str, data: dict):
    name = data["product_name"]
    stock = data["total_stock"]
    avg = data["avg_daily"]
    days = data["days_remaining"]
    prev = data["prev_daily"]

    if scenario_type == "stockout":
        severity = "CRITICAL" if days <= 1 else "WARNING"
        return {
            "severity": severity,
            "action": f"Reorder {name} immediately.",
            "reason": f"Current stock ({stock} units) will last approximately {days} days at the current sales rate of {avg} units/day.",
            "evidence": [
                {"fact": "Current stock", "value": f"{stock} units", "source": "inventory"},
                {"fact": "Avg daily sales (30d)", "value": f"{avg} units/day", "source": "sales"},
                {"fact": "Days remaining", "value": f"{days} days", "source": "calculated"},
            ]
        }
    elif scenario_type == "overstock":
        return {
            "severity": "INFO",
            "action": f"Consider promotion or inter-store transfer of {name}.",
            "reason": f"At the current rate of {avg} units/day, the existing stock of {stock} units will last {days} days — well above the 60-day overstock threshold.",
            "evidence": [
                {"fact": "Current stock", "value": f"{stock} units", "source": "inventory"},
                {"fact": "Avg daily sales (30d)", "value": f"{avg} units/day", "source": "sales"},
                {"fact": "Days remaining", "value": f"{days} days", "source": "calculated"},
            ]
        }
    elif scenario_type == "spike":
        if prev > 0:
            change_pct = round(((avg - prev) / prev) * 100, 1)
            reason_str = f"Sales rose from {prev} to {avg} units/day ({'+' if change_pct > 0 else ''}{change_pct}%)."
        else:
            reason_str = f"Current avg sales: {avg} units/day (no prior period data)."
        return {
            "severity": "INFO",
            "action": f"Investigate demand increase for {name} and verify inventory availability.",
            "reason": reason_str,
            "evidence": [
                {"fact": "Current avg daily sales (30d)", "value": f"{avg} units/day", "source": "sales"},
                {"fact": "Prev period avg daily sales", "value": f"{prev} units/day", "source": "sales"},
                {"fact": "Current stock", "value": f"{stock} units", "source": "inventory"},
            ]
        }
    elif scenario_type == "drop":
        if prev > 0:
            change_pct = round(((avg - prev) / prev) * 100, 1)
            reason_str = f"Sales dropped from {prev} to {avg} units/day ({change_pct}%)."
        else:
            reason_str = f"Current avg sales: {avg} units/day (no prior period data)."
        return {
            "severity": "WARNING",
            "action": f"Review inventory levels and investigate declining sales for {name}.",
            "reason": reason_str,
            "evidence": [
                {"fact": "Current avg daily sales (30d)", "value": f"{avg} units/day", "source": "sales"},
                {"fact": "Prev period avg daily sales", "value": f"{prev} units/day", "source": "sales"},
                {"fact": "Current stock", "value": f"{stock} units", "source": "inventory"},
            ]
        }

    return {"severity": "INFO", "action": "Review product performance.", "reason": "Routine check.", "evidence": []}
