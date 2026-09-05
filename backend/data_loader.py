import os
import random
from datetime import datetime, timedelta
from .database import engine, Base, SessionLocal, Store, Product, Inventory, Sale, PurchaseOrder

def generate_demo_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    if db.query(Store).first():
        db.close()
        return

    print("Generating demo data...")
    random.seed(42)  # Deterministic generation

    # Stores
    stores = [
        Store(name="Chennai Downtown", city="Chennai"),
        Store(name="Chennai Mall", city="Chennai"),
        Store(name="Coimbatore Neighborhood", city="Coimbatore")
    ]
    db.add_all(stores)
    db.commit()

    # Products
    categories = ["Dairy", "Bakery", "Beverages", "Snacks", "Produce", "Household", "Electronics"]
    products = [
        Product(name="Wireless Mouse", category="Electronics", price=499.0, cost=250.0, description="Standard wireless mouse", supplier="TechSupplies"),
        Product(name="Premium Detergent", category="Household", price=250.0, cost=180.0, description="5KG washing machine detergent", supplier="CleanCo"),
        Product(name="Chocolate Box", category="Snacks", price=350.0, cost=200.0, description="Assorted chocolate box", supplier="SweetTreats"),
        Product(name="Coffee Pack", category="Beverages", price=150.0, cost=90.0, description="500g filter coffee powder", supplier="BrewMaster")
    ]
    
    # Generate 36 more random products
    for i in range(36):
        cat = random.choice(categories)
        price = random.randint(50, 1000)
        products.append(Product(
            name=f"{cat} Item {i+1}",
            category=cat,
            price=float(price),
            cost=float(price * 0.6),
            description=f"Standard {cat} item",
            supplier="GenericSupplier"
        ))
    db.add_all(products)
    db.commit()

    # Generate Inventory & Sales
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=90)
    
    db_stores = db.query(Store).all()
    db_products = db.query(Product).all()

    sales_records = []
    inventory_records = []

    for store in db_stores:
        for product in db_products:
            # Scenarios setup
            avg_daily_sales = random.uniform(1.0, 10.0)
            current_stock = int(avg_daily_sales * random.uniform(15, 30))
            reorder_level = int(avg_daily_sales * 7)

            if product.name == "Wireless Mouse":
                avg_daily_sales = 6.2
                current_stock = 8  # CRITICAL STOCKOUT
                reorder_level = 15
            elif product.name == "Premium Detergent":
                avg_daily_sales = 5.8
                current_stock = 420  # OVERSTOCK
                reorder_level = 40
            elif product.name == "Chocolate Box":
                avg_daily_sales = 4.0
                current_stock = 50
                reorder_level = 20
            elif product.name == "Coffee Pack":
                avg_daily_sales = 8.0
                current_stock = 60
                reorder_level = 25

            inventory_records.append(Inventory(
                product_id=product.id,
                store_id=store.id,
                quantity=current_stock,
                reorder_level=reorder_level,
                last_updated=datetime.utcnow()
            ))

            # Generate Sales
            for day_offset in range(90):
                current_date = start_date + timedelta(days=day_offset)
                
                # Daily variation
                daily_units = int(random.gauss(avg_daily_sales, avg_daily_sales * 0.2))
                
                if product.name == "Chocolate Box" and day_offset > 80:
                    daily_units = int(avg_daily_sales * 3) # SPIKE
                
                if product.name == "Coffee Pack" and day_offset > 80:
                    daily_units = int(avg_daily_sales * 0.2) # DROP
                
                if daily_units < 0: daily_units = 0

                sales_records.append(Sale(
                    date=current_date,
                    product_id=product.id,
                    store_id=store.id,
                    units_sold=daily_units,
                    revenue=daily_units * product.price
                ))

    # Bulk insert for speed
    db.bulk_save_objects(inventory_records)
    
    # Process sales in chunks to avoid memory issues
    chunk_size = 5000
    for i in range(0, len(sales_records), chunk_size):
        db.bulk_save_objects(sales_records[i:i+chunk_size])
        
    db.commit()
    db.close()
    print("Demo data generated successfully.")

if __name__ == "__main__":
    generate_demo_data()
