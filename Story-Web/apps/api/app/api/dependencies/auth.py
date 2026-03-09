import jwt
import httpx
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


class ClerkAuth:
    """Xác thực Token JWT từ Clerk gửi tới Backend FastAPI"""

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(security)):
        token = credentials.credentials
        if not token:
            raise HTTPException(status_code=401, detail="Token missing")

        try:
            # Lấy headers và payload chưa verify để đọc kid + iss
            unverified_headers = jwt.get_unverified_header(token)
            unverified_payload = jwt.decode(
                token,
                key="",
                algorithms=["RS256"],
                options={"verify_signature": False},
            )

            # Clerk JWKS URL = {iss}/.well-known/jwks.json (public, không cần auth)
            iss = unverified_payload.get("iss")
            if not iss:
                raise HTTPException(status_code=401, detail="Invalid token: missing issuer")

            jwks_url = f"{iss}/.well-known/jwks.json"

            async with httpx.AsyncClient() as client:
                jwks_res = await client.get(jwks_url)
                jwks_res.raise_for_status()
                jwks = jwks_res.json()

            # Tìm key khớp kid
            rsa_key = {}
            for key in jwks.get("keys", []):
                if key["kid"] == unverified_headers["kid"]:
                    rsa_key = {k: key[k] for k in ("kty", "kid", "use", "n", "e")}
                    break

            if not rsa_key:
                raise HTTPException(status_code=401, detail="Unable to find appropriate key")

            # Verify và decode
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


get_current_user = ClerkAuth().verify_token
