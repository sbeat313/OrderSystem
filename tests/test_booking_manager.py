import tempfile
import unittest

from booking_manager import BookingManager


class BookingManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = BookingManager(db_path=f"{self.tmp.name}/test.db")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_seed_venues(self):
        venues = self.manager.list_venues()
        self.assertEqual(len(venues), 6)
        self.assertEqual(venues[0].name, "1號場")

    def test_seed_purposes(self):
        purposes = self.manager.list_purposes()
        self.assertEqual(
            [p.name for p in purposes],
            ["單月租", "雙月租", "臨租", "月租球友續租", "股東價", "連假專案", "寒暑假專案", "過年專案"],
        )

    def test_manage_venues_and_purposes(self):
        venue = self.manager.add_venue("7號場")
        self.assertEqual(venue.name, "7號場")
        self.manager.update_venue(venue.venue_id, "7號場-更新")
        venues = self.manager.list_venues()
        self.assertIn("7號場-更新", [v.name for v in venues])
        self.assertTrue(self.manager.delete_venue(venue.venue_id))

        purpose = self.manager.add_purpose("測試用途")
        self.assertEqual(purpose.name, "測試用途")
        self.manager.update_purpose(purpose.purpose_id, "測試用途2")
        purposes = self.manager.list_purposes()
        self.assertIn("測試用途2", [p.name for p in purposes])
        self.assertTrue(self.manager.delete_purpose(purpose.purpose_id))

    def test_add_booking_success(self):
        booking = self.manager.add_booking(
            venue_id=1,
            customer="王小明",
            purpose="臨租",
            price=600,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(booking.price, 600)
        self.assertEqual(len(self.manager.list_bookings("2026-04-01")), 1)

    def test_conflict_booking_raises_error(self):
        self.manager.add_booking(1, "王小明", "2026-04-01 09:00", "2026-04-01 11:00", "臨租")
        with self.assertRaises(ValueError):
            self.manager.add_booking(1, "李小華", "2026-04-01 10:30", "2026-04-01 12:00", "臨租")

    def test_add_bookings_for_single_month_rent(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="單月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertEqual(len(items), 5)
        self.assertEqual(items[0].start_time.strftime("%Y-%m-%d"), "2026-04-01")
        self.assertEqual(items[-1].start_time.strftime("%Y-%m-%d"), "2026-04-29")

    def test_add_bookings_for_double_month_rent(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="雙月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertEqual(len(items), 9)
        self.assertEqual(items[-1].start_time.strftime("%Y-%m-%d"), "2026-05-27")

    def test_summarize_fees(self):
        self.manager.add_booking(1, "王小明", "2026-04-01 09:00", "2026-04-01 11:00", "臨租", 500)
        self.manager.add_booking(2, "王小明", "2026-04-02 09:00", "2026-04-02 11:00", "臨租", 700)
        items = self.manager.summarize_fees("2026-04-01", "2026-04-30")
        self.assertEqual(items[0]["customer"], "王小明")
        self.assertEqual(items[0]["total_fee"], 1200)
        filtered = self.manager.summarize_fees("2026-04-01", "2026-04-30", "王小明")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["total_fee"], 1200)

    def test_cancel_single_month_rent_deletes_related_bookings(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="單月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertTrue(self.manager.cancel_booking(items[0].booking_id))
        self.assertEqual(len(self.manager.list_bookings("2026-04-01")), 0)
        self.assertEqual(len(self.manager.list_bookings("2026-04-08")), 0)

    def test_cancel_double_month_rent_deletes_related_bookings(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="雙月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )
        self.assertTrue(self.manager.cancel_booking(items[-1].booking_id))
        self.assertEqual(len(self.manager.list_bookings("2026-04-01")), 0)
        self.assertEqual(len(self.manager.list_bookings("2026-05-27")), 0)

    def test_persistence(self):
        self.manager.add_booking(2, "王小明", "2026-04-01 09:00", "2026-04-01 10:00", "臨租")
        manager2 = BookingManager(db_path=f"{self.tmp.name}/test.db")
        self.assertEqual(len(manager2.list_bookings("2026-04-01")), 1)


    def test_manage_racket_orders_and_stringing_items(self):
        item = self.manager.add_stringing_item("測試線材", 420)
        self.assertEqual(item.amount, 420)
        item = self.manager.update_stringing_item(item.item_id, "測試線材2", 450)
        self.assertEqual(item.name, "測試線材2")

        order = self.manager.add_racket_order(
            customer="王小明",
            racket_model="ARC11",
            status="施做中",
            fee_status="未結清",
            stringing_item_id=item.item_id,
            amount=450,
            received_date="2026-04-01",
            pickup_date="",
            note="急件",
        )
        self.assertEqual(order.status, "施做中")

        order = self.manager.update_racket_order(
            order_id=order.order_id,
            customer="王小明",
            racket_model="ARC11 Pro",
            status="客戶取回",
            fee_status="結清",
            stringing_item_id=item.item_id,
            amount=500,
            received_date="2026-04-01",
            pickup_date="2026-04-03",
            note="完成",
        )
        self.assertEqual(order.fee_status, "結清")

        items = self.manager.summarize_fees("2026-04-01", "2026-04-30", "王小明")
        self.assertEqual(items[0]["racket_fee"], 500)

        self.assertTrue(self.manager.delete_racket_order(order.order_id))
        self.assertTrue(self.manager.delete_stringing_item(item.item_id))

    def test_racket_fee_summary_only_count_settled_with_pickup_date(self):
        base_item = self.manager.list_stringing_items()[0]
        self.manager.add_racket_order("王小明", "A", "客戶取回", "未結清", base_item.item_id, 300, "2026-04-01", "2026-04-02")
        self.manager.add_racket_order("王小明", "B", "客戶取回", "結清", base_item.item_id, 400, "2026-04-01", "")
        self.manager.add_racket_order("王小明", "C", "客戶取回", "結清", base_item.item_id, 500, "2026-04-01", "2026-04-02")
        result = self.manager.summarize_fees("2026-04-01", "2026-04-30", "王小明")
        self.assertEqual(result[0]["racket_count"], 1)
        self.assertEqual(result[0]["racket_fee"], 500)


if __name__ == "__main__":
    unittest.main()
