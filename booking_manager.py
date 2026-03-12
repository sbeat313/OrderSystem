from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

TIME_FORMAT = "%Y-%m-%d %H:%M"
DEFAULT_DB_PATH = "booking.db"


@dataclass
class Venue:
    venue_id: int
    name: str


@dataclass
class Purpose:
    purpose_id: int
    name: str


@dataclass
class Booking:
    booking_id: int
    venue_id: int
    venue_name: str
    customer: str
    purpose: str
    price: float
    start_time: datetime
    end_time: datetime


RACKET_STATUSES = ["待取回加工", "施做中", "辦公室未取", "客戶取回"]
RACKET_FEE_STATUSES = ["未結清", "結清"]


@dataclass
class StringingItem:
    item_id: int
    name: str
    amount: float


@dataclass
class RacketOrder:
    order_id: int
    customer: str
    racket_model: str
    status: str
    fee_status: str
    stringing_item_id: int
    stringing_item_name: str
    amount: float
    received_date: str
    pickup_date: str
    note: str


class BookingManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS venues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS purposes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venue_id INTEGER NOT NULL,
                    customer TEXT NOT NULL,
                    purpose TEXT NOT NULL DEFAULT '',
                    price REAL NOT NULL DEFAULT 0,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    FOREIGN KEY (venue_id) REFERENCES venues(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stringing_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS racket_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT NOT NULL,
                    racket_model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    fee_status TEXT NOT NULL,
                    stringing_item_id INTEGER NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    received_date TEXT NOT NULL,
                    pickup_date TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (stringing_item_id) REFERENCES stringing_items(id)
                )
                """
            )
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(bookings)").fetchall()]
            if "price" not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN price REAL NOT NULL DEFAULT 0")
            if "rental_group_id" not in columns:
                conn.execute("ALTER TABLE bookings ADD COLUMN rental_group_id TEXT")
            count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO venues(name) VALUES (?)",
                    [(f"{index}號場",) for index in range(1, 7)],
                )

            purpose_count = conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]
            if purpose_count == 0:
                conn.executemany(
                    "INSERT INTO purposes(name) VALUES (?)",
                    [
                        ("單月租",),
                        ("雙月租",),
                        ("臨租",),
                        ("月租球友續租",),
                        ("股東價",),
                        ("連假專案",),
                        ("寒暑假專案",),
                        ("過年專案",),
                    ],
                )
            item_count = conn.execute("SELECT COUNT(*) FROM stringing_items").fetchone()[0]
            if item_count == 0:
                conn.executemany(
                    "INSERT INTO stringing_items(name, amount) VALUES (?, ?)",
                    [
                        ("BG65 穿線", 350),
                        ("NBG95 穿線", 500),
                    ],
                )

    def list_stringing_items(self) -> List[StringingItem]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, amount FROM stringing_items ORDER BY id").fetchall()
        return [
            StringingItem(item_id=row["id"], name=row["name"], amount=float(row["amount"] or 0))
            for row in rows
        ]

    def add_stringing_item(self, name: str, amount: float) -> StringingItem:
        item_name = name.strip()
        if not item_name:
            raise ValueError("穿線項目名稱不可為空")
        fee = self._parse_price(amount)
        try:
            with self._connect() as conn:
                cur = conn.execute("INSERT INTO stringing_items(name, amount) VALUES (?, ?)", (item_name, fee))
            return StringingItem(item_id=cur.lastrowid, name=item_name, amount=fee)
        except sqlite3.IntegrityError as exc:
            raise ValueError("穿線項目名稱不可重複") from exc

    def update_stringing_item(self, item_id: int, name: str, amount: float) -> StringingItem:
        item_name = name.strip()
        if not item_name:
            raise ValueError("穿線項目名稱不可為空")
        fee = self._parse_price(amount)
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE stringing_items SET name = ?, amount = ? WHERE id = ?",
                    (item_name, fee, item_id),
                )
                if cur.rowcount == 0:
                    raise ValueError("穿線項目不存在")
            return StringingItem(item_id=item_id, name=item_name, amount=fee)
        except sqlite3.IntegrityError as exc:
            raise ValueError("穿線項目名稱不可重複") from exc

    def delete_stringing_item(self, item_id: int) -> bool:
        with self._connect() as conn:
            used = conn.execute("SELECT COUNT(*) FROM racket_orders WHERE stringing_item_id = ?", (item_id,)).fetchone()[0]
            if used > 0:
                raise ValueError("此穿線項目已有球拍資料，無法刪除")
            cur = conn.execute("DELETE FROM stringing_items WHERE id = ?", (item_id,))
            return cur.rowcount > 0

    def list_racket_orders(self) -> List[RacketOrder]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.customer, r.racket_model, r.status, r.fee_status, r.stringing_item_id,
                       s.name AS stringing_item_name, r.amount, r.received_date, r.pickup_date, r.note
                FROM racket_orders r
                JOIN stringing_items s ON s.id = r.stringing_item_id
                ORDER BY r.received_date DESC, r.id DESC
                """
            ).fetchall()
        return [
            RacketOrder(
                order_id=row["id"],
                customer=row["customer"],
                racket_model=row["racket_model"],
                status=row["status"],
                fee_status=row["fee_status"],
                stringing_item_id=row["stringing_item_id"],
                stringing_item_name=row["stringing_item_name"],
                amount=float(row["amount"] or 0),
                received_date=row["received_date"],
                pickup_date=row["pickup_date"],
                note=row["note"],
            )
            for row in rows
        ]

    def add_racket_order(self, customer: str, racket_model: str, status: str, fee_status: str, stringing_item_id: int, amount: float, received_date: str, pickup_date: str = "", note: str = "") -> RacketOrder:
        customer_name = customer.strip()
        if not customer_name:
            raise ValueError("客戶名稱不可為空")
        self._validate_racket_statuses(status, fee_status)
        self._validate_date(received_date, "收件日期")
        if pickup_date:
            self._validate_date(pickup_date, "客戶取回日")
        fee = self._parse_price(amount)
        with self._connect() as conn:
            item = conn.execute("SELECT id, name FROM stringing_items WHERE id = ?", (stringing_item_id,)).fetchone()
            if item is None:
                raise ValueError("穿線項目不存在")
            cur = conn.execute(
                """
                INSERT INTO racket_orders(customer, racket_model, status, fee_status, stringing_item_id, amount, received_date, pickup_date, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (customer_name, racket_model.strip(), status, fee_status, stringing_item_id, fee, received_date, pickup_date.strip(), note.strip()),
            )
            order_id = cur.lastrowid
        return RacketOrder(order_id, customer_name, racket_model.strip(), status, fee_status, item["id"], item["name"], fee, received_date, pickup_date.strip(), note.strip())

    def update_racket_order(self, order_id: int, customer: str, racket_model: str, status: str, fee_status: str, stringing_item_id: int, amount: float, received_date: str, pickup_date: str = "", note: str = "") -> RacketOrder:
        customer_name = customer.strip()
        if not customer_name:
            raise ValueError("客戶名稱不可為空")
        self._validate_racket_statuses(status, fee_status)
        self._validate_date(received_date, "收件日期")
        if pickup_date:
            self._validate_date(pickup_date, "客戶取回日")
        fee = self._parse_price(amount)
        with self._connect() as conn:
            item = conn.execute("SELECT id, name FROM stringing_items WHERE id = ?", (stringing_item_id,)).fetchone()
            if item is None:
                raise ValueError("穿線項目不存在")
            cur = conn.execute(
                """
                UPDATE racket_orders
                SET customer = ?, racket_model = ?, status = ?, fee_status = ?, stringing_item_id = ?, amount = ?, received_date = ?, pickup_date = ?, note = ?
                WHERE id = ?
                """,
                (customer_name, racket_model.strip(), status, fee_status, stringing_item_id, fee, received_date, pickup_date.strip(), note.strip(), order_id),
            )
            if cur.rowcount == 0:
                raise ValueError("球拍資料不存在")
        return RacketOrder(order_id, customer_name, racket_model.strip(), status, fee_status, item["id"], item["name"], fee, received_date, pickup_date.strip(), note.strip())

    def delete_racket_order(self, order_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM racket_orders WHERE id = ?", (order_id,))
            return cur.rowcount > 0

    def list_venues(self) -> List[Venue]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name FROM venues ORDER BY id").fetchall()
        return [Venue(venue_id=row["id"], name=row["name"]) for row in rows]

    def add_venue(self, name: str) -> Venue:
        venue_name = name.strip()
        if not venue_name:
            raise ValueError("場地名稱不可為空")
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO venues(name) VALUES (?)", (venue_name,))
                venue_id = cursor.lastrowid
            return Venue(venue_id=venue_id, name=venue_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("場地名稱不可重複") from exc

    def update_venue(self, venue_id: int, name: str) -> Venue:
        venue_name = name.strip()
        if not venue_name:
            raise ValueError("場地名稱不可為空")
        try:
            with self._connect() as conn:
                cur = conn.execute("UPDATE venues SET name = ? WHERE id = ?", (venue_name, venue_id))
                if cur.rowcount == 0:
                    raise ValueError("場地不存在")
            return Venue(venue_id=venue_id, name=venue_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("場地名稱不可重複") from exc

    def delete_venue(self, venue_id: int) -> bool:
        with self._connect() as conn:
            used = conn.execute("SELECT COUNT(*) FROM bookings WHERE venue_id = ?", (venue_id,)).fetchone()[0]
            if used > 0:
                raise ValueError("此場地已有預約資料，無法刪除")
            cur = conn.execute("DELETE FROM venues WHERE id = ?", (venue_id,))
            return cur.rowcount > 0

    def list_purposes(self) -> List[Purpose]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name FROM purposes ORDER BY id").fetchall()
        return [Purpose(purpose_id=row["id"], name=row["name"]) for row in rows]

    def add_purpose(self, name: str) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO purposes(name) VALUES (?)", (purpose_name,))
                purpose_id = cursor.lastrowid
            return Purpose(purpose_id=purpose_id, name=purpose_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def update_purpose(self, purpose_id: int, name: str) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        try:
            with self._connect() as conn:
                cur = conn.execute("UPDATE purposes SET name = ? WHERE id = ?", (purpose_name, purpose_id))
                if cur.rowcount == 0:
                    raise ValueError("用途不存在")
            return Purpose(purpose_id=purpose_id, name=purpose_name)
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def delete_purpose(self, purpose_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT name FROM purposes WHERE id = ?", (purpose_id,)).fetchone()
            if row is None:
                return False
            purpose_name = row["name"]
            used = conn.execute("SELECT COUNT(*) FROM bookings WHERE purpose = ?", (purpose_name,)).fetchone()[0]
            if used > 0:
                raise ValueError("此用途已有預約資料，無法刪除")
            cur = conn.execute("DELETE FROM purposes WHERE id = ?", (purpose_id,))
            return cur.rowcount > 0

    def add_booking(
        self,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
        price: float = 0,
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        with self._connect() as conn:
            venue = conn.execute(
                "SELECT id, name FROM venues WHERE id = ?", (venue_id,)
            ).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_name = purpose.strip()
            if not purpose_name:
                raise ValueError("用途不可為空")
            purpose_row = conn.execute(
                "SELECT 1 FROM purposes WHERE name = ?",
                (purpose_name,),
            ).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            conflict = conn.execute(
                """
                SELECT b.id, b.start_time, b.end_time
                FROM bookings b
                WHERE b.venue_id = ?
                  AND b.start_time < ?
                  AND b.end_time > ?
                LIMIT 1
                """,
                (
                    venue_id,
                    end_time.strftime(TIME_FORMAT),
                    start_time.strftime(TIME_FORMAT),
                ),
            ).fetchone()
            if conflict:
                raise ValueError(
                    f"時段衝突：{venue['name']} 已有預約 "
                    f"({conflict['start_time']} - {conflict['end_time']})"
                )

            cursor = conn.execute(
                """
                INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    booking_price,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                    None,
                ),
            )
            booking_id = cursor.lastrowid

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            price=booking_price,
            start_time=start_time,
            end_time=end_time,
        )

    def add_bookings_for_purpose(
        self,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
        price: float = 0,
    ) -> List[Booking]:
        purpose_name = purpose.strip()
        if purpose_name not in {"單月租", "雙月租"}:
            return [self.add_booking(venue_id, customer, start, end, purpose, price)]

        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        duration = end_time - start_time
        period_end = self._month_end(start_time)
        if purpose_name == "雙月租":
            period_end = self._month_end(self._next_month_start(start_time))

        slot_starts: List[datetime] = []
        cursor = start_time
        while cursor.date() <= period_end.date():
            slot_starts.append(cursor)
            cursor += timedelta(days=7)

        with self._connect() as conn:
            group_id = str(uuid.uuid4())
            venue = conn.execute("SELECT id, name FROM venues WHERE id = ?", (venue_id,)).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_row = conn.execute("SELECT 1 FROM purposes WHERE name = ?", (purpose_name,)).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            for slot_start in slot_starts:
                slot_end = slot_start + duration
                conflict = conn.execute(
                    """
                    SELECT b.id, b.start_time, b.end_time
                    FROM bookings b
                    WHERE b.venue_id = ?
                      AND b.start_time < ?
                      AND b.end_time > ?
                    LIMIT 1
                    """,
                    (
                        venue_id,
                        slot_end.strftime(TIME_FORMAT),
                        slot_start.strftime(TIME_FORMAT),
                    ),
                ).fetchone()
                if conflict:
                    raise ValueError(
                        f"時段衝突：{venue['name']} 已有預約 "
                        f"({conflict['start_time']} - {conflict['end_time']})"
                    )

            created: List[Booking] = []
            for slot_start in slot_starts:
                slot_end = slot_start + duration
                cursor = conn.execute(
                    """
                    INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venue_id,
                        customer.strip(),
                        purpose_name,
                        booking_price,
                        slot_start.strftime(TIME_FORMAT),
                        slot_end.strftime(TIME_FORMAT),
                        group_id,
                    ),
                )
                created.append(
                    Booking(
                        booking_id=cursor.lastrowid,
                        venue_id=venue["id"],
                        venue_name=venue["name"],
                        customer=customer.strip(),
                        purpose=purpose_name,
                        price=booking_price,
                        start_time=slot_start,
                        end_time=slot_end,
                    )
                )

        return created

    def cancel_booking(self, booking_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, venue_id, customer, purpose, start_time, end_time, rental_group_id
                FROM bookings
                WHERE id = ?
                """,
                (booking_id,),
            ).fetchone()
            if row is None:
                return False

            if row["purpose"] in {"單月租", "雙月租"}:
                if row["rental_group_id"]:
                    cur = conn.execute(
                        "DELETE FROM bookings WHERE rental_group_id = ?",
                        (row["rental_group_id"],),
                    )
                    return cur.rowcount > 0

                start_time = datetime.strptime(row["start_time"], TIME_FORMAT)
                period_end = self._month_end(start_time)
                if row["purpose"] == "雙月租":
                    period_end = self._month_end(self._next_month_start(start_time))

                cur = conn.execute(
                    """
                    DELETE FROM bookings
                    WHERE venue_id = ?
                      AND customer = ?
                      AND purpose = ?
                      AND date(start_time) BETWEEN date(?) AND date(?)
                      AND time(start_time) = time(?)
                      AND time(end_time) = time(?)
                    """,
                    (
                        row["venue_id"],
                        row["customer"],
                        row["purpose"],
                        start_time.strftime("%Y-%m-%d"),
                        period_end.strftime("%Y-%m-%d"),
                        row["start_time"],
                        row["end_time"],
                    ),
                )
                return cur.rowcount > 0

            cur = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
            return cur.rowcount > 0

    def update_booking(
        self,
        booking_id: int,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
        price: float = 0,
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM bookings WHERE id = ?",
                (booking_id,),
            ).fetchone()
            if existing is None:
                raise ValueError("預約不存在")

            venue = conn.execute(
                "SELECT id, name FROM venues WHERE id = ?",
                (venue_id,),
            ).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_name = purpose.strip()
            if not purpose_name:
                raise ValueError("用途不可為空")
            purpose_row = conn.execute(
                "SELECT 1 FROM purposes WHERE name = ?",
                (purpose_name,),
            ).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            conflict = conn.execute(
                """
                SELECT b.id, b.start_time, b.end_time
                FROM bookings b
                WHERE b.venue_id = ?
                  AND b.id != ?
                  AND b.start_time < ?
                  AND b.end_time > ?
                LIMIT 1
                """,
                (
                    venue_id,
                    booking_id,
                    end_time.strftime(TIME_FORMAT),
                    start_time.strftime(TIME_FORMAT),
                ),
            ).fetchone()
            if conflict:
                raise ValueError(
                    f"時段衝突：{venue['name']} 已有預約 "
                    f"({conflict['start_time']} - {conflict['end_time']})"
                )

            cur = conn.execute(
                """
                UPDATE bookings
                SET venue_id = ?, customer = ?, purpose = ?, price = ?, start_time = ?, end_time = ?
                WHERE id = ?
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    booking_price,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                    booking_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("預約不存在")

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            price=booking_price,
            start_time=start_time,
            end_time=end_time,
        )

    def list_bookings(self, date: Optional[str] = None) -> List[Booking]:
        query = (
            "SELECT b.id, b.venue_id, v.name AS venue_name, b.customer, b.purpose, b.price, b.start_time, b.end_time "
            "FROM bookings b JOIN venues v ON b.venue_id = v.id"
        )
        params: tuple = ()
        if date:
            query += " WHERE date(b.start_time) = date(?)"
            params = (date,)
        query += " ORDER BY b.start_time, b.venue_id"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            Booking(
                booking_id=row["id"],
                venue_id=row["venue_id"],
                venue_name=row["venue_name"],
                customer=row["customer"],
                purpose=row["purpose"],
                price=float(row["price"]),
                start_time=datetime.strptime(row["start_time"], TIME_FORMAT),
                end_time=datetime.strptime(row["end_time"], TIME_FORMAT),
            )
            for row in rows
        ]

    def summarize_fees(self, start_date: str, end_date: str, customer: str = "") -> List[dict]:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("日期格式錯誤，請使用 YYYY-MM-DD") from exc
        if end_date < start_date:
            raise ValueError("結束日期不可早於開始日期")

        customer_name = customer.strip()
        query = """
            SELECT b.customer, COUNT(*) AS booking_count, SUM(b.price) AS total_fee
            FROM bookings b
            WHERE date(b.start_time) BETWEEN date(?) AND date(?)
        """
        params: tuple = (start_date, end_date)
        if customer_name:
            query += " AND b.customer = ?"
            params = (start_date, end_date, customer_name)
        query += " GROUP BY b.customer ORDER BY total_fee DESC, b.customer"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        summary = {
            row["customer"]: {
                "customer": row["customer"],
                "booking_count": int(row["booking_count"]),
                "booking_fee": float(row["total_fee"] or 0),
                "racket_count": 0,
                "racket_fee": 0.0,
            }
            for row in rows
        }

        racket_query = """
            SELECT customer, COUNT(*) AS racket_count, SUM(amount) AS racket_fee
            FROM racket_orders
            WHERE fee_status = '結清'
              AND pickup_date <> ''
              AND date(pickup_date) BETWEEN date(?) AND date(?)
        """
        racket_params: tuple = (start_date, end_date)
        if customer_name:
            racket_query += " AND customer = ?"
            racket_params = (start_date, end_date, customer_name)
        racket_query += " GROUP BY customer"

        with self._connect() as conn:
            racket_rows = conn.execute(racket_query, racket_params).fetchall()

        for row in racket_rows:
            record = summary.setdefault(
                row["customer"],
                {
                    "customer": row["customer"],
                    "booking_count": 0,
                    "booking_fee": 0.0,
                    "racket_count": 0,
                    "racket_fee": 0.0,
                },
            )
            record["racket_count"] = int(row["racket_count"])
            record["racket_fee"] = float(row["racket_fee"] or 0)

        items = list(summary.values())
        for item in items:
            item["total_fee"] = item["booking_fee"] + item["racket_fee"]
        items.sort(key=lambda x: (-x["total_fee"], x["customer"]))
        return items

    @staticmethod
    def _validate_date(date_str: str, field_name: str) -> None:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"{field_name}格式錯誤，請使用 YYYY-MM-DD") from exc

    @staticmethod
    def _validate_racket_statuses(status: str, fee_status: str) -> None:
        if status not in RACKET_STATUSES:
            raise ValueError("球拍狀態不正確")
        if fee_status not in RACKET_FEE_STATUSES:
            raise ValueError("收費狀態不正確")

    @staticmethod
    def _parse_price(price: float) -> float:
        try:
            value = float(price)
        except (TypeError, ValueError) as exc:
            raise ValueError("價錢格式錯誤") from exc
        if value < 0:
            raise ValueError("價錢不可為負數")
        return value

    @staticmethod
    def _month_end(dt: datetime) -> datetime:
        next_month = BookingManager._next_month_start(dt)
        return next_month - timedelta(days=1)

    @staticmethod
    def _next_month_start(dt: datetime) -> datetime:
        year = dt.year + 1 if dt.month == 12 else dt.year
        month = 1 if dt.month == 12 else dt.month + 1
        return datetime(year, month, 1, dt.hour, dt.minute)

    @staticmethod
    def _parse_time_range(start: str, end: str) -> tuple[datetime, datetime]:
        try:
            start_time = datetime.strptime(start.strip(), TIME_FORMAT)
            end_time = datetime.strptime(end.strip(), TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(f"時間格式錯誤，請使用 {TIME_FORMAT}") from exc

        if end_time <= start_time:
            raise ValueError("結束時間必須晚於開始時間")
        return start_time, end_time


def run_cli() -> None:
    manager = BookingManager()
    while True:
        print("\n場地預定管理系統\n1) 新增預約\n2) 查看今日預約\n3) 取消預約\n4) 離開")
        choice = input("請輸入選項：").strip()

        if choice == "1":
            venues = manager.list_venues()
            print("可用場地：")
            for v in venues:
                print(f"{v.venue_id}) {v.name}")
            try:
                purposes = manager.list_purposes()
                print("可用用途：")
                for p in purposes:
                    print(f"- {p.name}")
                booking = manager.add_booking(
                    venue_id=int(input("場地編號：").strip()),
                    customer=input("預約人：").strip(),
                    purpose=input("用途（請輸入完整名稱）：").strip(),
                    start=input(f"開始時間 ({TIME_FORMAT})：").strip(),
                    end=input(f"結束時間 ({TIME_FORMAT})：").strip(),
                    price=input("價錢：").strip() or 0,
                )
                print(f"新增成功，預約編號 #{booking.booking_id}")
            except ValueError as exc:
                print(f"新增失敗：{exc}")
        elif choice == "2":
            today = datetime.now().strftime("%Y-%m-%d")
            bookings = manager.list_bookings(date=today)
            if not bookings:
                print("今日無預約")
            for b in bookings:
                print(
                    f"#{b.booking_id} {b.venue_name} {b.start_time.strftime(TIME_FORMAT)}"
                    f"~{b.end_time.strftime(TIME_FORMAT)} {b.customer}/{b.purpose}/$ {b.price:.0f}"
                )
        elif choice == "3":
            booking_id = input("預約編號：").strip()
            print("取消成功" if booking_id.isdigit() and manager.cancel_booking(int(booking_id)) else "找不到編號")
        elif choice == "4":
            break


if __name__ == "__main__":
    run_cli()
