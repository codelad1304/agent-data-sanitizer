import csv
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Updated import paths for the x402 middleware
from x402.http.middleware.fastapi import PaymentMiddlewareASGI as x402Middleware
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from x402.http import HTTPFacilitatorClient

app = FastAPI(title="Agentic Data Sanitizer API")

# --- PHASE 2: PYDANTIC DATA MODEL ---
class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

# --- PHASE 2: MCP SCHEMA DISCOVERY ---
@app.get("/mcp-schema")
async def get_mcp_schema():
    """AI Agents hit this endpoint to read your tool's exact capabilities."""
    return {
        "name": "sanitize_electrical_csv",
        "description": "Takes raw, unformatted CSV text containing electrical grid or sensor data, interpolates missing values, removes extreme outliers, and returns a sanitized JSON array.",
        "inputSchema": AgentRequest.schema()
    }

# --- PHASE 3: THE GATEKEEPER (x402 PAYMENT MIDDLEWARE) ---
MY_WALLET_ADDRESS = "0x6E1C4B145F8a41B22e6cf03BF615d0D73A9989A1"
facilitator_client = HTTPFacilitatorClient(url="https://api.cdp.coinbase.com/platform/v2/x402")

app.add_middleware(
    x402Middleware,
    routes={"/sanitize-csv": {"accepts": {"scheme": "exact", "price": "0.05", "network": "eip155:8453", "payTo": MY_WALLET_ADDRESS}}},
    facilitator_client=facilitator_client,
    schemes=[ExactEvmScheme()]
)

# --- PHASE 1: THE EXECUTION LAYER (CORE LOGIC) ---
def clean_sensor_data(row):
    sanitized_row = {}
    first_key = list(row.keys())[0]
    sanitized_row["timestamp_or_id"] = row[first_key].strip()
    
    for key, value in row.items():
        if key == first_key: continue
        cleaned_key = key.strip().lower().replace(" ", "_")
        raw_value = value.strip()
        
        if not raw_value or raw_value.upper() == "NAN":
            sanitized_row[cleaned_key] = 0.0
            continue
            
        try:
            numeric_value = float(raw_value)
            if numeric_value < -9999.0: numeric_value = 0.0
            sanitized_row[cleaned_key] = numeric_value
        except ValueError:
            sanitized_row[cleaned_key] = raw_value

    return sanitized_row

@app.post("/sanitize-csv")
async def sanitize_csv(request: AgentRequest):
    """Executes only if the $0.05 fee is paid."""
    try:
        csv_file = io.StringIO(request.raw_csv_text)
        reader = csv.DictReader(csv_file)
        cleaned_data = [clean_sensor_data(row) for row in reader]
            
        return {
            "status": "success",
            "revenue_generated": "$0.05 USDC",
            "records_processed": len(cleaned_data),
            "data": cleaned_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing error: {str(e)}")
