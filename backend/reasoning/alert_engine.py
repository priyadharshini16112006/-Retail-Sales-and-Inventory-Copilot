from sqlalchemy.orm import Session
from .metrics import calculate_metrics

def generate_alerts(db: Session, store_id: int = None):
    metrics = calculate_metrics(db, store_id)
    alerts = []
    
    for m in metrics:
        alert = None
        
        # 1. Critical Stockout (<= 1 day)
        if m['days_remaining'] <= 1:
            alert = {
                "type": "Critical Stockout",
                "severity": "CRITICAL",
                "product_name": m['product_name'],
                "store_name": m['store_name'],
                "current_stock": m['current_stock'],
                "avg_daily_sales": m['avg_daily_sales'],
                "days_remaining": m['days_remaining']
            }
        # 2. Stockout Risk (<= 3 days)
        elif m['days_remaining'] <= 3:
            alert = {
                "type": "Stockout Risk",
                "severity": "WARNING",
                "product_name": m['product_name'],
                "store_name": m['store_name'],
                "current_stock": m['current_stock'],
                "avg_daily_sales": m['avg_daily_sales'],
                "days_remaining": m['days_remaining']
            }
        # 3. Overstock (> 60 days)
        elif m['days_remaining'] > 60 and m['current_stock'] > 0:
            alert = {
                "type": "Overstock",
                "severity": "INFO",
                "product_name": m['product_name'],
                "store_name": m['store_name'],
                "current_stock": m['current_stock'],
                "avg_daily_sales": m['avg_daily_sales'],
                "days_remaining": m['days_remaining']
            }
            
        if alert:
            alerts.append(alert)

        # 4. Sales Anomaly (Spike)
        if m['avg_daily_sales'] > (m['prev_avg_daily_sales'] * 1.8) and m['prev_avg_daily_sales'] > 0:
            alerts.append({
                "type": "Sales Spike",
                "severity": "INFO",
                "product_name": m['product_name'],
                "store_name": m['store_name'],
                "avg_daily_sales": m['avg_daily_sales'],
                "prev_avg_daily_sales": m['prev_avg_daily_sales'],
                "details": f"Sales increased from {m['prev_avg_daily_sales']} to {m['avg_daily_sales']} per day."
            })
            
        # 5. Sales Anomaly (Drop)
        elif m['avg_daily_sales'] < (m['prev_avg_daily_sales'] * 0.4) and m['prev_avg_daily_sales'] > 2:
            alerts.append({
                "type": "Sales Drop",
                "severity": "WARNING",
                "product_name": m['product_name'],
                "store_name": m['store_name'],
                "avg_daily_sales": m['avg_daily_sales'],
                "prev_avg_daily_sales": m['prev_avg_daily_sales'],
                "details": f"Sales dropped from {m['prev_avg_daily_sales']} to {m['avg_daily_sales']} per day."
            })

    # Sort alerts by severity (CRITICAL first, then WARNING, then INFO)
    severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return alerts
