import os
import json
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth, credentials, initialize_app

# Initialize Firebase Admin with your project credentials
# You'll need to download your Firebase service account key from the Firebase Console
# Save it as firebase_credentials.json
cred_path = "firebase_credentials.json"

if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_app = initialize_app(cred)
else:
    print("WARNING: Firebase credentials not found. Auth verification will fail.")

# Security scheme for token verification
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify Firebase ID token and return the user.
    This can be used as a dependency in FastAPI routes.
    """
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        return {"uid": uid, "email": decoded_token.get("email")}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )