import requests
import streamlit as st


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
        except:

            return False

    def get(self, endpoint: str):
        try:
            headers = {"Authorization": f"Bearer {st.session_state.get('access_token')}"}
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None


# Global instance
api_client = APIClient()