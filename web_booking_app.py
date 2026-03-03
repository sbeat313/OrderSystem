from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any, Dict, List, Union
from urllib.parse import parse_qs, urlparse

from booking_manager import Booking, BookingManager, TIME_FORMAT

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

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
:root { --border:#d1d5db; --primary:#2563eb; --bg:#f3f6fb; --panel:#ffffff; --sticky-venue:120px; --sticky-time:90px; }
*{ box-sizing:border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin: 0; background: linear-gradient(160deg,#eef2ff,#f8fafc); color: #111827; }
.container { width: 100%; max-width: none; margin: 0; padding: 16px 18px 24px; }
.title { margin: 0 0 12px; font-size: 34px; letter-spacing: .5px; }
.panel { border: 1px solid var(--border); border-radius: 14px; padding: 14px; background: var(--panel); box-shadow: 0 6px 20px rgba(15,23,42,.06); min-height: calc(100vh - 90px); }
label { display: block; margin-top: 0; font-weight: 700; color: #1f2937; font-size: 16px; }
input, select, button { width: 100%; padding: 12px; margin-top: 6px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 16px; }
button { background: var(--primary); color: white; border: none; font-weight: 700; cursor: pointer; }
button:hover { filter: brightness(.96); }
.note { margin-top: 8px; min-height: 22px; font-size: 16px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin-bottom: 10px; }
.toolbar .field { min-width: 150px; }
.toolbar input,.toolbar select { width: auto; min-width: 160px; }
.chip { width:auto; padding:10px 16px; border-radius:999px; border:1px solid #cbd5e1; background:#eef2ff; color:#1e3a8a; font-weight:700; font-size:15px; }
.chip.active { background:#1d4ed8; color:#fff; }
.grid-wrap { overflow-x: auto; overflow-y: visible; max-width: 100%; max-height: none; }
table { border-collapse: collapse; width: max-content; min-width: 100%; background: #fff; }
th, td { border: 1px solid #0f172a; text-align: center; font-size: 14px; padding: 6px; min-width: 48px; }
th { background: #f8fafc; height: 30px; position: sticky; top: 0; z-index: 6; }
th.top-row { top: 0; }
th.second-row { top: 42px; z-index: 7; }
th.sticky-left-1 { left: 0; min-width: var(--sticky-venue); z-index: 9; border-right: 1px solid #0f172a; box-shadow: inset -1px 0 0 #0f172a; }
th.sticky-left-2 { left: var(--sticky-venue); min-width: var(--sticky-time); z-index: 9; }
td.venue { min-width: var(--sticky-venue); font-weight: 700; background: #fff; position: sticky; left: 0; z-index: 4; border-right: 1px solid #0f172a; box-shadow: inset -1px 0 0 #0f172a; }
td.slot-time { min-width: var(--sticky-time); font-weight: 600; background: #f8fafc; position: sticky; left: var(--sticky-venue); z-index: 3; }
td.slot { height: 48px; background: #f8fafc; }
td.slot.booked-admin { background: #dcfce7; }
td.slot.booked-user { background: #0ea5e9; color: #fff; }
.badge { display:inline-block; padding:4px 10px; border-radius:999px; font-size:13px; font-weight:700; background:#e2e8f0; }
.small { font-size: 13px; line-height: 1.3; white-space: pre-line; }
.helper { margin: 6px 0 0; font-size: 14px; color: #475569; }
.legend { margin: 4px 0 8px; font-size: 14px; color: #334155; }
.legend .dot { display:inline-block; width:12px; height:12px; border-radius:3px; margin:0 6px 0 12px; vertical-align:middle; border:1px solid #0f172a; }
.legend .dot.admin { background:#dcfce7; }
.legend .dot.user { background:#0ea5e9; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.55); display: none; align-items: center; justify-content: center; z-index: 20; }
.modal { width: min(640px, 92vw); background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #cbd5e1; }
.modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.modal-actions { display: flex; gap: 8px; margin-top: 12px; }
.btn-secondary { background: #e2e8f0; color: #111827; }
</style>
</head>
<body>
<div class="container">
  <h2 class="title">暖西羽球館預約系統</h2>
  <div class="panel">
    <div class="toolbar">
      <div class="field">
        <label>日期</label>
        <input id="date" type="date" />
      </div>
      <div class="field">
        <label>顯示模式</label>
        <select id="view-mode">
          <option value="daily">每日</option>
          <option value="weekly">每週</option>
          <option value="biweekly" selected>雙週</option>
        </select>
      </div>
      <button class="chip" id="user-view">使用者檢視</button>
      <button class="chip" id="admin-view">管理員檢視</button>
      <button class="chip" id="options-link" style="display:none;" onclick="location.href='/options'">場地/用途設定</button>
      <button class="chip" id="open-add-modal" style="display:none;">新增預約</button>
      <span id="auth-state" class="badge">目前：使用者</span>
    </div>
    <div id="msg" class="note"></div>
    <div class="legend"><span class="dot admin"></span>管理員檢視：已預約 <span class="dot user"></span>藍色代表已預約（使用者檢視不顯示文字）</div>
    <div class="grid-wrap">
      <table id="grid"></table>
    </div>
  </div>
</div>

<div id="booking-modal" class="modal-backdrop">
  <div class="modal">
    <h3 style="margin-top:0;">新增預約（管理員）</h3>
    <div class="modal-grid">
      <div><label>場地</label><select id="venue"></select></div>
      <div><label>預約人</label><input id="customer" placeholder="例如：江江" /></div>
      <div><label>用途</label><select id="purpose"></select></div>
      <div><label>開始時間</label><input id="start" type="datetime-local" /></div>
      <div><label>結束時間</label><input id="end" type="datetime-local" /></div>
    </div>
    <div class="modal-actions">
      <button id="add-btn">送出預約</button>
      <button id="close-add-modal" class="btn-secondary">取消</button>
    </div>
    <p class="helper">※ 只有通過管理員驗證後可新增預約。</p>
  </div>
</div>

<script>
const START_HOUR = 8;
const END_HOUR = 22;
let currentRole = 'user';
let isAdmin = false;
let venues = [];
let purposes = [];
let bookingsCache = {};

function toServerDateTime(v) { return v.replace('T', ' '); }
function toDateObj(s) { return new Date(s.replace(' ', 'T') + ':00'); }
function fmtDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
function weekStart(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  const diff = (d.getDay() + 6) % 7; // monday start
  d.setDate(d.getDate() - diff);
  return d;
}

async function loadVenues() {
  const resp = await fetch('/api/venues');
  venues = await resp.json();
  const select = document.getElementById('venue');
  select.innerHTML = venues.map(v => `<option value="${v.venue_id}">${v.name}</option>`).join('');
}

async function loadPurposes() {
  const resp = await fetch('/api/purposes');
  purposes = await resp.json();
  const select = document.getElementById('purpose');
  select.innerHTML = purposes.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
}

async function loadBookings(date, force = false) {
  if (!force && bookingsCache[date]) return bookingsCache[date];
  const resp = await fetch(`/api/bookings?date=${date}`);
  const data = await resp.json();
  bookingsCache[date] = data;
  return data;
}

async function loadRangeBookings(baseDate, days) {
  const start = weekStart(baseDate);
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(fmtDate(d));
  }

  const lists = await Promise.all(dates.map(d => loadBookings(d)));
  const data = {};
  dates.forEach((d, idx) => {
    data[d] = lists[idx];
  });
  return data;
}

function bookingForSlot(venueId, slotHour, bookings) {
  return bookings.find(b => {
    if (b.venue_id !== venueId) return false;
    const start = toDateObj(b.start_time).getHours();
    const end = toDateObj(b.end_time).getHours();
    return slotHour >= start && slotHour < end;
  });
}

function setAuthBadge() {
  document.getElementById('auth-state').textContent = isAdmin ? '目前：管理員' : '目前：使用者';
  document.getElementById('admin-view').classList.toggle('active', currentRole === 'admin');
  document.getElementById('user-view').classList.toggle('active', currentRole === 'user');
  document.getElementById('options-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('open-add-modal').style.display = isAdmin ? 'inline-block' : 'none';
}

function renderDaily(bookings) {
  const grid = document.getElementById('grid');
  let html = '<tr><th>場地\\時段</th>';
  for (let h = START_HOUR; h < END_HOUR; h++) html += `<th>${String(h).padStart(2, '0')}<br>${String(h+1).padStart(2, '0')}</th>`;
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
          text = `${b.start_time.slice(11,16)}-${b.end_time.slice(11,16)}\n${b.customer}\n${b.purpose || ''}`;
        } else {
          cls += ' booked-user';
          text = '';
        }
      }
      html += `<td class="${cls}"><div class="small">${text}</div></td>`;
    }
    html += '</tr>';
  }
  grid.innerHTML = html;
}

function renderWeekly(weekData, baseDate, days = 7) {
  const grid = document.getElementById('grid');
  const start = weekStart(baseDate);
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    dates.push(fmtDate(d));
  }

  const weekdayNames = ['一', '二', '三', '四', '五', '六', '日'];
  const weeks = days > 7 ? [dates.slice(0, 7), dates.slice(7, 14)] : [dates];

  let html = '';
  weeks.forEach((weekDates, weekIdx) => {
    html += `<tr><th class="sticky-left-1 top-row" rowspan="2">場地</th>`;
    for (const day of weekDates) {
      const weekday = weekdayNames[(new Date(day + 'T00:00:00').getDay() + 6) % 7];
      html += `<th class="top-row" colspan="${END_HOUR - START_HOUR}">${day.slice(5)} (${weekday})</th>`;
    }
    html += '</tr><tr>';
    for (let d = 0; d < weekDates.length; d++) {
      for (let h = START_HOUR; h < END_HOUR; h++) {
        html += `<th class="second-row">${String(h).padStart(2, '0')}<br>${String(h + 1).padStart(2, '0')}</th>`;
      }
    }
    html += '</tr>';

    for (const venue of venues) {
      html += `<tr><td class="venue">${venue.name}</td>`;
      for (const day of weekDates) {
        const bookings = weekData[day] || [];
        for (let h = START_HOUR; h < END_HOUR; h++) {
          const b = bookingForSlot(venue.venue_id, h, bookings);
          let cls = 'slot';
          let cell = '';
          if (b) {
            cls += currentRole === 'admin' ? ' booked-admin' : ' booked-user';
            cell = currentRole === 'admin'
              ? `${b.start_time.slice(11,16)}-${b.end_time.slice(11,16)}\n${b.customer}\n${b.purpose || ''}`
              : '';
          }
          html += `<td class="${cls}"><div class="small">${cell}</div></td>`;
        }
      }
      html += '</tr>';
    }

    if (weekIdx < weeks.length - 1) {
      html += `<tr><td colspan="${1 + weekDates.length * (END_HOUR - START_HOUR)}" style="height:12px;background:#eef2ff;border:0;"></td></tr>`;
    }
  });

  grid.innerHTML = html;
}


async function refresh() {
  const date = document.getElementById('date').value;
  const mode = document.getElementById('view-mode').value;
  if (mode === 'daily') {
    renderDaily(await loadBookings(date));
  } else if (mode === 'weekly') {
    renderWeekly(await loadRangeBookings(date, 7), date, 7);
  } else {
    renderWeekly(await loadRangeBookings(date, 14), date, 14);
  }
}

async function requestAdmin() {
  const password = prompt('請輸入管理員密碼：');
  if (password === null) return;
  const resp = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!resp.ok) {
    alert('密碼錯誤，無法切換管理員檢視');
    return;
  }
  isAdmin = true;
  currentRole = 'admin';
  setAuthBadge();
  refresh();
}

function switchToUser() {
  currentRole = 'user';
  setAuthBadge();
  closeBookingModal();
  refresh();
}

function openBookingModal() {
  if (!isAdmin) return;
  document.getElementById('booking-modal').style.display = 'flex';
}

function closeBookingModal() {
  document.getElementById('booking-modal').style.display = 'none';
}

document.getElementById('admin-view').addEventListener('click', async () => {
  if (!isAdmin) await requestAdmin();
  else {
    currentRole = 'admin';
    setAuthBadge();
    refresh();
  }
});

document.getElementById('user-view').addEventListener('click', switchToUser);
document.getElementById('date').addEventListener('change', refresh);
document.getElementById('view-mode').addEventListener('change', refresh);
document.getElementById('open-add-modal').addEventListener('click', openBookingModal);
document.getElementById('close-add-modal').addEventListener('click', closeBookingModal);

document.getElementById('add-btn').addEventListener('click', async () => {
  const msg = document.getElementById('msg');
  if (!isAdmin) {
    msg.style.color = '#dc2626';
    msg.textContent = '請先切換為管理員並通過密碼驗證';
    return;
  }

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

  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '新增失敗';
    return;
  }
  msg.style.color = '#16a34a';
  msg.textContent = `新增成功 #${data.booking_id}`;
  bookingsCache = {};
  closeBookingModal();
  refresh();
});

(async function init() {
  const now = new Date();
  document.getElementById('date').value = now.toISOString().slice(0, 10);
  await loadVenues();
  await loadPurposes();
  setAuthBadge();
  await refresh();
})();
</script>
</body>
</html>
"""

OPTIONS_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>場地與用途設定</title>
<style>
body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f8fafc; font-size: 16px; }
.wrap { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel { background:#fff; border:1px solid #d1d5db; border-radius: 12px; padding: 14px; }
h1 { margin-top: 0; }
input, button { padding:10px; font-size:15px; }
button { cursor:pointer; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { border:1px solid #cbd5e1; padding:10px; text-align:left; font-size:15px; }
.actions button { margin-right: 6px; }
.top { max-width:1100px; margin:0 auto 12px; display:flex; gap:8px; align-items:center; }
</style>
</head>
<body>
<div class="top">
  <h1 style="margin:0;">場地 / 用途 管理</h1>
  <button onclick="location.href='/'">回預約頁</button>
</div>
<div class="wrap">
  <div class="panel">
    <h3>場地管理</h3>
    <input id="new-venue" placeholder="新增場地名稱" />
    <button onclick="createVenue()">新增場地</button>
    <table id="venue-table"></table>
  </div>
  <div class="panel">
    <h3>用途管理</h3>
    <input id="new-purpose" placeholder="新增用途名稱" />
    <button onclick="createPurpose()">新增用途</button>
    <table id="purpose-table"></table>
  </div>
</div>
<script>
let adminPassword = '';

async function login() {
  const pw = prompt('請輸入管理員密碼：');
  if (pw === null) return false;
  const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
  if (!resp.ok) { alert('密碼錯誤'); return false; }
  adminPassword = pw;
  return true;
}

async function ensureLogin() {
  if (adminPassword) return true;
  return await login();
}

async function api(method, path, payload = {}) {
  const ok = await ensureLogin();
  if (!ok) throw new Error('need login');
  payload.admin_password = adminPassword;
  const resp = await fetch(path, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || '操作失敗');
  return data;
}

async function refresh() {
  const venues = await (await fetch('/api/venues')).json();
  const purposes = await (await fetch('/api/purposes')).json();

  const vt = document.getElementById('venue-table');
  vt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>操作</th></tr>' + venues.map(v =>
    `<tr><td>${v.venue_id}</td><td><input value="${v.name}" id="venue-${v.venue_id}"/></td><td class="actions"><button onclick="updateVenue(${v.venue_id})">儲存</button><button onclick="deleteVenue(${v.venue_id})">刪除</button></td></tr>`
  ).join('');

  const pt = document.getElementById('purpose-table');
  pt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>操作</th></tr>' + purposes.map(p =>
    `<tr><td>${p.purpose_id}</td><td><input value="${p.name}" id="purpose-${p.purpose_id}"/></td><td class="actions"><button onclick="updatePurpose(${p.purpose_id})">儲存</button><button onclick="deletePurpose(${p.purpose_id})">刪除</button></td></tr>`
  ).join('');
}

async function createVenue() {
  try { await api('POST', '/api/venues', {name: document.getElementById('new-venue').value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function updateVenue(id) {
  try { await api('PUT', '/api/venues', {venue_id: id, name: document.getElementById(`venue-${id}`).value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function deleteVenue(id) {
  if (!confirm('確定刪除場地？')) return;
  try { await api('DELETE', '/api/venues', {venue_id: id}); await refresh(); }
  catch (e) { alert(e.message); }
}

async function createPurpose() {
  try { await api('POST', '/api/purposes', {name: document.getElementById('new-purpose').value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function updatePurpose(id) {
  try { await api('PUT', '/api/purposes', {purpose_id: id, name: document.getElementById(`purpose-${id}`).value}); await refresh(); }
  catch (e) { alert(e.message); }
}
async function deletePurpose(id) {
  if (!confirm('確定刪除用途？')) return;
  try { await api('DELETE', '/api/purposes', {purpose_id: id}); await refresh(); }
  catch (e) { alert(e.message); }
}

refresh();
</script>
</body>
</html>
"""


class BookingWebHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Union[Dict[str, Any], List[Any]], status: int = HTTPStatus.OK) -> None:
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
        if parsed.path == "/options":
            self._send_html(OPTIONS_PAGE)
            return
        if parsed.path == "/api/venues":
            with manager_lock:
                venues = [v.__dict__ for v in manager.list_venues()]
            self._send_json(venues)
            return
        if parsed.path == "/api/purposes":
            with manager_lock:
                purposes = [p.__dict__ for p in manager.list_purposes()]
            self._send_json(purposes)
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
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
        except json.JSONDecodeError:
            self._send_json({"error": "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/admin/login":
            password = str(payload.get("password", ""))
            if secrets.compare_digest(password, ADMIN_PASSWORD):
                self._send_json({"ok": True})
            else:
                self._send_json({"error": "密碼錯誤"}, status=HTTPStatus.UNAUTHORIZED)
            return

        if parsed.path in ["/api/venues", "/api/purposes"]:
            try:
                self._check_admin_password(payload)
                name = str(payload.get("name", "")).strip()
                with manager_lock:
                    if parsed.path == "/api/venues":
                        item = manager.add_venue(name)
                        self._send_json(item.__dict__, status=HTTPStatus.CREATED)
                    else:
                        item = manager.add_purpose(name)
                        self._send_json(item.__dict__, status=HTTPStatus.CREATED)
                return
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

        if parsed.path != "/api/bookings":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
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

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            self._check_admin_password(payload)
            with manager_lock:
                if parsed.path == "/api/venues":
                    item = manager.update_venue(int(payload.get("venue_id", 0)), str(payload.get("name", "")))
                elif parsed.path == "/api/purposes":
                    item = manager.update_purpose(int(payload.get("purpose_id", 0)), str(payload.get("name", "")))
                else:
                    self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
                    return
            self._send_json(item.__dict__)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc) or "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_len) or "{}")
            self._check_admin_password(payload)
            with manager_lock:
                if parsed.path == "/api/venues":
                    ok = manager.delete_venue(int(payload.get("venue_id", 0)))
                elif parsed.path == "/api/purposes":
                    ok = manager.delete_purpose(int(payload.get("purpose_id", 0)))
                else:
                    self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
                    return
            if not ok:
                self._send_json({"error": "資料不存在"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc) or "JSON 格式錯誤"}, status=HTTPStatus.BAD_REQUEST)

    @staticmethod
    def _check_admin_password(payload: Dict[str, Any]) -> None:
        password = str(payload.get("admin_password", ""))
        if not secrets.compare_digest(password, ADMIN_PASSWORD):
            raise ValueError("管理員密碼錯誤")


def run_web_app(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BookingWebHandler)
    print(f"伺服器已啟動：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_web_app()
