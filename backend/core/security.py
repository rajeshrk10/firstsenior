
import os
import base64

# Fernet provides authenticated encryption:
# it encrypts the token and detects tampering with encrypted data.
from cryptography.fernet import Fernet, InvalidToken

# These imports are used to derive a valid Fernet key from
# the existing ENCRYPTION_KEY environment variable.
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Initially, no Fernet object exists.
# We create it the first time encryption or decryption is needed,
# then reuse it instead of deriving the key on every call.
_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    """
    Return the Fernet encryption object.

    The underscore in _get_fernet indicates this is an internal
    helper function intended for use inside this module.
    """
    global _fernet_instance

    # If the Fernet object was already created, reuse it.
    if _fernet_instance is not None:
        return _fernet_instance

    # Read the existing secret from the environment.
    # Do not use a hardcoded fallback because that could
    # accidentally encrypt tokens with a publicly known secret.
    secret_key = os.getenv("ENCRYPTION_KEY")

    if not secret_key:
        raise RuntimeError("ENCRYPTION_KEY is not configured")

    # PBKDF2 converts the secret into a key suitable for Fernet.
    # Keep these settings unchanged to maintain compatibility
    # with tokens encrypted using the previous implementation.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # Required key length before Fernet encoding
        salt=b"firstsenior_salt_2026",
        iterations=100_000,
    )

    # Derive the encryption key from the configured secret.
    # Fernet expects the resulting key in URL-safe Base64 format.
    derived_key = base64.urlsafe_b64encode(
        kdf.derive(secret_key.encode("utf-8"))
    )

    # Create the Fernet object and cache it for future calls.
    _fernet_instance = Fernet(derived_key)

    return _fernet_instance


def encrypt_token(plain_token: str) -> str:
    """
    Encrypt a plain GitHub token.

    Example:
        Input:  ghp_example_token
        Output: enc:<encrypted-data>
    """
    # Reject empty tokens instead of storing meaningless values.
    if not plain_token:
        raise ValueError("Token must not be empty")

    # Encrypt the token's UTF-8 bytes.
    encrypted = _get_fernet().encrypt(
        plain_token.encode("utf-8")
    )

    # Preserve the existing 'enc:' prefix so the rest of the
    # application can continue recognizing encrypted tokens.
    return "enc:" + encrypted.decode("ascii")


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token previously produced by encrypt_token().
    """
    # An empty stored token is not a valid encrypted token.
    if not encrypted_token:
        raise ValueError("Stored token must not be empty")

    # Our existing database format uses the 'enc:' prefix.
    prefix = "enc:"

    # Refuse unknown formats rather than treating unencrypted
    # data as a valid credential.
    if not encrypted_token.startswith(prefix):
        raise ValueError(
            "Unsupported token format; the stored token may need migration"
        )

    # Remove 'enc:' before passing the encrypted content to Fernet.
    raw_token = encrypted_token[len(prefix):]

    try:
        # Decrypt the data and convert the resulting bytes to text.
        decrypted = _get_fernet().decrypt(
            raw_token.encode("ascii")
        )
        return decrypted.decode("utf-8")

    except InvalidToken:
        # This can happen if the data was changed or the key
        # does not match the key used when it was encrypted.
        raise RuntimeError(
            "Token decryption failed; check the encryption key and stored data"
        ) from None

    except UnicodeEncodeError:
        # The stored encrypted text was not valid ASCII.
        raise RuntimeError(
            "Stored token has an invalid format"
        ) from None

    except UnicodeDecodeError:
        # Decryption produced bytes that are not valid UTF-8 text.
        raise RuntimeError(
            "Decrypted token is not valid UTF-8"
        ) from None
