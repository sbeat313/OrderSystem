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
            note="測試備註",
        )
        self.assertEqual(booking.booking_id, 1)
        self.assertEqual(booking.price, 600)
        self.assertEqual(booking.note, "測試備註")
        self.assertTrue(booking.created_at)
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

    def test_update_single_month_rent_updates_related_bookings(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="單月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )

        self.manager.update_booking(
            booking_id=items[0].booking_id,
            venue_id=2,
            customer="王小明-更新",
            purpose="單月租",
            price=650,
            start="2026-04-01 10:00",
            end="2026-04-01 12:00",
            note="整組更新",
        )

        updated = self.manager.list_bookings("2026-04-08")
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0].venue_id, 2)
        self.assertEqual(updated[0].customer, "王小明-更新")
        self.assertEqual(updated[0].purpose, "單月租")
        self.assertEqual(updated[0].price, 650)
        self.assertEqual(updated[0].start_time.strftime("%Y-%m-%d %H:%M"), "2026-04-08 10:00")
        self.assertEqual(updated[0].end_time.strftime("%Y-%m-%d %H:%M"), "2026-04-08 12:00")
        self.assertEqual(updated[0].note, "整組更新")

    def test_update_double_month_rent_updates_related_bookings(self):
        items = self.manager.add_bookings_for_purpose(
            venue_id=1,
            customer="王小明",
            purpose="雙月租",
            price=500,
            start="2026-04-01 09:00",
            end="2026-04-01 11:00",
        )

        self.manager.update_booking(
            booking_id=items[-1].booking_id,
            venue_id=3,
            customer="王小明-雙月",
            purpose="雙月租",
            price=700,
            start="2026-05-27 08:00",
            end="2026-05-27 10:00",
            note="雙月整組更新",
        )

        updated = self.manager.list_bookings("2026-04-01")
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0].venue_id, 3)
        self.assertEqual(updated[0].customer, "王小明-雙月")
        self.assertEqual(updated[0].start_time.strftime("%Y-%m-%d %H:%M"), "2026-04-01 08:00")
        self.assertEqual(updated[0].end_time.strftime("%Y-%m-%d %H:%M"), "2026-04-01 10:00")

    def test_persistence(self):
        self.manager.add_booking(2, "王小明", "2026-04-01 09:00", "2026-04-01 10:00", "臨租")
        manager2 = BookingManager(db_path=f"{self.tmp.name}/test.db")
        self.assertEqual(len(manager2.list_bookings("2026-04-01")), 1)


    def test_manage_string_items(self):
        original = self.manager.list_string_items()
        self.assertGreaterEqual(len(original), 1)

        created = self.manager.add_string_item("測試線", 399)
        self.assertEqual(created.name, "測試線")
        self.assertEqual(created.amount, 399)

        updated = self.manager.update_string_item(created.string_item_id, "測試線2", 420)
        self.assertEqual(updated.name, "測試線2")
        self.assertEqual(updated.amount, 420)

        self.assertTrue(self.manager.delete_string_item(created.string_item_id))

    def test_update_extra_income(self):
        created = self.manager.add_extra_income(
            customer="王小明",
            item="球拍",
            amount=440,
            income_time="2026-04-02 10:00",
            racket_model="YONEX BG-66UM",
            string_tension=34,
        )
        updated = self.manager.update_extra_income(
            income_id=created.income_id,
            customer="王小明",
            item="球拍",
            amount=520,
            income_time="2026-04-03 09:00",
            racket_model="YONEX BG-80",
            string_tension=33,
            payment_status="結清",
            racket_status="客戶取回",
            pickup_date="2026-04-05",
        )
        self.assertEqual(updated.amount, 520)
        self.assertEqual(updated.payment_status, "結清")

    def test_extra_income_pickup_date_normalizes_slash_separator(self):
        created = self.manager.add_extra_income(
            customer="王小明",
            item="球拍",
            amount=440,
            income_time="2026-04-02 10:00",
            racket_model="YONEX BG-66UM",
            string_tension=34,
            pickup_date="2026/04/06",
        )
        self.assertEqual(created.pickup_date, "2026-04-06")

        updated = self.manager.update_extra_income(
            income_id=created.income_id,
            customer="王小明",
            item="球拍",
            amount=520,
            income_time="2026-04-03 09:00",
            racket_model="YONEX BG-80",
            string_tension=33,
            pickup_date="2026/04/07",
        )
        self.assertEqual(updated.pickup_date, "2026-04-07")

        listed = self.manager.list_extra_incomes(start_date="2026-04-01", end_date="2026-04-10")
        self.assertEqual(listed[0].pickup_date, "2026-04-07")



if __name__ == "__main__":
    unittest.main()
