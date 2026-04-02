import sqlite3
import hashlib
import os

DB_PATH = 'hospital.db'

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    # Enable fetching rows as dict-like objects
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # Create patients table
    # Notice that contact and medical_history are stored as TEXT,
    # since we will store base64 encoded Fernet tokens (ciphertext)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            contact TEXT,
            medical_history TEXT
        )
    ''')

    conn.commit()
    conn.close()

def hash_password(password):
    """Returns SHA-256 hash of the password."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_user(username, password):
    """Creates a new user with hashed password."""
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    """Verifies a user's credentials."""
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = hash_password(password)
    cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username, password_hash))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def add_patient(name, age, gender, contact_encrypted, medical_history_encrypted):
    """Adds a new patient to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO patients (name, age, gender, contact, medical_history)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, age, gender, contact_encrypted, medical_history_encrypted))
    conn.commit()
    conn.close()

def get_all_patients():
    """Retrieves all patients from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    conn.close()
    return [dict(row) for row in patients]

def reencrypt_all_patients(old_key, new_key):
    """
    Atomically re-encrypts all patient records when the encryption key is rotated.

    Process:
      1. Decrypt every sensitive field (contact, medical_history) using old_key.
      2. Validate that decryption succeeded for every record.
      3. Re-encrypt every field with new_key.
      4. Write ALL updates inside a single transaction — if anything fails at
         any step, the transaction is rolled back and the database is unchanged.

    Returns:
        (success: bool, message: str)
    """
    import encryption_utils as enc

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, contact, medical_history FROM patients")
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return True, "No patient records to migrate. Key updated."

        # ── Phase 1: Decrypt & validate ALL records before touching the DB ──
        updates = []
        for row in rows:
            patient_id = row["id"]

            plain_contact = enc.decrypt_data(row["contact"], old_key)
            plain_history = enc.decrypt_data(row["medical_history"], old_key)

            # decrypt_data returns None or a "<DECRYPTION_FAILED…>" sentinel on error
            failed = (
                plain_contact is None or plain_history is None
                or "<DECRYPTION_FAILED" in str(plain_contact)
                or "<DECRYPTION_FAILED" in str(plain_history)
            )
            if failed:
                conn.close()
                return False, (
                    f"❌ Could not decrypt record ID {patient_id} with the current key. "
                    "Key rotation aborted — your old key remains active and all data is safe."
                )

            new_contact = enc.encrypt_data(plain_contact, new_key)
            new_history = enc.encrypt_data(plain_history, new_key)

            if new_contact is None or new_history is None:
                conn.close()
                return False, (
                    f"❌ Could not re-encrypt record ID {patient_id} with the new key. "
                    "Key rotation aborted — your old key remains active and all data is safe."
                )

            updates.append((new_contact, new_history, patient_id))

        # ── Phase 2: All records validated — write atomically ──
        cursor.execute("BEGIN")
        for new_contact, new_history, patient_id in updates:
            cursor.execute(
                "UPDATE patients SET contact = ?, medical_history = ? WHERE id = ?",
                (new_contact, new_history, patient_id),
            )
        conn.commit()
        return True, f"✅ Key rotated successfully. {len(updates)} record(s) re-encrypted."

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, (
            f"❌ Unexpected error during key rotation: {exc}. "
            "Database rolled back — your old key remains active."
        )
    finally:
        conn.close()

# Initialize db when this module is loaded
init_db()
