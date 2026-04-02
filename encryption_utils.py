import logging
from cryptography.fernet import Fernet, InvalidToken

# Set up simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_key():
    """Generates a new Fernet key."""
    return Fernet.generate_key().decode('utf-8')

def encrypt_data(data, key):
    """
    Encrypts string data using the provided Fernet key.

    Args:
        data (str): The plaintext string to encrypt.
        key (str): The Fernet key (base64 encoded string).

    Returns:
        str: The encrypted ciphertext as a string.
    """
    if data is None:
        return None
    try:
        f = Fernet(key.encode('utf-8'))
        return f.encrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        # In a real app, you might want to raise the exception.
        # For this demo, return raw or error string.
        return None

def decrypt_data(encrypted_data, key):
    """
    Decrypts string data using the provided Fernet key.

    Args:
        encrypted_data (str): The ciphertext string to decrypt.
        key (str): The Fernet key (base64 encoded string).

    Returns:
        str: The decrypted plaintext string.
             If decryption fails (e.g. wrong key), returns an error message.
    """
    if encrypted_data is None:
        return None
    try:
        f = Fernet(key.encode('utf-8'))
        return f.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        logger.warning("Decryption failed: InvalidToken (Likely wrong key used).")
        return "<DECRYPTION_FAILED: INVALID_KEY>"
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return "<DECRYPTION_FAILED: ERROR>"
