import jwt
import httpx
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

class ClerkAuth:
    """Xác thực Token JWT từ Clerk gửi tới Backend FastAPI"""
    
    def __init__(self):
        # Lấy JWKS URL từ Publishable Key (Bóc tách domain)
        # VD: pk_test_Y2xlcmsuYmVzdC1jaGltcC0xMC5jbGVyay5hY2NvdW50cy5kZXYJA -> https://clerk.best-chimp-10.clerk.accounts.dev/.well-known/jwks.json
        # Tạm thời cấu trúc cơ bản vì key Clerk thật lấy từ API trực tiếp an toàn hơn.
        self.jwks_url = "https://api.clerk.dev/v1/jwks"
        self.clerk_secret = settings.CLERK_SECRET_KEY

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(security)):
        token = credentials.credentials
        if not token:
            raise HTTPException(status_code=401, detail="Token missing")

        try:
            # decode token headers để lấy kid
            unverified_headers = jwt.get_unverified_header(token)
            
            # TODO: Trong production, nên cache lại JWKS này bằng Redis để tránh gọi API liên tục
            async with httpx.AsyncClient() as client:
                jwks_res = await client.get(
                    self.jwks_url, 
                    headers={"Authorization": f"Bearer {self.clerk_secret}"}
                )
                jwks_res.raise_for_status()
                jwks = jwks_res.json()

            # Tìm key tương ứng
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key["kid"] == unverified_headers["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break
                    
            if not rsa_key:
                raise HTTPException(status_code=401, detail="Unable to find appropriate key")

            # Tạo public key và giải mã
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            
            return payload # Trả về user details (sub/id) từ Clerk
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

get_current_user = ClerkAuth().verify_token
