import csv
import io
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Core open-source x402 Imports (No proprietary wrappers required)
from x402.http.middleware.fastapi import PaymentMiddlewareASGI as x402Middleware
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from x402.http import HTTPFacilitatorClient, FacilitatorConfig
from x402.server import x402ResourceServer

app = FastAPI(title="Agentic Data Sanitizer API")

# Initialize the facilitator using the open, signup-free public protocol network
facilitator_client = HTTPFacilitatorClient(
    config=FacilitatorConfig(url="https://x402.org/facilitator")
)

# --- 1. Root Health Check Route ---
@app.get("/")
async def root():
    return {"status": "online", "message": "API is running. Use /sanitize-csv for data processing."}

class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

# Pull your real wallet address securely from the Render environment
MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS", "0xYourEthereumOrBaseAddressHere")

# --- 2. Initialize Resource Server ---
server = x402ResourceServer(facilitator_clients=[facilitator_client])
server.register("eip155:8453", ExactEvmScheme())

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
    server=server
)

@app.post("/sanitize-csv")
async def sanitize_csv(request: AgentRequest):
    try:
        csv_file = io.StringIO(request.raw_csv_text)
        reader = csv.DictReader(csv_file)
        cleaned_data = [row for row in reader] 
        
        return {
            "status": "success",
            "records_processed": len(cleaned_data),
            "data": cleaned_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing error: {str(e)}")
