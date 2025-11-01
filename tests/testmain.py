import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from pymain import app

client = TestClient(app)

# ---------------------------
# Test suite for ScoreLive
# ---------------------------
class TestScoreLive(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        """Runs before each test"""
        self.match_id = "test-match-id"
        self.fake_match = {"matchid": self.match_id, "hometeam": "Arsenal", "awayteam": "Chelsea"}

    # ---- 1. Root endpoint ----
    def test_root(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Welcome", response.json()["message"])

    # ---- 2. Create new match (mock DB + auth) ----
    @patch("pymain.check_token", return_value={"sub": "testuser"})
    @patch("pymain.database.execute", new_callable=AsyncMock)
    async def test_create_match(self, mock_execute, mock_token):
        response = client.post(
            "/newmatch",
            params={"Hometeam": "Arsenal", "Awayteam": "Chelsea"},
            headers={"Authorization": "Bearer faketoken"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("matchid", data)
        mock_execute.assert_awaited_once()

    # ---- 3. Goal scored (mock fetch_one + execute) ----
    @patch("pymain.database.fetch_one", new_callable=AsyncMock)
    @patch("pymain.database.execute", new_callable=AsyncMock)
    async def test_goal_scored(self, mock_execute, mock_fetch_one):
        mock_fetch_one.return_value = self.fake_match

        response = client.post(
            "/goalscored",
            params={
                "matchid": self.match_id,
                "minute": 45,
                "scorer": "Saka",
                "team": "Arsenal"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Goal recorded", response.text)
        mock_execute.assert_awaited_once()

    # ---- 4. Aggregate score (mock both queries) ----
    @patch("pymain.database.fetch_one", new_callable=AsyncMock)
    @patch("pymain.database.fetch_all", new_callable=AsyncMock)
    async def test_aggregate_score(self, mock_fetch_all, mock_fetch_one):
        mock_fetch_one.return_value = self.fake_match
        mock_fetch_all.return_value = [
            {"team": "Arsenal", "scorer": "Saka", "minute": 45},
            {"team": "Chelsea", "scorer": "Palmer", "minute": 60}
        ]

        response = client.get(f"/score?matchid={self.match_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Arsenal vs Chelsea", response.text)
