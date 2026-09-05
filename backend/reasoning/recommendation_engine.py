def get_recommendation_for_alert(alert):
    alert_type = alert.get("type")
    
    if alert_type == "Critical Stockout":
        return {
            "action": f"Reorder {alert['product_name']} immediately for {alert['store_name']}.",
            "reason": f"Only {alert['days_remaining']} days of stock remain ({alert['current_stock']} units)."
        }
    elif alert_type == "Stockout Risk":
        return {
            "action": f"Prepare to reorder {alert['product_name']} for {alert['store_name']}.",
            "reason": f"Only {alert['days_remaining']} days of stock remain."
        }
    elif alert_type == "Overstock":
        return {
            "action": f"Consider promotion or transfer of {alert['product_name']} from {alert['store_name']}.",
            "reason": f"Inventory coverage is high at {alert['days_remaining']} days."
        }
    elif alert_type == "Sales Spike":
        return {
            "action": f"Investigate demand increase for {alert['product_name']} and check inventory availability.",
            "reason": alert.get("details", "Recent sales are significantly higher than historical average.")
        }
    elif alert_type == "Sales Drop":
        return {
            "action": f"Review recent sales trend and inventory availability for {alert['product_name']}.",
            "reason": alert.get("details", "Recent sales are significantly lower than historical average.")
        }
    return {
        "action": "Review inventory levels.",
        "reason": "Routine check."
    }
