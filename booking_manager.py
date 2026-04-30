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
    price: float
    months: int = 0
    weeks: int = 0
    days: int = 0


@dataclass
class StringItem:
    string_item_id: int
    name: str
    amount: float


@dataclass
class ExtraIncome:
    income_id: int
    customer: str
    item: str
    amount: float
    note: str
    income_time: datetime
    contact_phone: str = ""
    racket_model: str = ""
    string_tension: Optional[int] = None
    payment_status: str = ""
    racket_status: str = ""
    pickup_date: str = ""

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
    note: str = ""
    created_at: str = ""
    rental_group_id: str = ""


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
                    name TEXT NOT NULL UNIQUE,
                    price REAL NOT NULL DEFAULT 0,
                    months INTEGER NOT NULL DEFAULT 0,
                    weeks INTEGER NOT NULL DEFAULT 0,
                    days INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
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
                CREATE TABLE IF NOT EXISTS string_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS extra_incomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT NOT NULL,
                    item TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    income_time TEXT NOT NULL,
                    contact_phone TEXT NOT NULL DEFAULT '',
                    racket_model TEXT NOT NULL DEFAULT '',
                    string_tension INTEGER,
                    payment_status TEXT NOT NULL DEFAULT '',
                    racket_status TEXT NOT NULL DEFAULT '',
                    pickup_date TEXT NOT NULL DEFAULT ''
                )
                """
            )
            self._ensure_column(conn, "bookings", "price", "ALTER TABLE bookings ADD COLUMN price REAL NOT NULL DEFAULT 0")
            self._ensure_column(conn, "bookings", "rental_group_id", "ALTER TABLE bookings ADD COLUMN rental_group_id TEXT")
            self._ensure_column(conn, "bookings", "note", "ALTER TABLE bookings ADD COLUMN note TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "bookings", "created_at", "ALTER TABLE bookings ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")

            self._ensure_column(conn, "extra_incomes", "contact_phone", "ALTER TABLE extra_incomes ADD COLUMN contact_phone TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "extra_incomes", "racket_model", "ALTER TABLE extra_incomes ADD COLUMN racket_model TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "extra_incomes", "string_tension", "ALTER TABLE extra_incomes ADD COLUMN string_tension INTEGER")
            self._ensure_column(conn, "extra_incomes", "payment_status", "ALTER TABLE extra_incomes ADD COLUMN payment_status TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "extra_incomes", "racket_status", "ALTER TABLE extra_incomes ADD COLUMN racket_status TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "extra_incomes", "pickup_date", "ALTER TABLE extra_incomes ADD COLUMN pickup_date TEXT NOT NULL DEFAULT ''")

            self._ensure_column(conn, "purposes", "price", "ALTER TABLE purposes ADD COLUMN price REAL NOT NULL DEFAULT 0")
            self._ensure_column(conn, "purposes", "months", "ALTER TABLE purposes ADD COLUMN months INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "purposes", "weeks", "ALTER TABLE purposes ADD COLUMN weeks INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "purposes", "days", "ALTER TABLE purposes ADD COLUMN days INTEGER NOT NULL DEFAULT 0")

            count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO venues(name) VALUES (?)",
                    [(f"{index}號場",) for index in range(1, 7)],
                )

            purpose_count = conn.execute("SELECT COUNT(*) FROM purposes").fetchone()[0]
            if purpose_count == 0:
                conn.executemany(
                    "INSERT INTO purposes(name, price, months, weeks, days) VALUES (?, ?, ?, ?, ?)",
                    [
                        ("單月租", 0, 1, 0, 0),
                        ("雙月租", 0, 2, 0, 0),
                        ("臨租", 0, 0, 0, 0),
                        ("月租球友續租", 0, 1, 0, 0),
                        ("股東價", 0, 0, 0, 0),
                        ("連假專案", 0, 0, 0, 0),
                        ("寒暑假專案", 0, 0, 0, 0),
                        ("過年專案", 0, 0, 0, 0),
                    ],
                )

            string_item_count = conn.execute("SELECT COUNT(*) FROM string_items").fetchone()[0]
            if string_item_count == 0:
                conn.executemany(
                    "INSERT INTO string_items(name, amount) VALUES (?, ?)",
                    [
                        ("YONEX BG-66UM", 350),
                        ("YONEX BG-80", 380),
                        ("YONEX BG-65", 320),
                    ],
                )

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
            rows = conn.execute("SELECT id, name, price, months, weeks, days FROM purposes ORDER BY id").fetchall()
        return [
            Purpose(
                purpose_id=row["id"],
                name=row["name"],
                price=float(row["price"] or 0),
                months=int(row["months"] or 0),
                weeks=int(row["weeks"] or 0),
                days=int(row["days"] or 0),
            )
            for row in rows
        ]


    def list_string_items(self) -> List[StringItem]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, amount FROM string_items ORDER BY id").fetchall()
        return [StringItem(string_item_id=row["id"], name=row["name"], amount=float(row["amount"] or 0)) for row in rows]

    def add_string_item(self, name: str, amount: float) -> StringItem:
        item_name = name.strip()
        if not item_name:
            raise ValueError("穿線項目不可為空")
        value = self._parse_price(amount)
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO string_items(name, amount) VALUES (?, ?)", (item_name, value))
                string_item_id = cursor.lastrowid
            return StringItem(string_item_id=string_item_id, name=item_name, amount=value)
        except sqlite3.IntegrityError as exc:
            raise ValueError("穿線項目不可重複") from exc

    def update_string_item(self, string_item_id: int, name: str, amount: float) -> StringItem:
        item_name = name.strip()
        if not item_name:
            raise ValueError("穿線項目不可為空")
        value = self._parse_price(amount)
        try:
            with self._connect() as conn:
                cur = conn.execute("UPDATE string_items SET name = ?, amount = ? WHERE id = ?", (item_name, value, string_item_id))
                if cur.rowcount == 0:
                    raise ValueError("穿線項目不存在")
            return StringItem(string_item_id=string_item_id, name=item_name, amount=value)
        except sqlite3.IntegrityError as exc:
            raise ValueError("穿線項目不可重複") from exc

    def delete_string_item(self, string_item_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM string_items WHERE id = ?", (string_item_id,))
            return cur.rowcount > 0

    def add_purpose(self, name: str, price: float = 0, months: int = 0, weeks: int = 0, days: int = 0) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        purpose_price = self._parse_price(price)
        months_value, weeks_value, days_value = self._parse_cycle(months, weeks, days)
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "INSERT INTO purposes(name, price, months, weeks, days) VALUES (?, ?, ?, ?, ?)",
                    (purpose_name, purpose_price, months_value, weeks_value, days_value),
                )
                purpose_id = cursor.lastrowid
            return Purpose(
                purpose_id=purpose_id,
                name=purpose_name,
                price=purpose_price,
                months=months_value,
                weeks=weeks_value,
                days=days_value,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def update_purpose(self, purpose_id: int, name: str, price: float = 0, months: int = 0, weeks: int = 0, days: int = 0) -> Purpose:
        purpose_name = name.strip()
        if not purpose_name:
            raise ValueError("用途名稱不可為空")
        purpose_price = self._parse_price(price)
        months_value, weeks_value, days_value = self._parse_cycle(months, weeks, days)
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "UPDATE purposes SET name = ?, price = ?, months = ?, weeks = ?, days = ? WHERE id = ?",
                    (purpose_name, purpose_price, months_value, weeks_value, days_value, purpose_id),
                )
                if cur.rowcount == 0:
                    raise ValueError("用途不存在")
            return Purpose(
                purpose_id=purpose_id,
                name=purpose_name,
                price=purpose_price,
                months=months_value,
                weeks=weeks_value,
                days=days_value,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("用途名稱不可重複") from exc

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

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
        note: str = "",
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        note_text = note.strip()
        created_at = datetime.now().strftime(TIME_FORMAT)
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
                INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    venue_id,
                    customer.strip(),
                    purpose_name,
                    booking_price,
                    start_time.strftime(TIME_FORMAT),
                    end_time.strftime(TIME_FORMAT),
                    None,
                    note_text,
                    created_at,
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
            note=note_text,
            created_at=created_at,
        )

    def add_bookings_for_purpose(
        self,
        venue_id: int,
        customer: str,
        start: str,
        end: str,
        purpose: str = "",
        price: float = 0,
        note: str = "",
    ) -> List[Booking]:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        note_text = note.strip()
        created_at = datetime.now().strftime(TIME_FORMAT)
        duration = end_time - start_time
        purpose_name = purpose.strip()

        slot_starts: List[datetime] = []

        with self._connect() as conn:
            venue = conn.execute("SELECT id, name FROM venues WHERE id = ?", (venue_id,)).fetchone()
            if venue is None:
                raise ValueError("場地不存在")

            purpose_row = conn.execute(
                "SELECT months, weeks, days FROM purposes WHERE name = ?",
                (purpose_name,),
            ).fetchone()
            if purpose_row is None:
                raise ValueError("用途不存在，請從選單選擇")

            months = int(purpose_row["months"] or 0)
            weeks = int(purpose_row["weeks"] or 0)
            days = int(purpose_row["days"] or 0)
            if months <= 0 and weeks <= 0 and days <= 0:
                slot_starts = [start_time]
            else:
                slot_candidates: set[datetime] = set()

                # 週期（月/周）維持每 7 天一筆
                if months > 0:
                    period_end_weekly = self._month_end(self._add_months(start_time, months - 1))
                else:
                    period_end_weekly = start_time
                if weeks > 0:
                    period_end_weekly = period_end_weekly + timedelta(days=max(0, weeks * 7 - 1))

                if months > 0 or weeks > 0:
                    slot_cursor = start_time
                    while slot_cursor.date() <= period_end_weekly.date():
                        slot_candidates.add(slot_cursor)
                        slot_cursor += timedelta(days=7)

                # 日規則：改為每日建立
                if days > 0:
                    for offset in range(days):
                        slot_candidates.add(start_time + timedelta(days=offset))

                slot_starts = sorted(slot_candidates)

            group_id = str(uuid.uuid4()) if len(slot_starts) > 1 else None

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
            note_text = note.strip()
            created_at = datetime.now().strftime(TIME_FORMAT)
            for slot_start in slot_starts:
                slot_end = slot_start + duration
                cursor = conn.execute(
                    """
                    INSERT INTO bookings(venue_id, customer, purpose, price, start_time, end_time, rental_group_id, note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        venue_id,
                        customer.strip(),
                        purpose_name,
                        booking_price,
                        slot_start.strftime(TIME_FORMAT),
                        slot_end.strftime(TIME_FORMAT),
                        group_id,
                        note_text,
                        created_at,
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
                        note=note_text,
                        created_at=created_at,
                    )
                )

        return created

    def cancel_booking(self, booking_id: int, delete_scope: str = "group") -> bool:
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

            if delete_scope not in {"single", "group"}:
                raise ValueError("刪除範圍不正確")

            if row["rental_group_id"] and delete_scope == "group":
                cur = conn.execute(
                    "DELETE FROM bookings WHERE rental_group_id = ?",
                    (row["rental_group_id"],),
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
        note: str = "",
    ) -> Booking:
        start_time, end_time = self._parse_time_range(start, end)
        booking_price = self._parse_price(price)
        note_text = note.strip()
        duration = end_time - start_time
        if duration <= timedelta(0):
            raise ValueError("結束時間必須晚於開始時間")
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, venue_id, customer, purpose, start_time, end_time, rental_group_id, created_at FROM bookings WHERE id = ?",
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

            rows_to_update = [
                {
                    "id": existing["id"],
                    "start_time": datetime.strptime(existing["start_time"], TIME_FORMAT),
                }
            ]
            original_start = rows_to_update[0]["start_time"]

            if existing["rental_group_id"]:
                group_rows = conn.execute(
                    """
                    SELECT id, start_time
                    FROM bookings
                    WHERE rental_group_id = ?
                    ORDER BY start_time
                    """,
                    (existing["rental_group_id"],),
                ).fetchall()
                if group_rows:
                    rows_to_update = [
                        {
                            "id": row["id"],
                            "start_time": datetime.strptime(row["start_time"], TIME_FORMAT),
                        }
                        for row in group_rows
                    ]
            start_delta = start_time - original_start
            update_targets = []
            row_ids = {row["id"] for row in rows_to_update}
            for row in rows_to_update:
                row_start = row["start_time"] + start_delta
                row_end = row_start + duration
                update_targets.append((row["id"], row_start, row_end))

                conflict = conn.execute(
                    """
                    SELECT b.id, b.start_time, b.end_time
                    FROM bookings b
                    WHERE b.venue_id = ?
                      AND b.id NOT IN ({ids})
                      AND b.start_time < ?
                      AND b.end_time > ?
                    LIMIT 1
                    """.format(ids=",".join(["?"] * len(row_ids))),
                    (
                        venue_id,
                        *row_ids,
                        row_end.strftime(TIME_FORMAT),
                        row_start.strftime(TIME_FORMAT),
                    ),
                ).fetchone()
                if conflict:
                    raise ValueError(
                        f"時段衝突：{venue['name']} 已有預約 "
                        f"({conflict['start_time']} - {conflict['end_time']})"
                    )

            for row_id, row_start, row_end in update_targets:
                conn.execute(
                    """
                    UPDATE bookings
                    SET venue_id = ?, customer = ?, purpose = ?, price = ?, start_time = ?, end_time = ?, note = ?
                    WHERE id = ?
                    """,
                    (
                        venue_id,
                        customer.strip(),
                        purpose_name,
                        booking_price,
                        row_start.strftime(TIME_FORMAT),
                        row_end.strftime(TIME_FORMAT),
                        note_text,
                        row_id,
                    ),
                )

        return Booking(
            booking_id=booking_id,
            venue_id=venue["id"],
            venue_name=venue["name"],
            customer=customer.strip(),
            purpose=purpose_name,
            price=booking_price,
            start_time=start_time,
            end_time=end_time,
            note=note_text,
            created_at=(existing["created_at"] or ""),
        )

    def list_bookings(self, date: Optional[str] = None) -> List[Booking]:
        query = (
            "SELECT b.id, b.venue_id, v.name AS venue_name, b.customer, b.purpose, b.price, b.start_time, b.end_time, b.note, b.created_at, b.rental_group_id "
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
                note=row["note"] or "",
                created_at=row["created_at"] or "",
                rental_group_id=row["rental_group_id"] or "",
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
            SELECT
                b.customer,
                COUNT(*) AS booking_count,
                ROUND(
                    SUM(
                        b.price * ((julianday(b.end_time) - julianday(b.start_time)) * 24.0)
                    ),
                    2
                ) AS total_fee
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

        return [
            {
                "customer": row["customer"],
                "booking_count": int(row["booking_count"]),
                "total_fee": float(row["total_fee"] or 0),
            }
            for row in rows
        ]

    def add_extra_income(
        self,
        customer: str,
        item: str,
        amount: float,
        income_time: str,
        note: str = "",
        contact_phone: str = "",
        racket_model: str = "",
        string_tension: Optional[int] = None,
        payment_status: str = "",
        racket_status: str = "",
        pickup_date: str = "",
    ) -> ExtraIncome:
        parsed = self._validate_extra_income_payload(
            customer=customer,
            item=item,
            amount=amount,
            income_time=income_time,
            note=note,
            contact_phone=contact_phone,
            racket_model=racket_model,
            string_tension=string_tension,
            payment_status=payment_status,
            racket_status=racket_status,
            pickup_date=pickup_date,
        )

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO extra_incomes(
                    customer, item, amount, note, income_time,
                    contact_phone, racket_model, string_tension, payment_status, racket_status, pickup_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parsed["customer_name"],
                    parsed["item_name"],
                    parsed["income_amount"],
                    parsed["memo"],
                    parsed["income_time"].strftime(TIME_FORMAT),
                    parsed["phone"],
                    parsed["racket"],
                    parsed["tension_value"],
                    parsed["paid_status"],
                    parsed["racket_state"],
                    parsed["pickup"],
                ),
            )
            income_id = cursor.lastrowid

        return ExtraIncome(
            income_id=income_id,
            customer=parsed["customer_name"],
            item=parsed["item_name"],
            amount=parsed["income_amount"],
            note=parsed["memo"],
            income_time=parsed["income_time"],
            contact_phone=parsed["phone"],
            racket_model=parsed["racket"],
            string_tension=parsed["tension_value"],
            payment_status=parsed["paid_status"],
            racket_status=parsed["racket_state"],
            pickup_date=parsed["pickup"],
        )

    def update_extra_income(
        self,
        income_id: int,
        customer: str,
        item: str,
        amount: float,
        income_time: str,
        note: str = "",
        contact_phone: str = "",
        racket_model: str = "",
        string_tension: Optional[int] = None,
        payment_status: str = "",
        racket_status: str = "",
        pickup_date: str = "",
    ) -> ExtraIncome:
        if income_id <= 0:
            raise ValueError("收入資料不存在")

        parsed = self._validate_extra_income_payload(
            customer=customer,
            item=item,
            amount=amount,
            income_time=income_time,
            note=note,
            contact_phone=contact_phone,
            racket_model=racket_model,
            string_tension=string_tension,
            payment_status=payment_status,
            racket_status=racket_status,
            pickup_date=pickup_date,
        )

        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE extra_incomes
                SET customer = ?, item = ?, amount = ?, note = ?, income_time = ?,
                    contact_phone = ?, racket_model = ?, string_tension = ?, payment_status = ?,
                    racket_status = ?, pickup_date = ?
                WHERE id = ?
                """,
                (
                    parsed["customer_name"],
                    parsed["item_name"],
                    parsed["income_amount"],
                    parsed["memo"],
                    parsed["income_time"].strftime(TIME_FORMAT),
                    parsed["phone"],
                    parsed["racket"],
                    parsed["tension_value"],
                    parsed["paid_status"],
                    parsed["racket_state"],
                    parsed["pickup"],
                    income_id,
                ),
            )
            if cur.rowcount == 0:
                raise ValueError("收入資料不存在")

        return ExtraIncome(
            income_id=income_id,
            customer=parsed["customer_name"],
            item=parsed["item_name"],
            amount=parsed["income_amount"],
            note=parsed["memo"],
            income_time=parsed["income_time"],
            contact_phone=parsed["phone"],
            racket_model=parsed["racket"],
            string_tension=parsed["tension_value"],
            payment_status=parsed["paid_status"],
            racket_status=parsed["racket_state"],
            pickup_date=parsed["pickup"],
        )

    def list_extra_incomes(
        self,
        start_date: str = "",
        end_date: str = "",
        customer: str = "",
    ) -> List[ExtraIncome]:
        query = (
            "SELECT id, customer, item, amount, note, income_time, "
            "contact_phone, racket_model, string_tension, payment_status, racket_status, pickup_date "
            "FROM extra_incomes WHERE 1=1"
        )
        params: List[str] = []
        if start_date:
            query += " AND date(income_time) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(income_time) <= date(?)"
            params.append(end_date)
        if customer.strip():
            query += " AND customer = ?"
            params.append(customer.strip())
        query += " ORDER BY income_time DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [
            ExtraIncome(
                income_id=row["id"],
                customer=row["customer"],
                item=row["item"],
                amount=float(row["amount"] or 0),
                note=row["note"] or "",
                income_time=datetime.strptime(row["income_time"], TIME_FORMAT),
                contact_phone=row["contact_phone"] or "",
                racket_model=row["racket_model"] or "",
                string_tension=(int(row["string_tension"]) if row["string_tension"] is not None else None),
                payment_status=row["payment_status"] or "",
                racket_status=row["racket_status"] or "",
                pickup_date=self._normalize_date_separator(row["pickup_date"] or ""),
            )
            for row in rows
        ]

    def delete_extra_income(self, income_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM extra_incomes WHERE id = ?", (income_id,))
            return cur.rowcount > 0

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, ddl: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            conn.execute(ddl)

    def _validate_extra_income_payload(
        self,
        customer: str,
        item: str,
        amount: float,
        income_time: str,
        note: str = "",
        contact_phone: str = "",
        racket_model: str = "",
        string_tension: Optional[int] = None,
        payment_status: str = "",
        racket_status: str = "",
        pickup_date: str = "",
    ) -> dict:
        customer_name = customer.strip()
        item_name = item.strip()
        memo = note.strip()
        phone = contact_phone.strip()
        racket = racket_model.strip()
        paid_status = payment_status.strip()
        racket_state = racket_status.strip()
        pickup = self._normalize_date_separator(pickup_date.strip())
        if not customer_name:
            raise ValueError("姓名不可為空")
        if not item_name:
            raise ValueError("項目不可為空")

        try:
            dt = datetime.strptime(income_time.strip(), TIME_FORMAT)
        except ValueError as exc:
            raise ValueError(f"時間格式錯誤，請使用 {TIME_FORMAT}") from exc
        income_amount = self._parse_price(amount)

        tension_value: Optional[int] = None
        if string_tension not in (None, ""):
            try:
                tension_value = int(string_tension)
            except (TypeError, ValueError) as exc:
                raise ValueError("磅數格式錯誤") from exc
            if tension_value <= 0:
                raise ValueError("磅數必須為正整數")

        if item_name == "球拍":
            if not racket:
                raise ValueError("球拍項目需填寫穿線項目")
            if tension_value is None:
                raise ValueError("球拍項目需填寫磅數")

        return {
            "customer_name": customer_name,
            "item_name": item_name,
            "memo": memo,
            "phone": phone,
            "racket": racket,
            "paid_status": paid_status,
            "racket_state": racket_state,
            "pickup": pickup,
            "income_time": dt,
            "income_amount": income_amount,
            "tension_value": tension_value,
        }

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
    def _parse_cycle(months: int, weeks: int, days: int) -> tuple[int, int, int]:
        try:
            m = int(months or 0)
            w = int(weeks or 0)
            d = int(days or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("週期格式錯誤，月/周/日需為整數") from exc
        if m < 0 or w < 0 or d < 0:
            raise ValueError("週期不可為負數")
        return m, w, d

    @staticmethod
    def _normalize_date_separator(value: str) -> str:
        text = value.strip()
        if len(text) >= 10 and text[4] == "/" and text[7] == "/":
            return f"{text[:4]}-{text[5:7]}-{text[8:10]}{text[10:]}"
        return text

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
    def _add_months(dt: datetime, months: int) -> datetime:
        total_month = (dt.year * 12 + (dt.month - 1)) + max(0, months)
        year = total_month // 12
        month = (total_month % 12) + 1
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
