import csv
import io
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Modern x402 imports
from x402.http.middleware.fastapi import PaymentMiddlewareASGI as x402Middleware
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from x402.http import HTTPFacilitatorClient, FacilitatorConfig

app = FastAPI(title="Agentic Data Sanitizer API")

class AgentRequest(BaseModel):
    raw_csv_text: str = Field(..., description="The raw, unformatted CSV text data.")

# Fetch wallet address from environment variables for security
MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS", "0xYourEthereumOrBaseAddressHere")

# Initialize client using the required FacilitatorConfig object
facilitator_client = HTTPFacilitatorClient(
    config=FacilitatorConfig(url="https://api.cdp.coinbase.com/platform/v2/x402")
)

# Apply the x402 middleware
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
    facilitator_client=facilitator_client,
    schemes=[ExactEvmScheme()]
)

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
            "records_processed": len(cleaned_data),
            "data": cleaned_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing error: {str(e)}")
