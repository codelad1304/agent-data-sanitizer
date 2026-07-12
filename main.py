import csv
import io
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Corrected imports for the modern x402 SDK
from x402.http.middleware.fastapi import PaymentMiddlewareASGI as x402Middleware
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from x402.http import HTTPFacilitatorClient, FacilitatorConfig
from x402.server import x402ResourceServer

app = FastAPI(title="Agentic Data Sanitizer API")

# --- 1. Root Health Check Route ---
@app.get("/")
async def root():
    return {"status": "online", "message": "API is running. Use /sanitize-csv for data processing."}

class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS", "0xYourEthereumOrBaseAddressHere")

# --- 2. Initialize Client and Server ---
# Create the facilitator client
facilitator_client = HTTPFacilitatorClient(
    config=FacilitatorConfig(
        url="https://api.cdp.coinbase.com/platform/v2/x402",
        api_key_id=os.getenv("CDP_API_KEY_ID"),
        api_key_secret=os.getenv("CDP_API_KEY_SECRET")
    )
)

# Wrap it in the ResourceServer as required by the middleware
server = x402ResourceServer(facilitator_client=facilitator_client)

# --- 3. Apply the Middleware ---
app.add_middleware(
    x402Middleware,
    routes={
        "/sanitize-csv": {
            "accepts": {
                "scheme": "exact", 
                "price": "0.05", 
                "network": "eip155:8453", 
                "payTo": MY_WALLET_ADDRESS
            }
        }
    },
    server=server, # Pass the server object, not the client directly
    schemes=[ExactEvmScheme()]
)

@app.post("/sanitize-csv")
async def sanitize_csv(request: AgentRequest):
    try:
        csv_file = io.StringIO(request.raw_csv_text)
        reader = csv.DictReader(csv_file)
        cleaned_data = [row for row in reader] 
        
        return {
            "status": "success",
            "data": cleaned_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing error: {str(e)}")
