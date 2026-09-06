import unittest
import os
from unittest.mock import patch

from flask_jwt_extended import create_access_token

os.environ["SMART_MATCHMAKER_DATABASE_URI"] = "sqlite://"

from app import app, db
from models import Preferences, User


class ApiMatchesTestCase(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            JWT_SECRET_KEY="test-secret-that-is-at-least-32-bytes-long"
        )

        self.context = app.app_context()
        self.context.push()
        db.drop_all()
        db.create_all()

        self.user = User(
            first_name="Current",
            last_name="Student",
            email="current@example.com",
            password="unused",
            is_banned=False
        )
        self.candidate = User(
            first_name="Matched",
            last_name="Student",
            email="matched@example.com",
            password="unused",
            is_banned=False
        )
        db.session.add_all([self.user, self.candidate])
        db.session.flush()

        self.user.preferences = self._preference(self.user.id, "111")
        self.candidate.preferences = self._preference(self.candidate.id, "222")
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @staticmethod
    def _preference(user_id, phone):
        return Preferences(
            user_id=user_id,
            age=24,
            gender="female",
            phone=phone,
            country_code="+963",
            gpa=3.5,
            program="ITE",
            semester="F24",
            academic_year=4,
            commitment_level=4
        )

    def _authorization(self, user_id=None):
        token = create_access_token(
            identity=str(user_id or self.user.id)
        )
        return {"Authorization": f"Bearer {token}"}

    def test_requires_jwt(self):
        response = self.client.get("/api/matches")
        self.assertEqual(response.status_code, 401)

    @patch("app.find_ml_matches")
    def test_returns_ranked_match_json(self, find_matches_mock):
        find_matches_mock.return_value = [
            (self.candidate.preferences, 0.8734)
        ]

        response = self.client.get(
            "/api/matches",
            headers=self._authorization()
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["matches"][0]["user_id"], self.candidate.id)
        self.assertEqual(body["matches"][0]["compatibility_percent"], 87.3)
        find_matches_mock.assert_called_once()

    def test_rejects_user_without_preferences(self):
        no_preferences_user = User(
            first_name="New",
            last_name="Student",
            email="new@example.com",
            password="unused",
            is_banned=False
        )
        db.session.add(no_preferences_user)
        db.session.commit()

        response = self.client.get(
            "/api/matches",
            headers=self._authorization(no_preferences_user.id)
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
