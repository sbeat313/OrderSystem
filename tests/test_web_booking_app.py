import json
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection

import web_booking_app
from booking_manager import BookingManager
from web_booking_app import BookingWebHandler


class TestWebBookingApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        web_booking_app.manager = BookingManager(db_path=f"{cls.tmp.name}/web.db")
        web_booking_app.manager_lock = web_booking_app.Lock()

        class ReusableTCPServer(web_booking_app.ThreadingHTTPServer):
            allow_reuse_address = True

        cls.server = ReusableTCPServer(("127.0.0.1", 0), BookingWebHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)
        cls.tmp.cleanup()

    def setUp(self):
        with web_booking_app.manager_lock:
            for booking in web_booking_app.manager.list_bookings():
                web_booking_app.manager.cancel_booking(booking.booking_id)

    def request(self, method, path, payload=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        body = None
        if payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        content = resp.read().decode("utf-8")
        conn.close()
        return resp.status, content


    def test_get_venues(self):
        status, body = self.request("GET", "/api/venues")
        self.assertEqual(status, 200)
        venues = json.loads(body)
        self.assertEqual(len(venues), 6)

    def test_get_purposes(self):
        status, body = self.request("GET", "/api/purposes")
        self.assertEqual(status, 200)
        purposes = json.loads(body)
        self.assertIn({"purpose_id": 1, "name": "單月租"}, purposes)

    def test_options_page_exists(self):
        status, body = self.request("GET", "/options")
        self.assertEqual(status, 200)
        self.assertIn("場地 / 用途 管理", body)

    def test_export_endpoint_removed(self):
        status, _ = self.request("GET", "/api/export?format=png&date=2026-04-01&role=user")
        self.assertEqual(status, 404)

    def test_create_and_list_booking(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "臨租",
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["venue_name"], "1號場")

        status, body = self.request("GET", "/api/bookings?date=2026-04-01")
        self.assertEqual(status, 200)
        items = json.loads(body)
        self.assertEqual(len(items), 1)

    def test_conflict_returns_400(self):
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
                "purpose": "臨租",
            },
        )
        status, _ = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "李小華",
                "start": "2026-04-01 19:00",
                "end": "2026-04-01 21:00",
                "purpose": "臨租",
            },
        )
        self.assertEqual(status, 400)

    def test_admin_login(self):
        status, _ = self.request("POST", "/api/admin/login", {"password": "wrong"})
        self.assertEqual(status, 401)

        status, body = self.request("POST", "/api/admin/login", {"password": "admin123"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_manage_venues_and_purposes_via_api(self):
        status, body = self.request(
            "POST",
            "/api/venues",
            {"admin_password": "admin123", "name": "7號場"},
        )
        self.assertEqual(status, 201)
        venue_id = json.loads(body)["venue_id"]

        status, _ = self.request(
            "PUT",
            "/api/venues",
            {"admin_password": "admin123", "venue_id": venue_id, "name": "7號場-更新"},
        )
        self.assertEqual(status, 200)

        status, _ = self.request(
            "DELETE",
            "/api/venues",
            {"admin_password": "admin123", "venue_id": venue_id},
        )
        self.assertEqual(status, 200)

        status, body = self.request(
            "POST",
            "/api/purposes",
            {"admin_password": "admin123", "name": "測試用途"},
        )
        self.assertEqual(status, 201)
        purpose_id = json.loads(body)["purpose_id"]

        status, _ = self.request(
            "PUT",
            "/api/purposes",
            {"admin_password": "admin123", "purpose_id": purpose_id, "name": "測試用途2"},
        )
        self.assertEqual(status, 200)

        status, _ = self.request(
            "DELETE",
            "/api/purposes",
            {"admin_password": "admin123", "purpose_id": purpose_id},
        )
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
