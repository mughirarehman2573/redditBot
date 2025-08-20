import streamlit as st
from utils.api_client import api_client



def main():
    st.set_page_config(
        page_title="Manage Accounts - Reddit Automation",
        page_icon="👥",
        layout="wide"
    )

    st.title("👥 Manage Reddit Accounts")
    st.markdown("---")

    # Connect New Account Button
    if st.button("🔗 Connect New Reddit Account", type="primary"):
        st.markdown('<meta http-equiv="refresh" content="0; url=http://localhost:8000/api/v1/auth/reddit/connect">',
                    unsafe_allow_html=True)
        st.info("Redirecting to Reddit authentication...")

    # List Connected Accounts
    st.subheader("Connected Accounts")
    accounts = api_client.get("/api/v1/accounts/") or []

    if accounts:
        for acc in accounts:
            with st.expander(f"u/{acc['reddit_username']} - {acc['status']}"):
                st.write(f"Karma: {acc['karma']}")
                st.write(f"Posts: {acc['total_posts']}")
                st.write(f"Comments: {acc['total_comments']}")
    else:
        st.info("No accounts connected yet")


if __name__ == "__main__":
    main()