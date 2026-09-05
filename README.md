TRACK_ID=PS03

# StockPilot AI

"AI-powered retail intelligence that turns sales and inventory data into evidence-backed actions."

## Problem
Retail store managers struggle to process large amounts of sales and inventory data to make quick, impactful decisions. They need a tool to monitor stock levels, detect sales anomalies, and answer business questions quickly without hallucinating facts.

## Solution
StockPilot AI is an AI-powered Retail Sales and Inventory Copilot. It monitors inventory health, alerts users to critical stockouts or overstocked items, and detects unusual sales spikes or drops. It features a natural-language copilot grounded purely in deterministic local data to provide accurate, evidence-backed recommendations.

## Key Features
- **Dashboard Overview**: Key KPIs including total revenue, units sold, and stockout risks.
- **Priority Alerts**: Deterministic flagging of stockout risks, overstocks, and sales anomalies.
- **AI Copilot**: Ask natural language questions. The AI uses real database metrics to answer and provide actionable recommendations.
- **Store Filtering**: View data globally or filter by specific store locations.

## Architecture
- **Backend**: Python 3.11, FastAPI, SQLite, SQLAlchemy, Pandas.
- **Frontend**: Server-rendered HTML, CSS, Vanilla JavaScript (no external CDNs).
- **AI**: Google Gemini (via Python SDK), tightly constrained to avoid hallucinations and restricted to generating JSON based strictly on provided context.

## Data
The application generates synthetic, realistic Indian retail data on first run. It creates 3 stores, around 40 products, 90 days of sales history, inventory records, and purchase orders.

## AI Grounding
The AI Copilot does not run open-ended queries or make up facts. The backend intercepts intents, retrieves relevant SQL data, computes deterministic metrics (e.g., average daily sales, days of inventory remaining), and feeds this precise context to Gemini. Gemini then formats the answer, cites evidence, and provides recommendations.

## Business Rules
- **Average Daily Sales**: Total units sold over the last 30 days divided by 30.
- **Days Remaining**: Current stock divided by average daily sales.
- **Critical Stockout**: Days remaining <= 1.
- **Stockout Risk**: Days remaining <= 3.
- **Overstock**: Days remaining > 60.

## How to Run
```bash
pip install -r requirements.txt
python app.py
```
Then open:
http://localhost:8000

- Demo data is generated automatically.
- SQLite is used.
- Gemini API key is optional for dashboard functionality but required for live AI responses (set `GEMINI_API_KEY` in `.env`).

## Demo Scenarios
The generated data intentionally includes these scenarios:
1. **Critical Stockout (Wireless Mouse)**: High recent sales, low inventory (1-2 days remaining).
2. **Overstock (Premium Detergent)**: High inventory, low sales (> 60 days remaining).
3. **Sales Spike (Chocolate Box)**: Recent sales significantly higher than normal.
4. **Sales Drop (Coffee Pack)**: Recent sales significantly lower than historical sales.
5. **Normal Product**: Stable sales, healthy inventory.
6. **Insufficient Data**: If you ask an unsupported question (e.g., "Why did customers stop buying?"), the AI gracefully refuses to hallucinate a cause.

## Demo Video
[Link to Demo Video]
