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

    def test_create_and_list_booking(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "練習",
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
            },
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
