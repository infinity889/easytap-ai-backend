from rest_framework import status
from rest_framework.test import APITestCase

from .models import TelegramLink, User


class TelegramLinkFlowTests(APITestCase):
    def test_start_reuses_existing_active_code(self):
        payload = {
            "tg_user_id": 123456789,
            "username": "demo_user",
            "full_name": "Demo User",
        }

        first = self.client.post("/api/tg/link/start/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        first_code = first.data["link_code"]
        self.assertTrue(first_code)

        second = self.client.post("/api/tg/link/start/", payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["link_code"], first_code)

    def test_confirm_accepts_code_after_repeated_start_requests(self):
        payload = {
            "tg_user_id": 987654321,
            "username": "repeat_user",
            "full_name": "Repeat User",
        }
        start = self.client.post("/api/tg/link/start/", payload, format="json")
        code = start.data["link_code"]

        repeated = self.client.post("/api/tg/link/start/", payload, format="json")
        self.assertEqual(repeated.data["link_code"], code)

        user = User.objects.create_user(
            email="telegram-link@example.com",
            password="StrongPass123!",
            full_name="Linked User",
        )
        self.client.force_authenticate(user=user)

        confirm = self.client.post("/api/tg/link/confirm/", {"code": code}, format="json")
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm.data, {"linked": True})

        link = TelegramLink.objects.get(tg_user_id=payload["tg_user_id"])
        self.assertEqual(link.user_id, user.id)
        self.assertEqual(link.link_code, "")
