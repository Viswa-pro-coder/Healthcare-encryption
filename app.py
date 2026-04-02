import streamlit as st
import database as db
import encryption_utils as enc
import pandas as pd

# Set page config
st.set_page_config(page_title="Hospital Management System (Encrypted)", layout="wide")

# Initialize session state for auth and encryption key
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'encryption_key' not in st.session_state:
    # Initialize with a key so the app works out of the box,
    # but give the user the ability to generate a new one.
    st.session_state['encryption_key'] = enc.generate_key()

# Sidebar: Key Management and Display
with st.sidebar:
    st.title("Security Settings")
    st.markdown("### Current Symmetric Key")
    # Display the key clearly as requested
    st.code(st.session_state['encryption_key'], language="text")

    if st.button("Generate New Key"):
        old_key = st.session_state['encryption_key']
        new_key = enc.generate_key()

        with st.spinner("Re-encrypting all patient records with the new key…"):
            success, message = db.reencrypt_all_patients(old_key, new_key)

        if success:
            st.session_state['encryption_key'] = new_key
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    if st.session_state['logged_in']:
        st.markdown(f"**Logged in as:** {st.session_state['username']}")
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.rerun()

# -----------------
# Authentication
# -----------------
if not st.session_state['logged_in']:
    st.title("Hospital Management System Login")

    # Create default user if not exists for demo purposes
    db.create_user("admin", "admin123")

    st.info("Demo account: Username: 'admin', Password: 'admin123'")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if db.verify_user(username, password):
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.success("Login Successful!")
            st.rerun()
        else:
            st.error("Invalid Username or Password")
    st.stop()

# -----------------
# Main Application
# -----------------
st.title("Hospital Management System")

tab1, tab2 = st.tabs(["Add Patient", "View Records"])

with tab1:
    st.header("Add Patient Record")
    st.markdown("Data entered here will be encrypted before being saved to the database.")

    with st.form("add_patient_form"):
        name = st.text_input("Full Name")
        age = st.number_input("Age", min_value=0, max_value=120, value=30)
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])
        contact = st.text_input("Contact Info (Phone/Email)")
        medical_history = st.text_area("Medical History & Notes")

        submitted = st.form_submit_button("Save Patient")

        if submitted:
            if name and contact and medical_history:
                # Encrypt sensitive data
                key = st.session_state['encryption_key']
                contact_enc = enc.encrypt_data(contact, key)
                history_enc = enc.encrypt_data(medical_history, key)

                if contact_enc and history_enc:
                    db.add_patient(name, age, gender, contact_enc, history_enc)
                    st.success(f"Patient {name} added successfully! Sensitive data encrypted.")
                else:
                    st.error("Encryption failed. Patient not added.")
            else:
                st.warning("Please fill in all required fields (Name, Contact, Medical History).")

with tab2:
    st.header("View Patient Records")

    # Manual View Control
    decrypt_data = st.toggle("Decrypt Sensitive Data", value=False)

    if decrypt_data:
        st.info("Decryption ON: Displaying readable plaintext data. (Requires correct key)")
    else:
        st.warning("Decryption OFF: Displaying raw ciphertext directly from database.")

    patients = db.get_all_patients()

    if not patients:
        st.info("No patient records found.")
    else:
        # Prepare data for display
        display_data = []
        key = st.session_state['encryption_key']

        for p in patients:
            row = {
                "ID": p["id"],
                "Name": p["name"],
                "Age": p["age"],
                "Gender": p["gender"]
            }

            if decrypt_data:
                # Decrypt in real-time
                row["Contact Info"] = enc.decrypt_data(p["contact"], key)
                row["Medical History"] = enc.decrypt_data(p["medical_history"], key)
            else:
                # Show raw ciphertext
                row["Contact Info"] = p["contact"]
                row["Medical History"] = p["medical_history"]

            display_data.append(row)

        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
