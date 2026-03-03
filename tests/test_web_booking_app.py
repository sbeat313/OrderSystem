import json
import threading
import time
import unittest
from http.client import HTTPConnection
import web_booking_app
from web_booking_app import BookingWebHandler


class TestWebBookingApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        web_booking_app.manager = web_booking_app.BookingManager()
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

    def setUp(self):
        with web_booking_app.manager_lock:
            web_booking_app.manager._bookings.clear()
            web_booking_app.manager._next_id = 1

    def request(self, method, path, payload=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        body = None
        headers = {}
        if payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")
        conn.close()
        return resp.status, data

    def test_create_and_list_booking(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue": "A館",
                "customer": "王小明",
                "start": "2026-04-01 09:00",
                "end": "2026-04-01 11:00",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["booking_id"], 1)

        status, body = self.request("GET", "/api/bookings")
        self.assertEqual(status, 200)
        items = json.loads(body)
        self.assertEqual(len(items), 1)

    def test_conflict_returns_400(self):
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue": "A館",
                "customer": "王小明",
                "start": "2026-04-01 09:00",
                "end": "2026-04-01 11:00",
            },
        )
        status, _ = self.request(
            "POST",
            "/api/bookings",
            {
                "venue": "A館",
                "customer": "李小華",
                "start": "2026-04-01 10:00",
                "end": "2026-04-01 12:00",
            },
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
