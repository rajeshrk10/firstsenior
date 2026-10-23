import os #used for accessing few functions of the operating system like environment variables.
import base64 #used for encoding and decoding data in base64 format
#used for symmetric encryption and decryption of data
from cryptography.fernet import Fernet 
#used like sha256 to use hashing algorithms for key derivation and secure password storage.
from cryptography.hazmat.primitives import hashes
# used to derive a secure key from a secret password.
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
# Reuse the same Fernet instance instead of deriving the key for every call.
_fernet_instance: Fernet | None = None


#function used to get the "fernet key" for encryption and decryption.
def _get_fernet_key() -> bytes:# telling the function to return a bytes object.
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    # Use the existing environment variable. No deployment configuration change.
    secret_key = os.getenv("ENCRYPTION_KEY")
    if not secret_key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")

    # Keep these values unchanged to preserve compatibility with existing
    # tokens encrypted by the previous implementation.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),#using SHA256 hashing algorithm for key derivation.
        length=32, #derived key should be 32 bytes long.
        salt=b"firstsenior_salt_2026",
        iterations=100_000,#using for underscore readability.
    )
    #first encoding the secret key to bytes, then deriving a secure key using the KDF, and finally encoding the derived key in a URL-safe base64 format.
    return base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))

#function used to encrypt github access token.
def encrypt_token(plain_token: str) -> str: #telling the function to take a string as input and return a string as output.
    """Encrypt a plain text GitHub access token."""
    if not plain_token:
        return ""
    if HAS_CRYPTOGRAPHY:
        try:
            fernet = Fernet(_get_fernet_key()) #creating a "Fernet object" using the derived key for encryption.

            #first encoding the plain token to bytes, then encrypting it using the Fernet object, and finally decoding the encrypted token back to a string.
            # adding enc prefix to indicate that the token is Fernet encrypted.
            return "enc:" + fernet.encrypt(plain_token.encode()).decode()

        #exception possiblities
            # Invalid encryption key: If the derived key is not valid for Fernet encryption, an exception will be raised.
            # Encryption failure: If there is an issue during the encryption process an exception will be raised.
            # Encoding/decoding errors: if the input is other than string might throw this error
            # Environment variable issues: If the ENCRYPTION_KEY environment variable is not set or is invalid, it may lead to an exception during key derivation
        except Exception as e:
            print(f"Encryption error: {e}")
            return plain_token
    else:
        # Simple base64 fallback if cryptography library is not installed
        return "b64:" + base64.b64encode(plain_token.encode()).decode()

#function used to decrypt github access token.
def decrypt_token(encrypted_token: str) -> str: #telling the function to take a string as input and return a string as output.
    """Decrypt an encrypted GitHub access token."""

    #if the encrypted token is empty or None, return an empty string.
    if not encrypted_token:
        return ""

    #if the encrypted value starts with "enc:" and the cryptography library is available.
    if encrypted_token.startswith("enc:") and HAS_CRYPTOGRAPHY:
        try:
            fernet = Fernet(_get_fernet_key()) #creating a "Fernet object" using the derived key for decryption.
            raw = encrypted_token[4:] #removing the "enc:" prefix from the encrypted token to get the actual encrypted data.

            #first encoding the raw value to bytes, then decrypting it using the Fernet object, and finally decoding the decrypted token back to a string.
            return fernet.decrypt(raw.encode()).decode()
       #exception possiblities
            # Invalid encryption key: If the derived key is not valid for Fernet decryption, an exception will be raised.
            # Decryption failure: If the encrypted token is tampered with or corrupted, an exception will be raised during decryption.
        except Exception:
            return encrypted_token
    #if the encrypted value starts with "b64:" and the cryptography library is not available.
    elif encrypted_token.startswith("b64:"):
        try:
            raw = encrypted_token[4:] #removing the "b64:" prefix from the encrypted token to get the actual base64 encoded data.

            #first encoding the raw value to bytes, then    secdecoding it from base64, and finally decoding the result back to a string.
            return base64.b64decode(raw.encode()).decode()
        except Exception:
            return encrypted_token
    else:
        # Fallback if token was saved unencrypted
        return encrypted_token
