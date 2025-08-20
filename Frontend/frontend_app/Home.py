import streamlit as st
import requests
from utils.api_client import api_client



def main():
    st.set_page_config(
        page_title="Reddit Automation Suite - Login",
        page_icon="🤖",
        layout="centered"
    )

    st.title("🤖 Reddit Automation Suite")
    st.markdown("---")

    # Login Form
    with st.form("login_form"):
        st.subheader("Login to Your Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            if api_client.login(username, password):
                st.success("Login successful!")
                st.session_state.user_authenticated = True
                st.switch_page("pages/1_Dashboard.py")
            else:
                st.error("Invalid credentials")


if __name__ == "__main__":
    main()