import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Password Context with explicit bcrypt cost factor 12
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt (cost factor 12)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def parse_uuid(val: Any) -> uuid.UUID:
    """Safely parse string or UUID object into a Python uuid.UUID instance. Raises ValueError on invalid format."""
    if isinstance(val, uuid.UUID):
        return val
    if not val or not isinstance(val, str):
        raise ValueError("Invalid UUID: string or UUID object expected")
    try:
        return uuid.UUID(val)
    except Exception:
        raise ValueError(f"Invalid UUID string format: '{val}'")


def create_access_token(
    user_id: str,
    institution_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT Access Token with unique UUID4 jti."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "institution_id": str(institution_id),
        "role": str(role),
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str,
    institution_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed JWT Refresh Token with unique UUID4 jti."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta else timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "institution_id": str(institution_id),
        "role": str(role),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token. Raises ValueError if invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
    """Ensure token type matches expected_type ('access' vs 'refresh')."""
    token_type = payload.get("type")
    if not token_type or token_type != expected_type:
        raise ValueError(f"Invalid token type: expected '{expected_type}', got '{token_type}'")
