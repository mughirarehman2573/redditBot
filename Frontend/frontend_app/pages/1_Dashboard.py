import streamlit as st
from utils.api_client import api_client



def main():
    st.set_page_config(
        page_title="Dashboard - Reddit Automation",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 Dashboard")
    st.markdown("---")

    # Quick Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Connected Accounts", "0")
    with col2:
        st.metric("Active Schedules", "0")
    with col3:
        st.metric("Total Posts", "0")
    with col4:
        st.metric("Success Rate", "100%")

    # Navigation
    st.subheader("Quick Actions")
    cols = st.columns(3)
    with cols[0]:
        if st.button("➕ Manage Accounts"):
            st.switch_page("pages/2_Accounts.py")
    with cols[1]:
        if st.button("📅 Create Schedule"):
            st.switch_page("pages/3_Scheduling.py")
    with cols[2]:
        if st.button("💬 Content Management"):
            st.switch_page("pages/4_Content.py")


if __name__ == "__main__":
    main()