import streamlit as st
import requests



class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def login(self, username: str, password: str) -> bool:
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                data={"username": username, "password": password}
            )
            if response.status_code == 200:
                token_data = response.json()
                st.session_state.access_token = token_data["access_token"]
                st.session_state.user_authenticated = True
                st.session_state.username = username
                return True
            return False
        except Exception as e:
            st.error(f"Login request failed: {e}")
            return False

    def get(self, endpoint: str):
        try:
            token = st.session_state.get("access_token")
            if not token:
                return None
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"API request failed: {e}")
            return None


api_client = APIClient()

def home_page():
    st.set_page_config(
        page_title="Reddit Automation - Login",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="collapsed"
    )

    hide_sidebar = """
        <style>
            section[data-testid="stSidebar"] { display: none; }
        </style>
    """
    st.markdown(hide_sidebar, unsafe_allow_html=True)

    if st.session_state.get("user_authenticated"):
        st.success("Already Logged In! Redirecting...")
        st.page_link("?page=dashboard", label="Go to Dashboard", icon="📊")
        return

    st.title("🤖 Reddit Automation")
    st.markdown("---")

    with st.form("login_form"):
        st.subheader("Login to Your Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            if api_client.login(username, password):
                st.success("Login successful!")
                st.session_state.current_page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials")


def dashboard_page():
    st.set_page_config(
        page_title="Dashboard - Reddit Automation",
        page_icon="📊",
        layout="wide"
    )

    if not st.session_state.get("user_authenticated"):
        st.warning("Please login first")
        st.page_link("?page=home", label="Go to Login", icon="🔐")
        st.stop()

    with st.sidebar:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("Logged out successfully!")
            st.session_state.current_page = "home"
            st.rerun()

    st.title(f"📊 Welcome, {st.session_state.username}!")
    st.markdown("---")

    # Quick Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Connected Accounts", "0")
    col2.metric("Active Schedules", "0")
    col3.metric("Total Posts", "0")
    col4.metric("Success Rate", "100%")

    # Quick Actions
    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    if col1.button("➕ Manage Accounts"):
        st.session_state.current_page = "accounts"
        st.rerun()
    if col2.button("📅 Create Schedule"):
        st.session_state.current_page = "scheduling"
        st.rerun()
    if col3.button("💬 Content Management"):
        st.session_state.current_page = "content"
        st.rerun()


def accounts_page():
    st.set_page_config(
        page_title="Manage Accounts - Reddit Automation",
        page_icon="👥",
        layout="wide"
    )

    if not st.session_state.get("user_authenticated"):
        st.warning("Please login first")
        st.page_link("?page=home", label="Go to Login", icon="🔐")
        st.stop()

    with st.sidebar:
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.success("Logged out successfully!")
            st.session_state.current_page = "home"
            st.rerun()

        if st.button("⬅️ Back to Dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.title("👥 Manage Reddit Accounts")
    st.markdown("---")

    # Connect New Account
    if st.button("🔗 Connect New Reddit Account"):
        token = st.session_state.get("access_token")
        if token:
            auth_url = f"http://localhost:8000/api/v1/auth/reddit/connect?token={token}"
            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
            st.info("Redirecting to Reddit authentication...")
        else:
            st.error("Please login first!")

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


# ------------------ Router ------------------ #
def main():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    page = st.session_state.current_page
    if page == "home":
        home_page()
    elif page == "dashboard":
        dashboard_page()
    elif page == "accounts":
        accounts_page()
    else:
        home_page()


if __name__ == "__main__":
    main()
