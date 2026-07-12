import csv
import io
import os
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
# PLACE THE NEW JWT GENERATION LOGIC HERE
# ==========================================
# 1. Grab keys from the Render environment
key_name = os.environ.get("CDP_API_KEY_NAME")
key_secret = os.environ.get("CDP_API_KEY_PRIVATE_KEY")

# 2. Generate the explicit JWT for the startup check
startup_jwt = generate_jwt(JwtOptions(
    api_key_id=key_name,
    api_key_secret=key_secret
))

# --- 1. Root Health Check Route ---
@app.get("/")
async def root():
    return {"status": "online", "message": "API is running. Use /sanitize-csv for data processing."}

class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS", "0xYourEthereumOrBaseAddressHere")

# --- 2. Initialize Client and Server ---
# The SDK automatically discovers CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY from environment variables
facilitator_client = HTTPFacilitatorClient(
    config=FacilitatorConfig(
        url="https://api.cdp.coinbase.com/platform/v2/x402",
        headers={"Authorization": f"Bearer {startup_jwt}"}
    )
)

# Initialize the ResourceServer and register the scheme here
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
        # Process data
        cleaned_data = [row for row in reader] 
        
        return {
            "status": "success",
            "records_processed": len(cleaned_data),
            "data": cleaned_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing error: {str(e)}")
