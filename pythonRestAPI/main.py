from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from jose import jwt  # You need to install python-jose
from jose import JWTError
from fastapi.responses import FileResponse
import logging
import requests
import fitz

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()


# Azure AD Configuration
TENANT_ID = "b5d31b4e-6d83-4373-b61b-de1b0cd6f140"
CLIENT_ID = "6bf0a972-724c-4751-a75c-1e1c6e05af91"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
JWKS_URL = f"{AUTHORITY}/discovery/v2.0/keys"

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{AUTHORITY}/oauth2/v2.0/authorize",
    tokenUrl=f"{AUTHORITY}/oauth2/v2.0/token"
)

def get_public_keys():
    try:
        response = requests.get(JWKS_URL)
        response.raise_for_status()
        jwks = response.json()
        return {key["kid"]: key for key in jwks["keys"]}
    except requests.RequestException as e:
        logger.error(f"Failed to fetch JWKS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {str(e)}")

def decode_token(token: str):
    try:
        keys = get_public_keys()
        unverified_header = jwt.get_unverified_header(token)
        logger.debug(f"Token header: {unverified_header}")
        key = keys.get(unverified_header["kid"])
        if not key:
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid token header: kid not found")
        # Allow audience with api:// prefix
        payload = jwt.decode(token, key, algorithms=["RS256"], audience=f"api://{CLIENT_ID}")
        logger.debug(f"Decoded payload: {payload}")
        return payload
    except JWTError as e:
        logger.error(f"Token decoding failed: {str(e)}")
        logger.error(f"Expected audience: api://{CLIENT_ID}")
        logger.error(f"Token (partial): {token[:20]}...")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=f"Token decoding failed: {str(e)}")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.debug(f"Received token: {token[:10]}...")
    try:
        payload = decode_token(token)
        return payload
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.get("/getprocessnumber")
async def consultar(protocol: str, user_info: dict = Depends(get_current_user)):
    user_email = user_info.get("upn", "unknown")
    return {"message": "0014356-84.2024.8.16.6000", "user_email": user_email}



@app.get("/getprocessdetails")
async def get_pdf_text(user_info: dict = Depends(get_current_user)):
    pdf_path = "pdfs/processo.pdf"
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return {"text": text}        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error to read the PDF: {str(e)}")


