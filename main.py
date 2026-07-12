import csv
import io
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Corrected imports for the modern x402 SDK
from x402.http.middleware.fastapi import PaymentMiddlewareASGI as x402Middleware
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from cdp.auth.utils.jwt import generate_jwt, JwtOptions
from x402.http import HTTPFacilitatorClient, FacilitatorConfig
from x402.server import x402ResourceServer

app = FastAPI(title="Agentic Data Sanitizer API")

# ==========================================
# 1. Grab keys from the Render environment
key_name = os.environ.get("CDP_API_KEY_ID")
key_secret = os.environ.get("CDP_API_KEY_SECRET")

# 2. Guard against missing variables during Render's build phase
if key_name and key_secret:
    startup_jwt = generate_jwt(JwtOptions(
        api_key_id=key_name,
        api_key_secret=key_secret
    ))
    
    # Use standard httpx.Client, NOT httpx.AsyncClient
    custom_client = httpx.Client(
        headers={"Authorization": f"Bearer {startup_jwt}"}
    )
    
    facilitator_client = HTTPFacilitatorClient(
        config=FacilitatorConfig(url="https://api.cdp.coinbase.com/platform/v2/x402"),
        client=custom_client
    )
else:
    # Fallback to prevent crash if Render scans the file without env vars
    print("WARNING: CDP API Keys not found in environment!")
    facilitator_client = HTTPFacilitatorClient(
        config=FacilitatorConfig(url="https://api.cdp.coinbase.com/platform/v2/x402")
    )
# ==========================================

# --- 1. Root Health Check Route ---
@app.get("/")
async def root():
    return {"status": "online", "message": "API is running. Use /sanitize-csv for data processing."}

class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS", "0xYourEthereumOrBaseAddressHere")

# --- 2. Initialize Client and Server ---
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
