import os
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

def _get_fernet_key() -> bytes:
    if not HAS_CRYPTOGRAPHY:
        return b""
    secret_key = os.getenv("ENCRYPTION_KEY", "firstsenior_default_secret_key_change_in_prod")
    salt = b'firstsenior_salt_2026'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))

def encrypt_token(plain_token: str) -> str:
    """Encrypt a plain text GitHub access token."""
    if not plain_token:
        return ""
    if HAS_CRYPTOGRAPHY:
        try:
            fernet = Fernet(_get_fernet_key())
            return "enc:" + fernet.encrypt(plain_token.encode()).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return plain_token
    else:
        # Simple base64 fallback if cryptography library is not installed
        return "b64:" + base64.b64encode(plain_token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted GitHub access token."""
    if not encrypted_token:
        return ""
    if encrypted_token.startswith("enc:") and HAS_CRYPTOGRAPHY:
        try:
            fernet = Fernet(_get_fernet_key())
            raw = encrypted_token[4:]
            return fernet.decrypt(raw.encode()).decode()
        except Exception:
            return encrypted_token
    elif encrypted_token.startswith("b64:"):
        try:
            raw = encrypted_token[4:]
            return base64.b64decode(raw.encode()).decode()
        except Exception:
            return encrypted_token
    else:
        # Fallback if token was saved unencrypted
        return encrypted_token
