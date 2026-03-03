from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, urlparse

from booking_manager import Booking, BookingManager, TIME_FORMAT

manager = BookingManager()
manager_lock = Lock()


def booking_to_dict(booking: Booking) -> dict:
    return {
        "booking_id": booking.booking_id,
        "venue_id": booking.venue_id,
        "venue_name": booking.venue_name,
        "customer": booking.customer,
        "purpose": booking.purpose,
        "start_time": booking.start_time.strftime(TIME_FORMAT),
        "end_time": booking.end_time.strftime(TIME_FORMAT),
    }


HTML_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>場地預約管理</title>
<style>
body { font-family: Arial, sans-serif; margin: 16px; color: #111827; }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 16px; }
.panel { border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; }
label { display: block; margin-top: 8px; font-weight: 600; }
input, select, button { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; }
button { background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
button:hover { background: #1d4ed8; }
.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.role-btn { width: auto; padding: 6px 10px; background: #e5e7eb; color: #111827; }
.role-btn.active { background: #2563eb; color: #fff; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th, td { border: 1px solid #111827; text-align: center; font-size: 12px; }
th { background: #f3f4f6; height: 30px; }
td.venue { width: 72px; font-weight: 700; background: #fff; }
td.slot { height: 38px; background: #f8fafc; }
td.slot.booked-admin { background: #d9f99d; }
td.slot.booked-user { background: #0ea5e9; color: #fff; }
td.slot.school { background: #f5e8c5; }
.small { font-size: 11px; line-height: 1.1; white-space: pre-line; }
</style>
</head>
<body>
<h2>暖西羽球館預約系統</h2>
<div class="layout">
  <div class="panel">
    <h3>新增預約（管理員）</h3>
    <label>場地</label>
    <select id="venue"></select>
    <label>預約人</label>
    <input id="customer" placeholder="例如：江江" />
    <label>用途</label>
    <input id="purpose" placeholder="例如：練習" />
    <label>開始時間</label>
    <input id="start" type="datetime-local" />
    <label>結束時間</label>
    <input id="end" type="datetime-local" />
    <button id="add-btn">新增</button>
    <div id="msg"></div>
  </div>
  <div class="panel">
    <div class="toolbar">
      <label>日期：</label>
      <input id="date" type="date" style="width:auto"/>
      <button class="role-btn active" id="admin-view">管理員檢視</button>
      <button class="role-btn" id="user-view">使用者檢視</button>
    </div>
    <table id="grid"></table>
  </div>
</div>
<script>
const START_HOUR = 8;
const END_HOUR = 22;
const SCHOOL_START = 9;
const SCHOOL_END = 16;
let currentRole = 'admin';
let venues = [];

function toServerDateTime(v) { return v.replace('T', ' '); }
function toDateObj(s) { return new Date(s.replace(' ', 'T') + ':00'); }

async function loadVenues() {
  const resp = await fetch('/api/venues');
  venues = await resp.json();
  const select = document.getElementById('venue');
  select.innerHTML = venues.map(v => `<option value="${v.venue_id}">${v.name}</option>`).join('');
}

async function loadBookings(date) {
  const resp = await fetch(`/api/bookings?date=${date}`);
  return await resp.json();
}

function bookingForSlot(venueId, slotHour, bookings) {
  return bookings.find(b => {
    if (b.venue_id !== venueId) return false;
    const start = toDateObj(b.start_time).getHours();
    const end = toDateObj(b.end_time).getHours();
    return slotHour >= start && slotHour < end;
  });
}

function renderGrid(bookings) {
  const grid = document.getElementById('grid');
  let html = '<tr><th>場地\\時段</th>';
  for (let h = START_HOUR; h < END_HOUR; h++) html += `<th>${String(h).padStart(2, '0')}</th>`;
  html += '</tr>';

  for (const venue of venues) {
    html += `<tr><td class="venue">${venue.name}</td>`;
    for (let h = START_HOUR; h < END_HOUR; h++) {
      const b = bookingForSlot(venue.venue_id, h, bookings);
      let cls = 'slot';
      let text = '';
      if (b) {
        if (currentRole === 'admin') {
          cls += ' booked-admin';
          text = `${b.customer}\n${b.purpose || ''}`;
        } else {
          cls += ' booked-user';
          text = '已預約';
        }
      } else if (currentRole === 'user' && h >= SCHOOL_START && h < SCHOOL_END) {
        cls += ' school';
        text = h === SCHOOL_START ? '學校上課時段' : '';
      }
      html += `<td class="${cls}"><div class="small">${text}</div></td>`;
    }
    html += '</tr>';
  }
  grid.innerHTML = html;
}

async function refresh() {
  const date = document.getElementById('date').value;
  const bookings = await loadBookings(date);
  renderGrid(bookings);
}

function setRole(role) {
  currentRole = role;
  document.getElementById('admin-view').classList.toggle('active', role === 'admin');
  document.getElementById('user-view').classList.toggle('active', role === 'user');
  refresh();
}

document.getElementById('admin-view').addEventListener('click', () => setRole('admin'));
document.getElementById('user-view').addEventListener('click', () => setRole('user'));
document.getElementById('date').addEventListener('change', refresh);

document.getElementById('add-btn').addEventListener('click', async () => {
  const payload = {
    venue_id: Number(document.getElementById('venue').value),
    customer: document.getElementById('customer').value.trim(),
    purpose: document.getElementById('purpose').value.trim(),
    start: toServerDateTime(document.getElementById('start').value),
    end: toServerDateTime(document.getElementById('end').value),
  };
  const resp = await fetch('/api/bookings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  const msg = document.getElementById('msg');
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '新增失敗';
    return;
  }
  msg.style.color = '#16a34a';
  msg.textContent = `新增成功 #${data.booking_id}`;
  refresh();
});

(async function init() {
  const now = new Date();
  document.getElementById('date').value = now.toISOString().slice(0, 10);
  await loadVenues();
  await refresh();
})();
</script>
</body>
</html>
"""


class BookingWebHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict | list, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(HTML_PAGE)
            return
        if parsed.path == "/api/venues":
            with manager_lock:
                venues = [v.__dict__ for v in manager.list_venues()]
            self._send_json(venues)
            return
        if parsed.path == "/api/bookings":
            date = parse_qs(parsed.query).get("date", [""])[0]
            if date:
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    self._send_json({"error": "日期格式錯誤，請使用 YYYY-MM-DD"}, status=HTTPStatus.BAD_REQUEST)
                    return
            with manager_lock:
                bookings = [booking_to_dict(b) for b in manager.list_bookings(date=date or None)]
            self._send_json(bookings)
            return
        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/bookings":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            for field in ["venue_id", "customer", "start", "end"]:
                if not str(payload.get(field, "")).strip():
                    raise ValueError(f"缺少必要欄位：{field}")
            with manager_lock:
                booking = manager.add_booking(
                    venue_id=int(payload["venue_id"]),
                    customer=payload["customer"],
                    purpose=payload.get("purpose", ""),
                    start=payload["start"],
                    end=payload["end"],
                )
            self._send_json(booking_to_dict(booking), status=HTTPStatus.CREATED)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except json.JSONDecodeError:
            self._send_json({"error": "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)


def run_web_app(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BookingWebHandler)
    print(f"伺服器已啟動：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_web_app()
