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
            for income in web_booking_app.manager.list_extra_incomes():
                web_booking_app.manager.delete_extra_income(income.income_id)

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
        self.assertIn({"purpose_id": 1, "name": "單月租", "price": 0.0}, purposes)

    def test_homepage_helper_text_removed(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertNotIn("在欲新增的「場地/時段空白格」雙擊可快速新增", body)
        self.assertNotIn("只有通過管理員驗證後可新增預約", body)

    def test_homepage_booking_modal_shows_validation_and_error_area(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('id="booking-modal-msg"', body)
        self.assertIn("已登入（點我登出）", body)
        self.assertIn("booking_admin_password", body)
        self.assertIn("booking_admin_expires_at", body)
        self.assertIn("DEFAULT_ADMIN_SESSION_TTL_MS", body)
        self.assertIn('場地（可複選）', body)
        self.assertIn('multiple size="6"', body)
        self.assertNotIn('id="view-mode"', body)
        self.assertNotIn('顯示模式', body)
        self.assertIn('renderWeekly(weekData, date, 7, document.getElementById(\'grid-week-1\'), 0);', body)
        self.assertIn('renderWeekly(weekData, date, 7, document.getElementById(\'grid-week-2\'), 7);', body)
        self.assertIn('booking-pill', body)
        self.assertIn('const week1Label = formatWeekSectionLabel(date, 0);', body)
        self.assertIn('const week2Label = formatWeekSectionLabel(date, 7);', body)
        self.assertIn('availability-pill', body)
        self.assertIn('const daysPerRow = isAdmin ? 2 : 7;', body)
        self.assertIn("text = '◉ 預約中';", body)
        self.assertIn("text = '🔒 已滿';", body)

    def test_options_page_exists(self):
        status, body = self.request("GET", "/options")
        self.assertEqual(status, 200)
        self.assertIn("系統設定", body)
        self.assertIn("登入時效(分鐘)", body)
        self.assertIn("更新管理員密碼", body)

    def test_purposes_page_exists(self):
        status, body = self.request("GET", "/purposes")
        self.assertEqual(status, 200)
        self.assertIn("用途設定", body)
        self.assertIn("價格", body)
        self.assertIn("booking_admin_session_ttl_ms", body)

    def test_reports_page_exists(self):
        status, body = self.request("GET", "/reports")
        self.assertEqual(status, 200)
        self.assertIn("預約費用統計", body)
        self.assertIn("預約收入明細", body)
        self.assertIn("額外收入明細", body)
        self.assertIn("匯出 Excel", body)
        self.assertIn("新增時間", body)

    def test_string_items_page_exists(self):
        status, body = self.request("GET", "/string-items")
        self.assertEqual(status, 200)
        self.assertIn("穿線項目設定", body)

    def test_extra_income_page_exists(self):
        status, body = self.request("GET", "/extra-income")
        self.assertEqual(status, 200)
        self.assertIn("額外收入登記", body)
        self.assertIn("box-sizing: border-box", body)
        self.assertIn("booking_admin_password", body)
        self.assertIn("booking_admin_expires_at", body)
        self.assertIn("DEFAULT_ADMIN_SESSION_TTL_MS", body)
        self.assertIn("穿線項目", body)
        self.assertIn("磅數", body)
        self.assertIn("穿線項目設定", body)
        self.assertIn('<select id="income-racket-model">', body)

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
                "price": 800,
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
                "note": "靠窗",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["venue_name"], "1號場")
        self.assertEqual(created["price"], 800)
        self.assertEqual(created["note"], "靠窗")
        self.assertTrue(created["created_at"])

        status, body = self.request("GET", "/api/bookings?date=2026-04-01")
        self.assertEqual(status, 200)
        items = json.loads(body)
        self.assertEqual(len(items), 1)


    def test_create_booking_with_multiple_venues(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_ids": [1, 2],
                "customer": "多場地測試",
                "purpose": "臨租",
                "price": 900,
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["created_count"], 2)

        status, body = self.request("GET", "/api/bookings?date=2026-04-01")
        self.assertEqual(status, 200)
        items = json.loads(body)
        self.assertEqual(len(items), 2)
        self.assertEqual({item["venue_id"] for item in items}, {1, 2})

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

    def test_booking_update_and_delete_with_admin_password(self):
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
        booking_id = json.loads(body)["booking_id"]

        status, body = self.request(
            "PUT",
            "/api/bookings",
            {
                "admin_password": "admin123",
                "booking_id": booking_id,
                "venue_id": 2,
                "customer": "王小明-改",
                "purpose": "臨租",
                "price": 1200,
                "start": "2026-04-01 19:00",
                "end": "2026-04-01 21:00",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["venue_id"], 2)
        self.assertEqual(json.loads(body)["price"], 1200)

        status, _ = self.request(
            "DELETE",
            "/api/bookings",
            {"admin_password": "admin123", "booking_id": booking_id},
        )
        self.assertEqual(status, 200)

    def test_monthly_rent_auto_fills_same_timeslot(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "單月租",
                "price": 500,
                "start": "2026-04-01 09:00",
                "end": "2026-04-01 11:00",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["created_count"], 5)

        status, body = self.request("GET", "/api/bookings")
        self.assertEqual(status, 200)
        items = json.loads(body)
        self.assertEqual(len(items), 5)

    def test_double_monthly_rent_auto_fills_until_next_month_end(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "雙月租",
                "price": 500,
                "start": "2026-04-01 09:00",
                "end": "2026-04-01 11:00",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["created_count"], 9)

    def test_delete_monthly_rent_removes_related_bookings(self):
        status, body = self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "單月租",
                "price": 500,
                "start": "2026-04-01 09:00",
                "end": "2026-04-01 11:00",
            },
        )
        self.assertEqual(status, 201)
        booking_id = json.loads(body)["booking_id"]

        status, _ = self.request(
            "DELETE",
            "/api/bookings",
            {"admin_password": "admin123", "booking_id": booking_id},
        )
        self.assertEqual(status, 200)

        status, body = self.request("GET", "/api/bookings")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)), 0)

    def test_fee_report_endpoint(self):
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "臨租",
                "price": 500,
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
            },
        )
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 2,
                "customer": "王小明",
                "purpose": "臨租",
                "price": 700,
                "start": "2026-04-02 18:00",
                "end": "2026-04-02 20:00",
            },
        )
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 3,
                "customer": "李小華",
                "purpose": "臨租",
                "price": 400,
                "start": "2026-04-03 18:00",
                "end": "2026-04-03 19:00",
            },
        )

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
            },
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["grand_total"], 1600)
        self.assertEqual(data["items"][0]["customer"], "王小明")
        self.assertTrue(any(row["purpose"] == "臨租" for row in data["booking_records"]))
        self.assertTrue(all("start_time" in row and "end_time" in row for row in data["booking_records"]))
        self.assertTrue(all("created_at" in row for row in data["booking_records"]))

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "customer": "王小明",
            },
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["grand_total"], 1200)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["customer"], "王小明")

    def test_fee_report_pagination_keeps_grand_totals(self):
        for i in range(25):
            day = (i % 28) + 1
            self.request(
                "POST",
                "/api/bookings",
                {
                    "venue_id": 1,
                    "customer": f"顧客{i:02d}",
                    "purpose": "臨租",
                    "price": 100,
                    "start": f"2026-04-{day:02d} 18:00",
                    "end": f"2026-04-{day:02d} 19:00",
                },
            )

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "booking_page": 1,
            },
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(len(data["booking_records"]), 10)
        self.assertEqual(data["booking_total_records"], 25)
        self.assertEqual(data["booking_total_pages"], 3)
        self.assertEqual(data["booking_page"], 1)
        self.assertEqual(data["booking_grand_total"], 2500)
        self.assertEqual(data["grand_total"], 2500)

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "booking_page": 3,
            },
        )
        self.assertEqual(status, 200)
        page_two = json.loads(body)
        self.assertEqual(len(page_two["booking_records"]), 5)
        self.assertEqual(page_two["booking_page"], 3)
        self.assertEqual(page_two["booking_grand_total"], 2500)
        self.assertEqual(page_two["grand_total"], 2500)


    def test_fee_report_export_csv(self):
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "臨租",
                "price": 500,
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
            },
        )
        self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-02 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 480,
                "racket_model": "YONEX BG-65",
                "string_tension": 32,
                "payment_status": "結清",
                "pickup_date": "2026-04-16",
            },
        )

        status, body = self.request(
            "POST",
            "/api/reports/fees/export",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "customer": "王小明",
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("<h3>預約收入明細</h3>", body)
        self.assertIn("<th>用途</th>", body)
        self.assertIn("<th>新增時間</th>", body)
        self.assertIn("<th>備註</th>", body)
        self.assertIn("總計（預約）：$500｜總計（額外收入）：$480｜整體總計：$980", body)

    def test_extra_income_in_report(self):
        self.request(
            "POST",
            "/api/bookings",
            {
                "venue_id": 1,
                "customer": "王小明",
                "purpose": "臨租",
                "price": 500,
                "start": "2026-04-01 18:00",
                "end": "2026-04-01 20:00",
            },
        )

        status, body = self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-02 10:00",
                "customer": "王小明",
                "item": "球具寄賣",
                "amount": 300,
                "note": "測試",
            },
        )
        self.assertEqual(status, 201)

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "customer": "王小明",
            },
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["booking_grand_total"], 500)
        self.assertEqual(data["extra_income_grand_total"], 300)
        self.assertEqual(data["grand_total"], 800)
        self.assertEqual(len(data["extra_income_records"]), 1)
        self.assertEqual(data["extra_income_records"][0]["item"], "球具寄賣")

    def test_extra_income_racket_fields(self):
        status, body = self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-02 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 440,
                "note": "白色線",
                "contact_phone": "0912222333",
                "racket_model": "YONEX BG-66UM",
                "string_tension": 34,
                "payment_status": "尚未付款",
                "racket_status": "施做中",
                "pickup_date": "2026-04-14",
            },
        )
        self.assertEqual(status, 201)
        created = json.loads(body)
        self.assertEqual(created["racket_model"], "YONEX BG-66UM")
        self.assertEqual(created["string_tension"], 34)

        status, body = self.request(
            "POST",
            "/api/extra-incomes/query",
            {"admin_password": "admin123", "customer": "王小明"},
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(len(data["items"]), 1)
        row = data["items"][0]
        self.assertEqual(row["contact_phone"], "0912222333")
        self.assertEqual(row["payment_status"], "尚未付款")

    def test_update_and_delete_extra_income_via_api(self):
        status, body = self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-02 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 440,
                "racket_model": "YONEX BG-66UM",
                "string_tension": 34,
            },
        )
        self.assertEqual(status, 201)
        income_id = json.loads(body)["income_id"]

        status, body = self.request(
            "PUT",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_id": income_id,
                "income_time": "2026-04-03 11:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 500,
                "racket_model": "YONEX BG-80",
                "string_tension": 33,
                "payment_status": "結清",
                "racket_status": "客戶取回",
                "pickup_date": "2026-04-05",
            },
        )
        self.assertEqual(status, 200)
        updated = json.loads(body)
        self.assertEqual(updated["amount"], 500)
        self.assertEqual(updated["racket_model"], "YONEX BG-80")

        status, _ = self.request(
            "DELETE",
            "/api/extra-incomes",
            {"admin_password": "admin123", "income_id": income_id},
        )
        self.assertEqual(status, 200)

    def test_racket_income_requires_paid_and_pickup_to_count_in_report(self):
        self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-02 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 440,
                "racket_model": "YONEX BG-66UM",
                "string_tension": 34,
                "payment_status": "尚未付款",
                "pickup_date": "2026-04-14",
            },
        )
        self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-03 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 460,
                "racket_model": "YONEX BG-80",
                "string_tension": 33,
                "payment_status": "結清",
                "pickup_date": "",
            },
        )
        self.request(
            "POST",
            "/api/extra-incomes",
            {
                "admin_password": "admin123",
                "income_time": "2026-04-04 10:00",
                "customer": "王小明",
                "item": "球拍",
                "amount": 480,
                "racket_model": "YONEX BG-65",
                "string_tension": 32,
                "payment_status": "結清",
                "pickup_date": "2026-04-16",
            },
        )

        status, body = self.request(
            "POST",
            "/api/reports/fees",
            {
                "admin_password": "admin123",
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "customer": "王小明",
            },
        )
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["extra_income_grand_total"], 480)
        self.assertEqual(len(data["extra_income_records"]), 1)
        self.assertEqual(data["extra_income_records"][0]["pickup_date"], "2026-04-16")


    def test_manage_string_items_via_api(self):
        status, body = self.request(
            "POST",
            "/api/string-items",
            {"admin_password": "admin123", "name": "測試線", "amount": 399},
        )
        self.assertEqual(status, 201)
        item_id = json.loads(body)["string_item_id"]

        status, body = self.request(
            "POST",
            "/api/string-items/query",
            {"admin_password": "admin123"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(any(row["name"] == "測試線" for row in json.loads(body)["items"]))

        status, body = self.request(
            "PUT",
            "/api/string-items",
            {"admin_password": "admin123", "string_item_id": item_id, "name": "測試線2", "amount": 420},
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["name"], "測試線2")

        status, _ = self.request(
            "DELETE",
            "/api/string-items",
            {"admin_password": "admin123", "string_item_id": item_id},
        )
        self.assertEqual(status, 200)

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
