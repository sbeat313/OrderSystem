from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any, Dict, List, Union
from urllib.parse import parse_qs, urlparse

from booking_manager import Booking, BookingManager, TIME_FORMAT, ExtraIncome

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
        "price": booking.price,
        "start_time": booking.start_time.strftime(TIME_FORMAT),
        "end_time": booking.end_time.strftime(TIME_FORMAT),
        "note": booking.note,
        "created_at": booking.created_at,
    }


def extra_income_to_dict(income: ExtraIncome) -> dict:
    return {
        "income_id": income.income_id,
        "customer": income.customer,
        "item": income.item,
        "amount": income.amount,
        "note": income.note,
        "income_time": income.income_time.strftime(TIME_FORMAT),
        "contact_phone": income.contact_phone,
        "racket_model": income.racket_model,
        "string_tension": income.string_tension,
        "payment_status": income.payment_status,
        "racket_status": income.racket_status,
        "pickup_date": income.pickup_date,
    }


def string_item_to_dict(item: Any) -> dict:
    return {
        "string_item_id": item.string_item_id,
        "name": item.name,
        "amount": item.amount,
    }


def purpose_to_dict(item: Any) -> dict:
    return {
        "purpose_id": item.purpose_id,
        "name": item.name,
        "price": item.price,
    }


def get_admin_password() -> str:
    with manager_lock:
        saved = manager.get_setting("admin_password", "")
    return saved or ADMIN_PASSWORD

HTML_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>場地預約管理</title>
<style>
:root {
  --border:#dbe4f0;
  --primary:#2563eb;
  --primary-strong:#1d4ed8;
  --bg:#f8f6ff;
  --panel:#ffffff;
  --text:#0f172a;
  --muted:#475569;
  --sticky-venue:120px;
  --sticky-time:90px;
}
*{ box-sizing:border-box; }
body {
  font-family: "Noto Sans TC", "Segoe UI", Arial, sans-serif;
  margin: 0;
  color: var(--text);
  background:
    radial-gradient(circle at 12% 8%, #e8ecff 0%, rgba(232,236,255,0) 42%),
    radial-gradient(circle at 92% 4%, #e8f9ff 0%, rgba(232,249,255,0) 36%),
    radial-gradient(circle at 55% 100%, #f9edff 0%, rgba(249,237,255,0) 40%),
    var(--bg);
}
.container { width: 100%; max-width: none; margin: 0; padding: 18px 20px 26px; }
.title { margin: 0 0 10px; font-size: 48px; letter-spacing: .8px; color:#18396f; font-weight: 900; }
.hover-top-zone {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 82px;
  z-index: 40;
  display: flex;
  justify-content: center;
  pointer-events: auto;
}
.floating-actions {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  border: 1px solid #d6deef;
  border-radius: 14px;
  background: rgba(255,255,255,.94);
  box-shadow: 0 10px 28px rgba(15,23,42,.18);
  opacity: 0;
  transform: translateY(-20px);
  pointer-events: none;
  transition: opacity .2s ease, transform .2s ease;
  backdrop-filter: blur(4px);
}
.hover-top-zone:hover .floating-actions,
.floating-actions:focus-within {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}
.panel {
  border: 1px solid #d9e4f2;
  border-radius: 20px;
  padding: 14px;
  background: linear-gradient(180deg, #f7fbff, #f4f8ff);
  box-shadow: 0 8px 26px rgba(30,64,175,.08);
  min-height: calc(100vh - 96px);
}
label { display: block; margin-top: 0; font-weight: 700; color: #1f2937; font-size: 16px; }
input, select, button {
  width: 100%; padding: 12px; margin-top: 6px;
  border-radius: 12px; border: 1px solid #c9d6ea; font-size: 15px;
}
input, select { background: #fff; box-shadow: inset 0 1px 2px rgba(15,23,42,.04); }
button {
  background: linear-gradient(180deg, var(--primary), var(--primary-strong));
  color: white; border: none; font-weight: 700; cursor: pointer;
  box-shadow: 0 6px 16px rgba(37,99,235,.24);
}
button:hover { filter: brightness(.98); transform: translateY(-1px); }
.note { margin-top: 10px; min-height: 22px; font-size: 15px; }
#msg:empty { display: none; }
.title-row { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom: 8px; }
.title-wrap { display:flex; align-items:center; gap:10px; }
.contact-info {
  text-align:right;
  color:#334155;
  font-weight:700;
  line-height:1.45;
  font-size:16px;
  background: linear-gradient(180deg, #ffffff, #eef4ff);
  border: 1px solid #cddaf2;
  border-radius: 14px;
  padding: 10px 14px;
  box-shadow: 0 6px 18px rgba(30,64,175,.12);
}
.contact-line { display:flex; align-items:center; justify-content:flex-end; gap:8px; }
.contact-line + .contact-line { margin-top: 4px; }
.contact-icon { font-size:18px; line-height:1; }
.contact-info .address { font-size:17px; color:#1f2937; }
.contact-info .phone { font-size:20px; color:#1e3a8a; font-weight:800; }
.title-icon { font-size: 44px; opacity:.35; line-height:1; }
.control-row { display:flex; align-items:flex-end; gap:10px; flex-wrap:wrap; margin-bottom: 10px; }
.week-nav { display:flex; gap:8px; align-items:center; }
.week-nav button { width:auto; padding:10px 12px; border-radius:10px; box-shadow:none; margin-top:0; }
.week-label { background:#fff; border:1px solid #d5dfef; border-radius:10px; padding:10px 12px; color:#334155; font-weight:700; }
.toolbar { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin-bottom: 0; }
.toolbar .field { min-width: 150px; }
.toolbar input,.toolbar select { width: auto; min-width: 170px; }
.chip {
  width:auto; padding:10px 16px; border-radius:999px;
  border:1px solid #c9d6ea; background:linear-gradient(180deg,#eef2ff,#e0ecff); color:#1e3a8a;
  font-weight:700; font-size:14px; box-shadow:none;
}
.chip.active { background: linear-gradient(180deg, #4f46e5, #2563eb); color:#fff; }
.grid-wrap {
  overflow-x: auto; overflow-y: visible; max-width: 100%; max-height: none;
  border: 1px solid var(--border); border-radius: 12px; background:#fff;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6);
}
.grid-section { margin-bottom: 14px; }
.grid-section:last-child { margin-bottom: 0; }
.grid-section-title {
  margin: 0 0 6px;
  font-size: 16px;
  color: #334155;
  font-weight: 800;
}
table { border-collapse: separate; border-spacing: 0; width: max-content; min-width: 100%; background: #fff; }
th, td { border: 1px solid #dbe5f2; text-align: center; font-size: 16px; padding: 8px; min-width: 48px; }
th {
  background: linear-gradient(180deg, #f5f7ff, #eaf1ff);
  height: 32px; position: sticky; top: 0; z-index: 6;
  color:#0f2f66;
}
th.top-row { top: 0; }
th.second-row { top: 44px; z-index: 7; }
th.sticky-left-1 {
  left: 0; min-width: var(--sticky-venue); z-index: 9;
  border-right: 1px solid #dbe5f2; box-shadow: inset -1px 0 0 #dbe5f2;
}
th.sticky-left-2 { left: var(--sticky-venue); min-width: var(--sticky-time); z-index: 9; }
td.venue {
  min-width: var(--sticky-venue); font-weight: 700; color:#0f2f66;
  background: #f8fbff; position: sticky; left: 0; z-index: 4;
  border-right: 1px solid #dbe5f2; box-shadow: inset -1px 0 0 #dbe5f2;
}
td.slot-time { min-width: var(--sticky-time); font-weight: 600; background: #f8fafc; position: sticky; left: var(--sticky-venue); z-index: 3; }
td.slot { height: 54px; background: #fcfdff; border-radius: 0; }
td.slot.available,
td.slot.full { background: #fcfdff; color: #0f172a; }
.availability-pill {
  width: 85%;
  margin: 0 auto;
  border-radius: 10px;
  padding: 8px 4px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.55);
}
td.slot.available .availability-pill { background: #e7f8eb; color: #166534; }
td.slot.full .availability-pill { background: #ffdfe0; color: #991b1b; }
th.day-block-start, td.day-block-start { border-left: 3px solid #cbd5e1; }
th.weekend-head {
  background: linear-gradient(180deg, #fde047, #facc15);
  color: #713f12;
  border-top: 3px solid #f59e0b;
  border-bottom: 3px solid #f59e0b;
  border-right: 1px solid #dbe5f2;
}
th.weekend-date-label {
  background: linear-gradient(180deg, #fef08a, #fde047);
  color: #713f12;
  border-bottom: 2px solid #f59e0b;
}
td.weekend-time {
  background: #fcfdff;
  color: #713f12;
  border-left: 1px solid #dbe5f2;
  border-right: 1px solid #dbe5f2;
}
td.slot.weekend-time.available .availability-pill { background: #f4fde2; color: #4d5f1f; }
td.slot.weekend-time.full .availability-pill { background: #ffdede; color: #8f1d1d; }
th.weekend-head.day-block-start,
th.weekend-date-label.day-block-start,
td.slot.weekend-time.day-block-start { border-left: 3px solid #f59e0b; }
th.weekend-head:last-child,
th.weekend-date-label:last-child,
td.slot.weekend-time:last-child { border-right: 3px solid #f59e0b; }
#grid-sections table tr:last-child td.slot.weekend-time { border-bottom: 3px solid #f59e0b; }
td.slot.booked-admin,
td.slot.booked-user { background: #fcfdff; color: #0f172a; }
.booking-pill {
  width: 85%;
  margin: 0 auto;
  border-radius: 10px;
  padding: 6px 4px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.55);
}
td.slot.booked-admin .booking-pill { background: #bbf7d0; }
td.slot.booked-user .booking-pill { background: #93c5fd; }
.small { font-size: 15px; line-height: 1.35; white-space: pre-line; }
.slot.selected { outline: 3px solid #f59e0b; outline-offset: -3px; }
.helper { margin: 6px 0 0; font-size: 14px; color: var(--muted); }
.modal-backdrop { position: fixed; inset: 0; background: rgba(15,23,42,0.55); display: none; align-items: center; justify-content: center; z-index: 20; }
.modal { width: min(680px, 92vw); background: #fff; border-radius: 14px; padding: 18px; border: 1px solid #cbd5e1; box-shadow: 0 20px 50px rgba(15,23,42,.2); }
.modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.modal-actions { display: flex; gap: 8px; margin-top: 12px; }
.btn-secondary { background: #e2e8f0; color: #111827; box-shadow:none; }
@media (hover: none) {
  .floating-actions {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }
}
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button class="chip" id="admin-view">進階檢視</button>
    <button class="chip" id="options-link" style="display:none;" onclick="location.href='/settings'">系統設定</button>
    <button class="chip" id="data-settings-link" style="display:none;" onclick="location.href='/purposes'">資料設定</button>
    <button class="chip" id="report-link" style="display:none;" onclick="location.href='/reports'">費用統計</button>
    <button class="chip" id="extra-income-link" style="display:none;" onclick="location.href='/extra-income'">額外收入</button>
    <button class="chip" id="open-add-modal" style="display:none;">新增預約</button>
  </div>
</div>
<div class="container">
  <div class="title-row">
    <div class="title-wrap">
      <h2 class="title">暖西羽球館預約系統</h2>
      <div class="title-icon">🏸</div>
    </div>
    <div class="contact-info">
      <div class="contact-line address">
        <span class="contact-icon">📍</span>
        <span>205基隆市暖暖區暖暖街350號</span>
      </div>
      <div class="contact-line phone">
        <span class="contact-icon">☎️</span>
        <span>(02)2457-0277</span>
      </div>
    </div>
  </div>
  <div class="control-row">
    <div class="toolbar">
      <div class="field">
        <label>&nbsp;</label>
        <input id="date" type="date" />
      </div>
    </div>
    <div class="week-nav">
      <button id="prev-week" class="btn-secondary" type="button">‹ 上一週</button>
      <span id="week-label" class="week-label"></span>
      <button id="next-week" class="btn-secondary" type="button">下一週 ›</button>
    </div>
  </div>
  <div class="panel">
    <div id="msg" class="note"></div>
    <div id="grid-sections"></div>
  </div>
</div>

<div id="booking-modal" class="modal-backdrop">
  <div class="modal">
    <h3 style="margin-top:0;">新增預約（管理員）</h3>
    <div class="modal-grid">
      <div><label>場地（可複選）</label><select id="venue" multiple size="6"></select></div>
      <div><label>預約人</label><input id="customer" placeholder="例如：江江" /></div>
      <div><label>用途</label><select id="purpose"></select></div>
      <div><label>價錢</label><input id="price" type="number" min="0" step="1" placeholder="例如：500" /></div>
      <div><label>開始時間</label><input id="start" type="datetime-local" /></div>
      <div><label>結束時間</label><input id="end" type="datetime-local" /></div>
      <div style="grid-column:1 / -1;"><label>備註</label><input id="booking-note" placeholder="可留空" /></div>
    </div>
    <div class="modal-actions">
      <button id="add-btn">送出預約</button>
      <button id="close-add-modal" class="btn-secondary">取消</button>
    </div>
    <div id="booking-modal-msg" class="note"></div>
  </div>
</div>

<script>
const START_HOUR = 8;
const END_HOUR = 22;
let isAdmin = false;
let adminPassword = '';
let venues = [];
let purposes = [];
let bookingsCache = {};
let selectedBookingId = null;
let modalEditingBookingId = null;
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';
const ADMIN_SESSION_TTL_MS_KEY = 'booking_admin_session_ttl_ms';
const DEFAULT_ADMIN_SESSION_TTL_MS = 2 * 60 * 60 * 1000;

function getAdminSessionTtlMs() {
  const raw = Number(localStorage.getItem(ADMIN_SESSION_TTL_MS_KEY) || 0);
  if (!raw || raw < 60 * 1000) return DEFAULT_ADMIN_SESSION_TTL_MS;
  return raw;
}

function saveAdminPassword(password) {
  localStorage.setItem(ADMIN_PASSWORD_KEY, password);
  localStorage.setItem(ADMIN_EXPIRES_KEY, String(Date.now() + getAdminSessionTtlMs()));
}

function loadAdminPassword() {
  const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || '';
  const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0);
  if (!password || !expiresAt || Date.now() >= expiresAt) {
    clearAdminPassword();
    return '';
  }
  return password;
}

function clearAdminPassword() {
  localStorage.removeItem(ADMIN_PASSWORD_KEY);
  localStorage.removeItem(ADMIN_EXPIRES_KEY);
}

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

function formatWeekSectionLabel(baseDate, startOffsetDays = 0) {
  const start = weekStart(baseDate);
  start.setDate(start.getDate() + startOffsetDays);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const startText = `${start.getFullYear()}/${String(start.getMonth() + 1).padStart(2, '0')}/${String(start.getDate()).padStart(2, '0')}`;
  if (start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth()) {
    return `${startText}-${String(end.getDate()).padStart(2, '0')}`;
  }
  const endText = `${end.getFullYear()}/${String(end.getMonth() + 1).padStart(2, '0')}/${String(end.getDate()).padStart(2, '0')}`;
  return `${startText}-${endText}`;
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
  select.innerHTML = purposes.map(p => `<option value="${p.name}" data-price="${Number(p.price || 0)}">${p.name}</option>`).join('');
  const first = purposes[0];
  if (first) document.getElementById('price').value = Number(first.price || 0);
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

function availableVenueCountForSlot(slotHour, bookings) {
  let available = 0;
  for (const venue of venues) {
    if (!bookingForSlot(venue.venue_id, slotHour, bookings)) available += 1;
  }
  return available;
}

function makeAvailabilityCell(day, hour, availableCount) {
  let cls = 'slot available';
  let text = '✓ 可預約';
  if (availableCount === 0) {
    cls = 'slot full';
    text = '🔒 已滿';
  }
  return `<td class="${cls}" data-day="${day}" data-hour="${hour}"><div class="small availability-pill">${text}</div></td>`;
}

function setAuthBadge() {
  document.getElementById('admin-view').classList.toggle('active', isAdmin);
  document.getElementById('admin-view').textContent = isAdmin ? '已登入（點我登出）' : '進階檢視';
  document.getElementById('options-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('data-settings-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('report-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('extra-income-link').style.display = isAdmin ? 'inline-block' : 'none';
  document.getElementById('open-add-modal').style.display = isAdmin ? 'inline-block' : 'none';
}

function makeSlotCell(day, hour, venueId, booking, text, rowspan = 1) {
  let cls = 'slot';
  if (booking) cls += isAdmin ? ' booked-admin' : ' booked-user';
  if (booking && selectedBookingId === booking.booking_id) cls += ' selected';
  const bookingId = booking ? booking.booking_id : '';
  const rowspanAttr = rowspan > 1 ? ` rowspan="${rowspan}"` : '';
  const draggableAttr = booking && isAdmin ? ' draggable="true"' : '';
  const content = booking
    ? `<div class="small booking-pill">${text}</div>`
    : `<div class="small">${text}</div>`;
  return `<td class="${cls}"${rowspanAttr}${draggableAttr} data-day="${day}" data-hour="${hour}" data-venue-id="${venueId}" data-booking-id="${bookingId}">${content}</td>`;
}

function bindGridEvents() {
  const slots = document.querySelectorAll('#grid-sections td.slot');
  slots.forEach(cell => {
    cell.addEventListener('click', () => {
      if (!isAdmin) return;
      const bookingId = Number(cell.dataset.bookingId || 0);
      selectedBookingId = bookingId || null;
      document.querySelectorAll('#grid-sections td.slot.selected').forEach(node => node.classList.remove('selected'));
      if (selectedBookingId) cell.classList.add('selected');
    });

    cell.addEventListener('dblclick', () => {
      if (!isAdmin) return;
      const bookingId = Number(cell.dataset.bookingId || 0);
      openBookingModalFromCell(cell, bookingId || null);
    });

    cell.addEventListener('dragstart', (event) => {
      if (!isAdmin) return;
      const bookingId = Number(cell.dataset.bookingId || 0);
      if (!bookingId) return;
      event.dataTransfer.setData('text/plain', JSON.stringify({ booking_id: bookingId }));
      event.dataTransfer.effectAllowed = 'copyMove';
    });

    cell.addEventListener('dragover', (event) => {
      if (!isAdmin) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = event.ctrlKey ? 'copy' : 'move';
    });

    cell.addEventListener('drop', async (event) => {
      if (!isAdmin) return;
      event.preventDefault();
      try {
        const payload = JSON.parse(event.dataTransfer.getData('text/plain') || '{}');
        await handleBookingDrop(cell, payload, event.ctrlKey);
      } catch (_err) {
        const msg = document.getElementById('msg');
        msg.style.color = '#dc2626';
        msg.textContent = '拖移失敗：資料格式錯誤';
      }
    });
  });
}

function findBookingByIdInCache(bookingId) {
  for (const day of Object.keys(bookingsCache)) {
    const found = (bookingsCache[day] || []).find(item => item.booking_id === bookingId);
    if (found) return found;
  }
  return null;
}

function toServerDateObj(dt) {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, '0');
  const d = String(dt.getDate()).padStart(2, '0');
  const h = String(dt.getHours()).padStart(2, '0');
  const min = String(dt.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${d} ${h}:${min}`;
}

async function handleBookingDrop(targetCell, dragData, copyMode) {
  const msg = document.getElementById('msg');
  const bookingId = Number(dragData.booking_id || 0);
  if (!bookingId) return;

  const source = findBookingByIdInCache(bookingId);
  if (!source) {
    msg.style.color = '#dc2626';
    msg.textContent = '拖移失敗：找不到來源預約';
    return;
  }

  const targetDay = targetCell.dataset.day;
  const targetHour = Number(targetCell.dataset.hour || 0);
  const targetVenueId = Number(targetCell.dataset.venueId || 0);
  if (!targetDay || !targetVenueId) return;

  const sourceStart = toDateObj(source.start_time);
  const sourceEnd = toDateObj(source.end_time);
  const durationMs = sourceEnd.getTime() - sourceStart.getTime();

  const newStart = new Date(`${targetDay}T00:00:00`);
  newStart.setHours(targetHour, sourceStart.getMinutes(), 0, 0);
  const newEnd = new Date(newStart.getTime() + durationMs);

  const basePayload = {
    venue_id: targetVenueId,
    customer: source.customer,
    purpose: source.purpose,
    price: Number(source.price || 0),
    start: toServerDateObj(newStart),
    end: toServerDateObj(newEnd),
    admin_password: adminPassword,
  };

  const resp = await fetch('/api/bookings', {
    method: copyMode ? 'POST' : 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(copyMode ? basePayload : { ...basePayload, booking_id: bookingId }),
  });
  const data = await resp.json();

  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || (copyMode ? '複製失敗' : '拖移失敗');
    return;
  }

  msg.style.color = '#16a34a';
  msg.textContent = copyMode ? `複製成功 #${data.booking_id}` : `拖移成功 #${bookingId}`;
  bookingsCache = {};
  if (!copyMode) selectedBookingId = null;
  await refresh();
}

function renderDaily(bookings) {
  const grid = document.querySelector('#grid-sections table');
  const day = document.getElementById('date').value;
  let html = '<tr><th class="sticky-left-1">時段</th>';
  for (const venue of venues) html += `<th>${venue.name}</th>`;
  html += '</tr>';

  for (let h = START_HOUR; h < END_HOUR; h++) {
    html += `<tr><td class="venue">${String(h).padStart(2, '0')}-${String(h + 1).padStart(2, '0')}</td>`;
    for (const venue of venues) {
      const b = bookingForSlot(venue.venue_id, h, bookings);
      if (b) {
        const startHour = toDateObj(b.start_time).getHours();
        const endHour = toDateObj(b.end_time).getHours();
        if (h > startHour) continue;
        const span = Math.max(1, endHour - startHour);
        const text = isAdmin ? `${b.customer}
${b.purpose || ''}
$${Number(b.price || 0).toFixed(0)}` : '已預約';
        html += makeSlotCell(day, h, venue.venue_id, b, text, span);
        continue;
      }
      html += makeSlotCell(day, h, venue.venue_id, null, '', 1);
    }
    html += '</tr>';
  }
  grid.innerHTML = html;
  bindGridEvents();
}

function isWeekend(day) {
  const weekDay = new Date(`${day}T00:00:00`).getDay();
  return weekDay === 0 || weekDay === 6;
}

function renderTwoDay(dayData, baseDate) {
  const grid = document.querySelector('#grid-sections table');
  const firstDay = new Date(`${baseDate}T00:00:00`);
  const secondDay = new Date(firstDay);
  secondDay.setDate(secondDay.getDate() + 1);
  const days = [fmtDate(firstDay), fmtDate(secondDay)];
  const weekdayNames = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

  let html = '<tr><th class="sticky-left-1">時段</th>';
  for (const day of days) {
    const weekDay = new Date(`${day}T00:00:00`).getDay();
    const weekendClass = isWeekend(day) ? ' weekend-head' : '';
    const separatorClass = day === days[1] ? ' day-block-start' : '';
    html += `<th class="${separatorClass}${weekendClass}" colspan="${venues.length}">${day}（${weekdayNames[weekDay]}）</th>`;
  }
  html += '</tr><tr><th class="sticky-left-1">場地</th>';
  for (const day of days) {
    for (const [index, venue] of venues.entries()) {
      const classes = [];
      if (day === days[1] && index === 0) classes.push('day-block-start');
      html += `<th class="${classes.join(' ')}">${venue.name}</th>`;
    }
  }
  html += '</tr>';

  for (let h = START_HOUR; h < END_HOUR; h++) {
    html += `<tr><td class="venue">${String(h).padStart(2, '0')}-${String(h + 1).padStart(2, '0')}</td>`;
    for (const day of days) {
      const bookings = dayData[day] || [];
      for (const [index, venue] of venues.entries()) {
        const b = bookingForSlot(venue.venue_id, h, bookings);
        if (b) {
          const startHour = toDateObj(b.start_time).getHours();
          const endHour = toDateObj(b.end_time).getHours();
          if (h > startHour) continue;
          const span = Math.max(1, endHour - startHour);
          const text = isAdmin ? `${b.customer}
${b.purpose || ''}
$${Number(b.price || 0).toFixed(0)}` : '已預約';
          let cell = makeSlotCell(day, h, venue.venue_id, b, text, span);
          if (day === days[1] && index === 0) cell = cell.replace('class="slot', 'class="slot day-block-start');
          html += cell;
          continue;
        }
        let cell = makeSlotCell(day, h, venue.venue_id, null, '', 1);
        if (day === days[1] && index === 0) cell = cell.replace('class="slot', 'class="slot day-block-start');
        html += cell;
      }
    }
    html += '</tr>';
  }
  grid.innerHTML = html;
  bindGridEvents();
}

function renderWeekly(weekData, baseDate, days = 14, grid, startOffsetDays = 0) {
  const start = weekStart(baseDate);
  const daysPerRow = isAdmin ? 2 : 7;
  const dates = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + startOffsetDays + i);
    dates.push(fmtDate(d));
  }

  const weekdayNames = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
  let html = '';

  for (let i = 0; i < dates.length; i += daysPerRow) {
    const blockDays = dates.slice(i, i + daysPerRow);

    html += '<tr><th class="sticky-left-1">時段</th>';
    for (const [dayIndex, day] of blockDays.entries()) {
      const weekDay = new Date(`${day}T00:00:00`).getDay();
      const weekendClass = isWeekend(day) ? ' weekend-head' : '';
      const separatorClass = dayIndex > 0 ? ' day-block-start' : '';
      const colSpan = isAdmin ? venues.length : 1;
      html += `<th class="${separatorClass}${weekendClass}" colspan="${colSpan}">${day}（${weekdayNames[(weekDay + 6) % 7]}）</th>`;
    }
    html += '</tr><tr><th class="sticky-left-1">';
    html += isAdmin ? '場地' : '可預約狀態';
    html += '</th>';

    for (const [dayIndex, day] of blockDays.entries()) {
      const isWeekendDay = isWeekend(day);
      if (isAdmin) {
        for (const [index, venue] of venues.entries()) {
          const classes = [];
          if (dayIndex > 0 && index === 0) classes.push('day-block-start');
          html += `<th class="${classes.join(' ')}">${venue.name}</th>`;
        }
      } else {
        const classes = [];
        if (dayIndex > 0) classes.push('day-block-start');
        if (isWeekendDay) classes.push('weekend-date-label');
        html += `<th class="${classes.join(' ')}">時段狀態</th>`;
      }
    }
    html += '</tr>';

    for (let h = START_HOUR; h < END_HOUR; h++) {
      html += `<tr><td class="venue">${String(h).padStart(2, '0')}-${String(h + 1).padStart(2, '0')}</td>`;
      for (const [dayIndex, day] of blockDays.entries()) {
        const bookings = weekData[day] || [];
        const isWeekendDay = isWeekend(day);

        if (!isAdmin) {
          const availableCount = availableVenueCountForSlot(h, bookings);
          let cell = makeAvailabilityCell(day, h, availableCount);
          if (dayIndex > 0) cell = cell.replace('class="slot', 'class="slot day-block-start');
          if (isWeekendDay) cell = cell.replace('class="slot', 'class="slot weekend-time');
          html += cell;
          continue;
        }

        for (const [index, venue] of venues.entries()) {
          const b = bookingForSlot(venue.venue_id, h, bookings);
          if (b) {
            const startHour = toDateObj(b.start_time).getHours();
            const endHour = toDateObj(b.end_time).getHours();
            if (h > startHour) continue;
            const span = Math.max(1, endHour - startHour);
            const text = `${b.customer}
${b.purpose || ''}
$${Number(b.price || 0).toFixed(0)}`;
            let cell = makeSlotCell(day, h, venue.venue_id, b, text, span);
            if (dayIndex > 0 && index === 0) cell = cell.replace('class="slot', 'class="slot day-block-start');
            html += cell;
            continue;
          }
          let cell = makeSlotCell(day, h, venue.venue_id, null, '', 1);
          if (dayIndex > 0 && index === 0) cell = cell.replace('class="slot', 'class="slot day-block-start');
          html += cell;
        }
      }
      html += '</tr>';
    }
  }

  grid.innerHTML = html;
  bindGridEvents();
}

async function refresh() {
  const date = document.getElementById('date').value;
  const gridSections = document.getElementById('grid-sections');
  const weekData = await loadRangeBookings(date, 14);

  if (isAdmin) {
    gridSections.innerHTML = '<div class="grid-wrap"><table id="grid-admin"></table></div>';
    renderWeekly(weekData, date, 14, document.getElementById('grid-admin'));
  } else {
    const week1Label = formatWeekSectionLabel(date, 0);
    const week2Label = formatWeekSectionLabel(date, 7);
    gridSections.innerHTML = [
      '<div class="grid-section">',
      `  <h3 class="grid-section-title">${week1Label}</h3>`,
      '  <div class="grid-wrap"><table id="grid-week-1"></table></div>',
      '</div>',
      '<div class="grid-section">',
      `  <h3 class="grid-section-title">${week2Label}</h3>`,
      '  <div class="grid-wrap"><table id="grid-week-2"></table></div>',
      '</div>',
    ].join('');
    renderWeekly(weekData, date, 7, document.getElementById('grid-week-1'), 0);
    renderWeekly(weekData, date, 7, document.getElementById('grid-week-2'), 7);
  }
  updateWeekLabel();
}

function shiftDateByDays(days) {
  const current = new Date(`${document.getElementById('date').value}T00:00:00`);
  current.setDate(current.getDate() + days);
  document.getElementById('date').value = fmtDate(current);
}

function updateWeekLabel() {
  const date = document.getElementById('date').value;
  const start = weekStart(date);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  document.getElementById('week-label').textContent = `${fmtDate(start)} ~ ${fmtDate(end)}`;
}

async function requestAdmin() {
  const password = prompt('請輸入管理員密碼：');
  if (password === null) return false;
  const resp = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  if (!resp.ok) {
    alert('密碼錯誤，無法切換進階檢視');
    return false;
  }
  isAdmin = true;
  adminPassword = password;
  saveAdminPassword(password);
  setAuthBadge();
  refresh();
  return true;
}


async function restoreAdminSession() {
  const stored = loadAdminPassword();
  if (!stored) return false;
  const resp = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: stored }),
  });
  if (!resp.ok) {
    clearAdminPassword();
    return false;
  }
  isAdmin = true;
  adminPassword = stored;
  return true;
}

function logoutAdmin() {
  isAdmin = false;
  adminPassword = '';
  selectedBookingId = null;
  clearAdminPassword();
  setAuthBadge();
  refresh();
}

function openBookingModal(data = null) {
  if (!isAdmin) return;
  modalEditingBookingId = data?.booking_id || null;
  document.getElementById('booking-modal').style.display = 'flex';
  document.getElementById('booking-modal-msg').textContent = '';
  document.getElementById('add-btn').textContent = modalEditingBookingId ? '儲存修改' : '送出預約';
  if (data) {
    const venueSelect = document.getElementById('venue');
    Array.from(venueSelect.options).forEach(option => {
      option.selected = Number(option.value) === Number(data.venue_id);
    });
    document.getElementById('customer').value = data.customer || '';
    document.getElementById('purpose').value = data.purpose || '';
    document.getElementById('price').value = Number(data.price || 0);
    document.getElementById('start').value = data.start_time.replace(' ', 'T');
    document.getElementById('end').value = data.end_time.replace(' ', 'T');
    document.getElementById('booking-note').value = data.note || '';
  }
}

function openBookingModalFromCell(cell, bookingId) {
  const day = cell.dataset.day;
  const hour = Number(cell.dataset.hour);
  const venueId = Number(cell.dataset.venueId);

  if (bookingId) {
    const dateBookings = bookingsCache[day] || [];
    const booking = dateBookings.find(item => item.booking_id === bookingId);
    if (booking) openBookingModal(booking);
    return;
  }

  const start = `${day}T${String(hour).padStart(2, '0')}:00`;
  const end = `${day}T${String(hour + 1).padStart(2, '0')}:00`;
  modalEditingBookingId = null;
  const venueSelect = document.getElementById('venue');
  Array.from(venueSelect.options).forEach(option => {
    option.selected = Number(option.value) === venueId;
  });
  document.getElementById('customer').value = '';
  document.getElementById('purpose').value = purposes[0]?.name || '';
  document.getElementById('price').value = 0;
  document.getElementById('start').value = start;
  document.getElementById('end').value = end;
  document.getElementById('booking-note').value = '';
  openBookingModal();
}

function closeBookingModal() {
  document.getElementById('booking-modal').style.display = 'none';
  document.getElementById('booking-modal-msg').textContent = '';
  modalEditingBookingId = null;
}

async function deleteSelectedBooking() {
  if (!isAdmin || !selectedBookingId) return;
  if (!confirm(`確定刪除預約 #${selectedBookingId}？`)) return;

  const resp = await fetch('/api/bookings', {
    method: 'DELETE',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ booking_id: selectedBookingId, admin_password: adminPassword }),
  });
  const data = await resp.json();
  const msg = document.getElementById('msg');
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '刪除失敗';
    return;
  }

  msg.style.color = '#16a34a';
  msg.textContent = `已刪除預約 #${selectedBookingId}`;
  selectedBookingId = null;
  bookingsCache = {};
  refresh();
}

document.getElementById('purpose').addEventListener('change', () => {
  const selected = purposes.find(p => p.name === document.getElementById('purpose').value);
  if (selected) document.getElementById('price').value = Number(selected.price || 0);
});

document.getElementById('admin-view').addEventListener('click', async () => {
  if (isAdmin) {
    logoutAdmin();
    return;
  }
  await requestAdmin();
});

document.getElementById('date').addEventListener('change', refresh);
document.getElementById('prev-week').addEventListener('click', async () => { shiftDateByDays(-7); await refresh(); });
document.getElementById('next-week').addEventListener('click', async () => { shiftDateByDays(7); await refresh(); });
document.getElementById('open-add-modal').addEventListener('click', () => openBookingModal());
document.getElementById('close-add-modal').addEventListener('click', closeBookingModal);
document.addEventListener('keydown', (event) => {
  if (event.key === 'Delete') deleteSelectedBooking();
});

document.getElementById('add-btn').addEventListener('click', async () => {
  const msg = document.getElementById('msg');
  const modalMsg = document.getElementById('booking-modal-msg');
  modalMsg.textContent = '';
  if (!isAdmin) {
    msg.style.color = '#dc2626';
    msg.textContent = '請先切換進階檢視並通過密碼驗證';
    return;
  }

  const selectedVenueIds = Array.from(document.getElementById('venue').selectedOptions).map(option => Number(option.value));
  const payload = {
    venue_ids: selectedVenueIds,
    venue_id: selectedVenueIds[0] || 0,
    customer: document.getElementById('customer').value.trim(),
    purpose: document.getElementById('purpose').value.trim(),
    price: Number(document.getElementById('price').value || 0),
    start: toServerDateTime(document.getElementById('start').value),
    end: toServerDateTime(document.getElementById('end').value),
    note: document.getElementById('booking-note').value.trim(),
    admin_password: adminPassword,
  };

  const required = [
    { key: 'venue_ids', label: '場地', check: value => Array.isArray(value) && value.length > 0 },
    { key: 'customer', label: '預約人' },
    { key: 'purpose', label: '用途' },
    { key: 'start', label: '開始時間' },
    { key: 'end', label: '結束時間' },
  ];
  const missing = required.filter(item => {
    if (item.check) return !item.check(payload[item.key]);
    return !String(payload[item.key] ?? '').trim();
  });
  if (missing.length > 0) {
    modalMsg.style.color = '#dc2626';
    modalMsg.textContent = `請填寫：${missing.map(item => item.label).join('、')}`;
    return;
  }

  const resp = await fetch('/api/bookings', {
    method: modalEditingBookingId ? 'PUT' : 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(modalEditingBookingId ? { ...payload, booking_id: modalEditingBookingId } : payload),
  });
  const data = await resp.json();

  if (!resp.ok) {
    modalMsg.style.color = '#dc2626';
    modalMsg.textContent = data.error || (modalEditingBookingId ? '更新失敗' : '新增失敗');
    return;
  }

  msg.style.color = '#16a34a';
  const createdCount = Number(data.created_count || 1);
  msg.textContent = modalEditingBookingId
    ? `更新成功 #${data.booking_id}`
    : (createdCount > 1 ? `新增成功，共建立 ${createdCount} 筆預約` : `新增成功 #${data.booking_id}`);
  bookingsCache = {};
  closeBookingModal();
  refresh();
});

(async function init() {
  const now = new Date();
  document.getElementById('date').value = now.toISOString().slice(0, 10);
  await loadVenues();
  await loadPurposes();
  await restoreAdminSession();
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
<title>系統設定</title>
<style>
:root {
  --opt-bg:#f7f7ff;
  --opt-border:#d6d9ee;
  --opt-primary:#4f46e5;
  --opt-primary-strong:#4338ca;
}
* { box-sizing: border-box; }
body {
  font-family: "Noto Sans TC", Arial, sans-serif;
  margin: 0;
  padding: 22px;
  background:
    radial-gradient(circle at 15% 0%, #e9ebff 0%, rgba(233,235,255,0) 45%),
    radial-gradient(circle at 90% 100%, #e6f5ff 0%, rgba(230,245,255,0) 40%),
    var(--opt-bg);
  font-size: 16px;
  color:#0f172a;
}
.top { max-width:900px; margin:0 auto 14px; display:flex; gap:10px; align-items:center; }
.wrap { max-width:900px; margin: 0 auto; display:grid; gap:14px; }
.panel {
  background:linear-gradient(180deg,#ffffff,#fbfcff);
  border:1px solid var(--opt-border);
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 10px 28px rgba(67,56,202,.08);
}
h1 { margin-top: 0; color:#1e3a8a; }
h3 { margin: 0 0 10px; color:#334155; }
input, button { padding:10px 12px; font-size:15px; border-radius:10px; border:1px solid #cbd5e1; }
input { width: 100%; background:#fff; min-width: 0; }
button {
  cursor:pointer;
  background:linear-gradient(180deg,var(--opt-primary),var(--opt-primary-strong));
  color:#fff;
  border:none;
  box-shadow: 0 6px 14px rgba(79,70,229,.25);
}
button:hover { filter:brightness(.98); }
.inline-help { font-size:13px; color:#475569; margin-top:6px; }
.section-row { display:grid; grid-template-columns:1fr 1fr auto; gap:10px; align-items:end; }
.hover-top-zone { position: fixed; top: 0; left: 0; right: 0; height: 82px; z-index: 40; display:flex; justify-content:center; }
.floating-actions { margin-top:8px; display:flex; gap:10px; align-items:center; padding:10px 14px; border:1px solid #d6d9ee; border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 10px 24px rgba(67,56,202,.18); opacity:0; transform:translateY(-20px); pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
.hover-top-zone:hover .floating-actions, .floating-actions:focus-within { opacity:1; transform:translateY(0); pointer-events:auto; }
@media (max-width: 900px) {
  .section-row { grid-template-columns:1fr; }
}
@media (hover: none) {
  .floating-actions { opacity:1; transform:translateY(0); pointer-events:auto; }
}
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button onclick="location.href='/'">回預約頁</button>
    <button onclick="location.href='/purposes'">資料設定</button>
    <button onclick="location.href='/reports'">費用統計</button>
    <button onclick="location.href='/extra-income'">額外收入</button>
    <button onclick="logoutAdmin()">登出管理員</button>
  </div>
</div>
<div class="top">
  <h1 style="margin:0;">系統設定</h1>
</div>
<div class="wrap">
  <div class="panel">
    <h3>登入時效設定</h3>
    <div class="section-row">
      <div>
        <label style="font-size:14px;">登入時效(分鐘)</label>
        <input id="session-ttl-minutes" type="number" min="1" step="1" />
        <div class="inline-help">控制管理員密碼在本機儲存與自動續期的有效時間。</div>
      </div>
      <div></div>
      <button onclick="saveSessionTtl()">儲存時效</button>
    </div>
  </div>

  <div class="panel">
    <h3>管理員密碼設定</h3>
    <div class="section-row">
      <div><label style="font-size:14px;">新管理員密碼</label><input id="new-admin-password" type="password" placeholder="至少4碼"/></div>
      <div><label style="font-size:14px;">再次輸入新密碼</label><input id="confirm-admin-password" type="password" placeholder="再次輸入"/></div>
      <button onclick="updateAdminPassword()">更新管理員密碼</button>
    </div>
  </div>
</div>
<script>
let adminPassword = '';
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';
const ADMIN_SESSION_TTL_MS_KEY = 'booking_admin_session_ttl_ms';
const DEFAULT_ADMIN_SESSION_TTL_MS = 2 * 60 * 60 * 1000;

function getAdminSessionTtlMs() {
  const raw = Number(localStorage.getItem(ADMIN_SESSION_TTL_MS_KEY) || 0);
  if (!raw || raw < 60 * 1000) return DEFAULT_ADMIN_SESSION_TTL_MS;
  return raw;
}

function saveAdminPassword(password) {
  localStorage.setItem(ADMIN_PASSWORD_KEY, password);
  localStorage.setItem(ADMIN_EXPIRES_KEY, String(Date.now() + getAdminSessionTtlMs()));
}

function loadAdminPassword() {
  const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || '';
  const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0);
  if (!password || !expiresAt || Date.now() >= expiresAt) {
    clearAdminPassword();
    return '';
  }
  return password;
}

function clearAdminPassword() {
  localStorage.removeItem(ADMIN_PASSWORD_KEY);
  localStorage.removeItem(ADMIN_EXPIRES_KEY);
}

function logoutAdmin() {
  clearAdminPassword();
  adminPassword = '';
  alert('已登出管理員');
}

function saveSessionTtl() {
  const minutes = Number(document.getElementById('session-ttl-minutes').value || 0);
  if (!minutes || minutes < 1) {
    alert('請輸入大於等於 1 的分鐘數');
    return;
  }
  localStorage.setItem(ADMIN_SESSION_TTL_MS_KEY, String(minutes * 60 * 1000));
  if (adminPassword) saveAdminPassword(adminPassword);
  alert('登入時效已更新');
}

async function login() {
  const pw = prompt('請輸入管理員密碼：');
  if (pw === null) return false;
  const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
  if (!resp.ok) { alert('密碼錯誤'); return false; }
  adminPassword = pw;
  saveAdminPassword(pw);
  return true;
}

async function ensureLogin() {
  if (!adminPassword) adminPassword = loadAdminPassword();
  if (adminPassword) {
    const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminPassword})});
    if (resp.ok) return true;
    clearAdminPassword();
    adminPassword = '';
  }
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

async function updateAdminPassword() {
  const pw = document.getElementById('new-admin-password').value;
  const confirm = document.getElementById('confirm-admin-password').value;
  if (!pw || pw.length < 4) { alert('新密碼至少 4 碼'); return; }
  if (pw !== confirm) { alert('兩次密碼不一致'); return; }
  try {
    await api('POST', '/api/system-settings', { new_admin_password: pw });
    adminPassword = pw;
    saveAdminPassword(pw);
    document.getElementById('new-admin-password').value = '';
    document.getElementById('confirm-admin-password').value = '';
    alert('管理員密碼已更新');
  } catch (e) { alert(e.message); }
}

(function initSessionTtl() {
  const ttlMinutes = Math.floor(getAdminSessionTtlMs() / 60000);
  const input = document.getElementById('session-ttl-minutes');
  if (input) input.value = ttlMinutes;
})();
</script>
</body>
</html>
"""

PURPOSES_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>資料設定</title>
<style>
* { box-sizing: border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin:0; padding:22px; background:#f4f6ff; color:#0f172a; }
.wrap { max-width: 1200px; margin: 0 auto; }
.top { display:flex; gap:10px; align-items:center; margin-bottom:12px; }
.card { background:#fff; border:1px solid #dbe2f0; border-radius:14px; padding:16px; box-shadow:0 10px 25px rgba(30,64,175,.08); }
.stack { display:flex; flex-direction:column; gap:14px; }
.section-title { margin: 0 0 10px; color:#1e3a8a; }
input, button { padding:10px 12px; border-radius:10px; border:1px solid #cbd5e1; font-size:15px; }
button { background:#4f46e5; color:#fff; border:none; cursor:pointer; }
.btn-danger { background:#dc2626 !important; }
.toolbar { display:flex; justify-content:flex-end; margin-bottom:10px; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th, td { border:1px solid #dbe2f0; padding:10px; text-align:left; }
th { background:#eef2ff; }
.actions{display:flex;gap:8px;}
.hover-top-zone { position: fixed; top: 0; left: 0; right: 0; height: 82px; z-index: 40; display:flex; justify-content:center; }
.floating-actions { margin-top:8px; display:flex; gap:10px; align-items:center; padding:10px 14px; border:1px solid #dbe2f0; border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 10px 24px rgba(30,64,175,.18); opacity:0; transform:translateY(-20px); pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
.hover-top-zone:hover .floating-actions, .floating-actions:focus-within { opacity:1; transform:translateY(0); pointer-events:auto; }
@media (hover:none){ .floating-actions{ opacity:1; transform:translateY(0); pointer-events:auto; } }
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button onclick="location.href='/'">回預約頁</button>
    <button onclick="location.href='/settings'">系統設定</button>
    <button onclick="location.href='/reports'">費用統計</button>
    <button onclick="location.href='/extra-income'">額外收入</button>
  </div>
</div>
<div class="wrap">
  <div class="top">
    <h1 style="margin:0;">資料設定</h1>
  </div>
  <div class="toolbar">
    <button onclick="saveAllChanges()">批次儲存</button>
  </div>
  <div class="stack">
    <div class="card">
      <h3 class="section-title">場地設定</h3>
      <input id="new-venue" placeholder="新增場地名稱" />
      <button style="margin-top:8px;" onclick="createVenue()">新增場地</button>
      <table id="venue-table"></table>
    </div>

    <div class="card">
      <h3 class="section-title">用途設定</h3>
      <div style="display:grid;grid-template-columns:2fr 1fr auto;gap:10px;align-items:end;">
        <div><label>用途名稱</label><input id="new-purpose" placeholder="新增用途名稱" /></div>
        <div><label>價格</label><input id="new-purpose-price" type="number" min="0" step="1" value="0"/></div>
        <button onclick="createPurpose()">新增用途</button>
      </div>
      <table id="purpose-table"></table>
    </div>

    <div class="card">
      <h3 class="section-title">穿線項目設定</h3>
      <div style="display:flex; gap:10px; align-items:end; flex-wrap:wrap;">
        <div><div>穿線項目</div><input id="string-item-name"/></div>
        <div><div>對應金額</div><input id="string-item-amount" type="number" min="0" step="1"/></div>
        <button id="save-string-item">儲存</button>
        <button id="cancel-string-item-edit" style="display:none; background:#64748b;">取消編輯</button>
      </div>
      <div id="string-item-msg" style="margin-top:8px;"></div>
      <table id="string-item-table"></table>
    </div>
  </div>
</div>
<script>
let adminPassword = '';
let editingStringItemId = null;
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';
const ADMIN_SESSION_TTL_MS_KEY = 'booking_admin_session_ttl_ms';
const DEFAULT_ADMIN_SESSION_TTL_MS = 2 * 60 * 60 * 1000;
function getAdminSessionTtlMs(){ const raw = Number(localStorage.getItem(ADMIN_SESSION_TTL_MS_KEY) || 0); return (!raw || raw < 60*1000) ? DEFAULT_ADMIN_SESSION_TTL_MS : raw; }
function saveAdminPassword(password){ localStorage.setItem(ADMIN_PASSWORD_KEY, password); localStorage.setItem(ADMIN_EXPIRES_KEY, String(Date.now() + getAdminSessionTtlMs())); }
function loadAdminPassword(){ const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || ''; const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0); if (!password || !expiresAt || Date.now() >= expiresAt) return ''; return password; }

async function login(){ const pw = prompt('請輸入管理員密碼：'); if (pw === null) return false; const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})}); if (!resp.ok) { alert('密碼錯誤'); return false; } adminPassword = pw; saveAdminPassword(pw); return true; }
async function ensureLogin(){ if (!adminPassword) adminPassword = loadAdminPassword(); if (adminPassword) { const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminPassword})}); if (resp.ok) return true; adminPassword = ''; } return await login(); }
async function api(method, path, payload = {}) { const ok = await ensureLogin(); if (!ok) throw new Error('need login'); payload.admin_password = adminPassword; const resp = await fetch(path, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) }); const data = await resp.json(); if (!resp.ok) throw new Error(data.error || '操作失敗'); return data; }

async function refreshPurposes(){ const purposes = await (await fetch('/api/purposes')).json(); const pt = document.getElementById('purpose-table'); pt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>價格</th><th>操作</th></tr>' + purposes.map(p => `<tr><td>${p.purpose_id}</td><td><input value="${p.name}" id="purpose-${p.purpose_id}"/></td><td><input type="number" min="0" step="1" value="${Number(p.price || 0)}" id="purpose-price-${p.purpose_id}"/></td><td class="actions"><button onclick="updatePurpose(${p.purpose_id})">儲存</button><button class="btn-danger" onclick="deletePurpose(${p.purpose_id})">刪除</button></td></tr>`).join(''); }
async function createPurpose(){ try { await api('POST', '/api/purposes', {name: document.getElementById('new-purpose').value, price: Number(document.getElementById('new-purpose-price').value || 0)}); await refreshPurposes(); } catch (e) { alert(e.message); } }
async function updatePurpose(id){ try { await api('PUT', '/api/purposes', {purpose_id: id, name: document.getElementById(`purpose-${id}`).value, price: Number(document.getElementById(`purpose-price-${id}`).value || 0)}); await refreshPurposes(); } catch (e) { alert(e.message); } }
async function deletePurpose(id){ if (!confirm('確定刪除用途？')) return; try { await api('DELETE', '/api/purposes', {purpose_id: id}); await refreshPurposes(); } catch (e) { alert(e.message); } }

async function refreshVenues(){ const venues = await (await fetch('/api/venues')).json(); const vt = document.getElementById('venue-table'); vt.innerHTML = '<tr><th>ID</th><th>名稱</th><th>操作</th></tr>' + venues.map(v => `<tr><td>${v.venue_id}</td><td><input value="${v.name}" id="venue-${v.venue_id}"/></td><td class="actions"><button onclick="updateVenue(${v.venue_id})">儲存</button><button class="btn-danger" onclick="deleteVenue(${v.venue_id})">刪除</button></td></tr>`).join(''); }
async function createVenue(){ try { await api('POST', '/api/venues', {name: document.getElementById('new-venue').value}); document.getElementById('new-venue').value=''; await refreshVenues(); } catch (e) { alert(e.message); } }
async function updateVenue(id){ try { await api('PUT', '/api/venues', {venue_id: id, name: document.getElementById(`venue-${id}`).value}); await refreshVenues(); } catch (e) { alert(e.message); } }
async function deleteVenue(id){ if (!confirm('確定刪除場地？')) return; try { await api('DELETE', '/api/venues', {venue_id: id}); await refreshVenues(); } catch (e) { alert(e.message); } }

async function saveAllChanges(){
  try {
    const purposes = await (await fetch('/api/purposes')).json();
    const venues = await (await fetch('/api/venues')).json();
    for (const p of purposes) {
      await api('PUT', '/api/purposes', {
        purpose_id: p.purpose_id,
        name: document.getElementById(`purpose-${p.purpose_id}`).value,
        price: Number(document.getElementById(`purpose-price-${p.purpose_id}`).value || 0),
      });
    }
    for (const v of venues) {
      await api('PUT', '/api/venues', {
        venue_id: v.venue_id,
        name: document.getElementById(`venue-${v.venue_id}`).value,
      });
    }
    await refreshPurposes();
    await refreshVenues();
    alert('批次儲存完成');
  } catch (e) { alert(e.message); }
}

function resetStringItemForm() {
  editingStringItemId = null;
  document.getElementById('string-item-name').value = '';
  document.getElementById('string-item-amount').value = '';
  document.getElementById('save-string-item').textContent = '儲存';
  document.getElementById('cancel-string-item-edit').style.display = 'none';
}

function editStringItem(id, name, amount) {
  editingStringItemId = Number(id);
  document.getElementById('string-item-name').value = name;
  document.getElementById('string-item-amount').value = amount;
  document.getElementById('save-string-item').textContent = '儲存';
  document.getElementById('cancel-string-item-edit').style.display = 'inline-block';
}

async function refreshStringItems() {
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/string-items/query', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '讀取失敗'); return; }
  document.getElementById('string-item-table').innerHTML = '<tr><th>項目</th><th>金額</th><th>操作</th></tr>' +
    data.items.map(row => `<tr><td>${row.name}</td><td>$${Number(row.amount).toFixed(0)}</td><td><button style="padding:6px 10px; margin-right:6px;" onclick="editStringItem(${row.string_item_id}, '${row.name.replace(/'/g, "\'")}', ${Number(row.amount)})">儲存</button><button class="btn-danger" style="padding:6px 10px;" onclick="deleteStringItem(${row.string_item_id})">刪除</button></td></tr>`).join('');
}

async function deleteStringItem(id) {
  if (!confirm(`確定刪除穿線項目 #${id}？`)) return;
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/string-items', {
    method:'DELETE', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword, string_item_id: Number(id) }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '刪除失敗'); return; }
  if (editingStringItemId === Number(id)) resetStringItemForm();
  await refreshStringItems();
}

document.getElementById('cancel-string-item-edit').addEventListener('click', resetStringItemForm);
document.getElementById('save-string-item').addEventListener('click', async () => {
  if (!await ensureLogin()) return;
  const payload = {
    admin_password: adminPassword,
    name: document.getElementById('string-item-name').value.trim(),
    amount: Number(document.getElementById('string-item-amount').value || 0),
  };
  if (editingStringItemId) payload.string_item_id = editingStringItemId;
  const resp = await fetch('/api/string-items', {
    method: editingStringItemId ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  const msg = document.getElementById('string-item-msg');
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '儲存失敗';
    return;
  }
  msg.style.color = '#16a34a';
  msg.textContent = editingStringItemId ? `更新成功 #${data.string_item_id}` : `新增成功 #${data.string_item_id}`;
  resetStringItemForm();
  await refreshStringItems();
});

(async function init(){
  await refreshPurposes();
  await refreshVenues();
  await refreshStringItems();
})();
</script>
</body>
</html>
"""


EXTRA_INCOME_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>額外收入登記</title>
<style>
* { box-sizing: border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin:0; padding:22px; background:#f4f6ff; color:#0f172a; }
.wrap { max-width: 1180px; margin: 0 auto; }
.card { background:#fff; border:1px solid #dbe2f0; border-radius:14px; padding:16px; box-shadow:0 10px 25px rgba(30,64,175,.08); }
.top { display:flex; gap:10px; align-items:center; margin-bottom:12px; }
h1 { margin:0; color:#1e3a8a; }
input, button, select { padding:10px 12px; border-radius:10px; border:1px solid #cbd5e1; font-size:15px; }
button { background:#4f46e5; color:#fff; border:none; cursor:pointer; }
.filters { display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; align-items:end; margin-bottom:12px; }
.racket-fields { display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; align-items:end; margin-bottom:12px; }
textarea { padding:10px 12px; border-radius:10px; border:1px solid #cbd5e1; font-size:15px; min-height:72px; width:100%; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th, td { border:1px solid #dbe2f0; padding:10px; text-align:left; }
th { background:#eef2ff; }
.note { min-height:20px; margin-top:8px; }
.helper { font-size:13px; color:#475569; margin-top:4px; }
.hover-top-zone { position: fixed; top: 0; left: 0; right: 0; height: 82px; z-index: 40; display:flex; justify-content:center; }
.floating-actions { margin-top:8px; display:flex; gap:10px; align-items:center; padding:10px 14px; border:1px solid #dbe2f0; border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 10px 24px rgba(30,64,175,.18); opacity:0; transform:translateY(-20px); pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
.hover-top-zone:hover .floating-actions, .floating-actions:focus-within { opacity:1; transform:translateY(0); pointer-events:auto; }
@media (hover:none){ .floating-actions{ opacity:1; transform:translateY(0); pointer-events:auto; } }
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button onclick="location.href='/'">回預約頁</button>
    <button onclick="location.href='/settings'">系統設定</button>
    <button onclick="location.href='/purposes'">資料設定</button>
    <button onclick="location.href='/reports'">去費用統計</button>
    <button onclick="logoutAdmin()">登出管理員</button>
  </div>
</div>
<div class="wrap">
  <div class="top">
    <h1>額外收入登記</h1>
  </div>
  <div class="card">
    <div class="filters">
      <div><div>日期時間</div><input id="income-time" type="datetime-local"/></div>
      <div><div>姓名</div><input id="income-customer" placeholder="例如：王小明"/></div>
      <div>
        <div>項目</div>
        <select id="income-item">
          <option value="">請選擇</option>
          <option value="球拍">球拍</option>
          <option value="球具寄賣">球具寄賣</option>
          <option value="其他">其他</option>
        </select>
      </div>
      <div><div>金額</div><input id="income-amount" type="number" min="0" step="1"/></div>
    </div>

    <div id="racket-fields" class="racket-fields" style="display:none;">
      <div><div>連絡電話</div><input id="income-phone" placeholder="例如：0912345678"/></div>
      <div><div>穿線項目</div><select id="income-racket-model"></select></div>
      <div><div>磅數</div><input id="income-tension" type="number" min="1" step="1"/></div>
      <div>
        <div>收費狀態</div>
        <select id="income-payment-status">
          <option value="">未設定</option>
          <option value="尚未付款">尚未付款</option>
          <option value="結清">結清</option>
        </select>
      </div>
      <div>
        <div>球拍狀態</div>
        <select id="income-racket-status">
          <option value="">未設定</option>
          <option value="待取回加工">待取回加工</option>
          <option value="施做中">施做中</option>
          <option value="辦公室未取">辦公室未取</option>
          <option value="客戶取回">客戶取回</option>
        </select>
      </div>
      <div>
        <div>客戶取回日</div>
        <input id="income-pickup-date" type="date"/>
      </div>
    </div>

    <div>
      <div>備註</div>
      <textarea id="income-note" placeholder="可留空"></textarea>
      <div class="helper">若項目選擇「球拍」，請先至「穿線項目設定」維護金額，再於此下拉選取。</div>
    </div>

    <div style="margin-top:10px; display:flex; gap:8px;">
      <button id="save-income">新增額外收入</button>
      <button id="cancel-edit-income" style="display:none; background:#64748b;">取消編輯</button>
    </div>
    <div id="income-msg" class="note"></div>
    <table id="income-table"></table>
  </div>
</div>
<script>
let adminPassword = '';
let editingIncomeId = null;
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';
const ADMIN_SESSION_TTL_MS_KEY = 'booking_admin_session_ttl_ms';
const DEFAULT_ADMIN_SESSION_TTL_MS = 2 * 60 * 60 * 1000;

function getAdminSessionTtlMs() {
  const raw = Number(localStorage.getItem(ADMIN_SESSION_TTL_MS_KEY) || 0);
  if (!raw || raw < 60 * 1000) return DEFAULT_ADMIN_SESSION_TTL_MS;
  return raw;
}

function saveAdminPassword(password) {
  localStorage.setItem(ADMIN_PASSWORD_KEY, password);
  localStorage.setItem(ADMIN_EXPIRES_KEY, String(Date.now() + getAdminSessionTtlMs()));
}

function loadAdminPassword() {
  const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || '';
  const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0);
  if (!password || !expiresAt || Date.now() >= expiresAt) {
    clearAdminPassword();
    return '';
  }
  return password;
}

function clearAdminPassword() {
  localStorage.removeItem(ADMIN_PASSWORD_KEY);
  localStorage.removeItem(ADMIN_EXPIRES_KEY);
}
function logoutAdmin() {
  clearAdminPassword();
  adminPassword = '';
  alert('已登出管理員');
}

function saveSessionTtl() {
  const minutes = Number(document.getElementById('session-ttl-minutes').value || 0);
  if (!minutes || minutes < 1) {
    alert('請輸入大於等於 1 的分鐘數');
    return;
  }
  localStorage.setItem(ADMIN_SESSION_TTL_MS_KEY, String(minutes * 60 * 1000));
  if (adminPassword) saveAdminPassword(adminPassword);
  alert('登入時效已更新');
}

function toServerDateTime(v) { return v.replace('T', ' '); }

function isRacketItem() {
  return document.getElementById('income-item').value.trim() === '球拍';
}

function toggleRacketFields() {
  document.getElementById('racket-fields').style.display = isRacketItem() ? 'grid' : 'none';
}

async function login() {
  const pw = prompt('請輸入管理員密碼：');
  if (pw === null) return false;
  const resp = await fetch('/api/admin/login', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})
  });
  if (!resp.ok) { alert('密碼錯誤'); return false; }
  adminPassword = pw;
  saveAdminPassword(pw);
  return true;
}

async function ensureLogin() {
  if (!adminPassword) adminPassword = loadAdminPassword();
  if (adminPassword) {
    const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminPassword})});
    if (resp.ok) return true;
    clearAdminPassword();
    adminPassword = '';
  }
  return login();
}


async function loadStringItems() {
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/string-items/query', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword }),
  });
  const data = await resp.json();
  if (!resp.ok) { return; }
  const select = document.getElementById('income-racket-model');
  select.innerHTML = '<option value="">請選擇穿線項目</option>' +
    data.items.map(row => `<option value="${row.name}" data-amount="${Number(row.amount || 0)}">${row.name}（$${Number(row.amount || 0).toFixed(0)}）</option>`).join('');
}

function syncAmountByStringItem() {
  if (!isRacketItem()) return;
  const select = document.getElementById('income-racket-model');
  const option = select.options[select.selectedIndex];
  if (!option) return;
  const amount = Number(option.getAttribute('data-amount') || 0);
  if (amount > 0) document.getElementById('income-amount').value = String(amount);
}

function racketSummary(row) {
  if (row.item !== '球拍') return row.note || '';
  const parts = [];
  if (row.contact_phone) parts.push(`電話：${row.contact_phone}`);
  if (row.racket_model) parts.push(`穿線：${row.racket_model}`);
  if (row.string_tension) parts.push(`磅數：${row.string_tension}`);
  if (row.payment_status) parts.push(`收費：${row.payment_status}`);
  if (row.racket_status) parts.push(`球拍：${row.racket_status}`);
  if (row.pickup_date) parts.push(`取回日：${row.pickup_date}`);
  if (row.note) parts.push(`備註：${row.note}`);
  return parts.join('｜');
}

async function refreshList() {
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/extra-incomes/query', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '讀取失敗'); return; }

  const table = document.getElementById('income-table');
  table.innerHTML = '<tr><th>時間</th><th>姓名</th><th>項目</th><th>金額</th><th>詳細/備註</th><th>操作</th></tr>' +
    data.items.map(row => `<tr><td>${row.income_time}</td><td>${row.customer}</td><td>${row.item}</td><td>$${Number(row.amount).toFixed(0)}</td><td>${racketSummary(row)}</td><td><button style="padding:6px 10px; margin-right:6px;" onclick="startEditIncome(${row.income_id})">編輯</button><button style="padding:6px 10px; background:#dc2626;" onclick="deleteIncome(${row.income_id})">刪除</button></td></tr>`).join('');
}

function resetIncomeForm() {
  editingIncomeId = null;
  document.getElementById('save-income').textContent = '新增額外收入';
  document.getElementById('cancel-edit-income').style.display = 'none';
  document.getElementById('income-customer').value = '';
  document.getElementById('income-item').value = '';
  document.getElementById('income-amount').value = '';
  document.getElementById('income-note').value = '';
  document.getElementById('income-phone').value = '';
  document.getElementById('income-racket-model').value = '';
  document.getElementById('income-tension').value = '';
  document.getElementById('income-payment-status').value = '';
  document.getElementById('income-racket-status').value = '';
  document.getElementById('income-pickup-date').value = '';
  toggleRacketFields();
}

async function startEditIncome(incomeId) {
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/extra-incomes/query', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '讀取失敗'); return; }
  const row = data.items.find(item => Number(item.income_id) === Number(incomeId));
  if (!row) { alert('找不到資料'); return; }

  editingIncomeId = Number(row.income_id);
  document.getElementById('save-income').textContent = '儲存修改';
  document.getElementById('cancel-edit-income').style.display = 'inline-block';
  document.getElementById('income-time').value = row.income_time.replace(' ', 'T');
  document.getElementById('income-customer').value = row.customer || '';
  document.getElementById('income-item').value = row.item || '';
  document.getElementById('income-amount').value = Number(row.amount || 0);
  document.getElementById('income-note').value = row.note || '';
  document.getElementById('income-phone').value = row.contact_phone || '';
  const modelSelect = document.getElementById('income-racket-model');
  if (row.racket_model && !Array.from(modelSelect.options).some(opt => opt.value === row.racket_model)) {
    modelSelect.innerHTML += `<option value="${row.racket_model}">${row.racket_model}</option>`;
  }
  modelSelect.value = row.racket_model || '';
  document.getElementById('income-tension').value = row.string_tension || '';
  document.getElementById('income-payment-status').value = row.payment_status || '';
  document.getElementById('income-racket-status').value = row.racket_status || '';
  document.getElementById('income-pickup-date').value = row.pickup_date || '';
  toggleRacketFields();
}

async function deleteIncome(incomeId) {
  if (!confirm(`確定刪除收入 #${incomeId}？`)) return;
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/extra-incomes', {
    method:'DELETE',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword, income_id: Number(incomeId) }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '刪除失敗'); return; }
  if (editingIncomeId === Number(incomeId)) resetIncomeForm();
  await refreshList();
}

document.getElementById('income-item').addEventListener('change', toggleRacketFields);
document.getElementById('income-racket-model').addEventListener('change', syncAmountByStringItem);
document.getElementById('cancel-edit-income').addEventListener('click', resetIncomeForm);

document.getElementById('save-income').addEventListener('click', async () => {
  const msg = document.getElementById('income-msg');
  msg.textContent = '';
  if (!await ensureLogin()) return;

  const payload = {
    admin_password: adminPassword,
    income_time: toServerDateTime(document.getElementById('income-time').value),
    customer: document.getElementById('income-customer').value.trim(),
    item: document.getElementById('income-item').value.trim(),
    amount: Number(document.getElementById('income-amount').value || 0),
    note: document.getElementById('income-note').value.trim(),
    contact_phone: document.getElementById('income-phone').value.trim(),
    racket_model: document.getElementById('income-racket-model').value.trim(),
    string_tension: document.getElementById('income-tension').value.trim(),
    payment_status: document.getElementById('income-payment-status').value.trim(),
    racket_status: document.getElementById('income-racket-status').value.trim(),
    pickup_date: document.getElementById('income-pickup-date').value.trim(),
  };

  if (editingIncomeId) payload.income_id = editingIncomeId;
  const resp = await fetch('/api/extra-incomes', {
    method: editingIncomeId ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '新增失敗';
    return;
  }

  msg.style.color = '#16a34a';
  msg.textContent = editingIncomeId ? `更新成功 #${data.income_id}` : `新增成功 #${data.income_id}`;
  resetIncomeForm();
  await refreshList();
});

(function init() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const h = String(now.getHours()).padStart(2, '0');
  const min = String(now.getMinutes()).padStart(2, '0');
  document.getElementById('income-time').value = `${y}-${m}-${d}T${h}:${min}`;
  toggleRacketFields();
  loadStringItems();
  refreshList();
})();
</script>
</body>
</html>
"""


STRING_ITEMS_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>穿線項目設定</title>
<style>
* { box-sizing: border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin:0; padding:22px; background:#f4f6ff; color:#0f172a; }
.wrap { max-width: 920px; margin: 0 auto; }
.card { background:#fff; border:1px solid #dbe2f0; border-radius:14px; padding:16px; box-shadow:0 10px 25px rgba(30,64,175,.08); }
.top { display:flex; gap:10px; align-items:center; margin-bottom:12px; }
input, button { padding:10px 12px; border-radius:10px; border:1px solid #cbd5e1; font-size:15px; }
button { background:#4f46e5; color:#fff; border:none; cursor:pointer; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th, td { border:1px solid #dbe2f0; padding:10px; text-align:left; }
th { background:#eef2ff; }
.hover-top-zone { position: fixed; top: 0; left: 0; right: 0; height: 82px; z-index: 40; display:flex; justify-content:center; }
.floating-actions { margin-top:8px; display:flex; gap:10px; align-items:center; padding:10px 14px; border:1px solid #dbe2f0; border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 10px 24px rgba(30,64,175,.18); opacity:0; transform:translateY(-20px); pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
.hover-top-zone:hover .floating-actions, .floating-actions:focus-within { opacity:1; transform:translateY(0); pointer-events:auto; }
@media (hover:none){ .floating-actions{ opacity:1; transform:translateY(0); pointer-events:auto; } }
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button onclick="location.href='/'">回預約頁</button>
    <button onclick="location.href='/settings'">系統設定</button>
    <button onclick="location.href='/purposes'">資料設定</button>
    <button onclick="location.href='/extra-income'">額外收入</button>
  </div>
</div>
<div class="wrap">
  <div class="top">
    <h1>穿線項目設定</h1>
  </div>
  <div class="card">
    <div style="display:flex; gap:10px; align-items:end; flex-wrap:wrap;">
      <div><div>穿線項目</div><input id="string-item-name"/></div>
      <div><div>對應金額</div><input id="string-item-amount" type="number" min="0" step="1"/></div>
      <button id="save-string-item">新增項目</button>
      <button id="cancel-string-item-edit" style="display:none; background:#64748b;">取消編輯</button>
    </div>
    <div id="string-item-msg" style="margin-top:8px;"></div>
    <table id="string-item-table"></table>
  </div>
</div>
<script>
let adminPassword = '';
let editingStringItemId = null;
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';

function loadAdminPassword() {
  const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || '';
  const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0);
  if (!password || !expiresAt || Date.now() >= expiresAt) return '';
  return password;
}

async function ensureLogin() {
  if (!adminPassword) adminPassword = loadAdminPassword();
  if (!adminPassword) {
    const pw = prompt('請輸入管理員密碼：');
    if (pw === null) return false;
    const resp = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})});
    if (!resp.ok) { alert('密碼錯誤'); return false; }
    adminPassword = pw;
  }
  return true;
}

function resetForm() {
  editingStringItemId = null;
  document.getElementById('string-item-name').value = '';
  document.getElementById('string-item-amount').value = '';
  document.getElementById('save-string-item').textContent = '儲存';
  document.getElementById('cancel-string-item-edit').style.display = 'none';
}

async function refreshStringItems() {
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/string-items/query', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '讀取失敗'); return; }
  document.getElementById('string-item-table').innerHTML = '<tr><th>項目</th><th>金額</th><th>操作</th></tr>' +
    data.items.map(row => `<tr><td>${row.name}</td><td>$${Number(row.amount).toFixed(0)}</td><td><button style="padding:6px 10px; margin-right:6px;" onclick="editStringItem(${row.string_item_id}, '${row.name.replace(/'/g, "\'")}', ${Number(row.amount)})">儲存</button><button class="btn-danger" style="padding:6px 10px;" onclick="deleteStringItem(${row.string_item_id})">刪除</button></td></tr>`).join('');
}

function editStringItem(id, name, amount) {
  editingStringItemId = Number(id);
  document.getElementById('string-item-name').value = name;
  document.getElementById('string-item-amount').value = amount;
  document.getElementById('save-string-item').textContent = '儲存';
  document.getElementById('cancel-string-item-edit').style.display = 'inline-block';
}

async function deleteStringItem(id) {
  if (!confirm(`確定刪除穿線項目 #${id}？`)) return;
  if (!await ensureLogin()) return;
  const resp = await fetch('/api/string-items', {
    method:'DELETE', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword, string_item_id: Number(id) }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '刪除失敗'); return; }
  if (editingStringItemId === Number(id)) resetForm();
  await refreshStringItems();
}

document.getElementById('cancel-string-item-edit').addEventListener('click', resetForm);
document.getElementById('save-string-item').addEventListener('click', async () => {
  if (!await ensureLogin()) return;
  const payload = {
    admin_password: adminPassword,
    name: document.getElementById('string-item-name').value.trim(),
    amount: Number(document.getElementById('string-item-amount').value || 0),
  };
  if (editingStringItemId) payload.string_item_id = editingStringItemId;
  const resp = await fetch('/api/string-items', {
    method: editingStringItemId ? 'PUT' : 'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload),
  });
  const data = await resp.json();
  const msg = document.getElementById('string-item-msg');
  if (!resp.ok) {
    msg.style.color = '#dc2626';
    msg.textContent = data.error || '儲存失敗';
    return;
  }
  msg.style.color = '#16a34a';
  msg.textContent = editingStringItemId ? `更新成功 #${data.string_item_id}` : `新增成功 #${data.string_item_id}`;
  resetForm();
  await refreshStringItems();
});

refreshStringItems();
</script>
</body>
</html>
"""


REPORT_PAGE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>預約費用統計</title>
<style>
* { box-sizing: border-box; }
body { font-family: "Noto Sans TC", Arial, sans-serif; margin:0; padding:22px; background:#f4f6ff; color:#0f172a; }
.wrap { max-width: 980px; margin: 0 auto; }
.card { background:#fff; border:1px solid #dbe2f0; border-radius:14px; padding:16px; box-shadow:0 10px 25px rgba(30,64,175,.08); }
.top { display:flex; gap:10px; align-items:center; margin-bottom:12px; }
h1 { margin:0; color:#1e3a8a; }
input, button { padding:10px 12px; border-radius:10px; border:1px solid #cbd5e1; font-size:15px; }
button { background:#4f46e5; color:#fff; border:none; cursor:pointer; }
.filters { display:flex; flex-wrap:wrap; gap:10px; align-items:end; margin-bottom:12px; }
table { width:100%; border-collapse:collapse; margin-top:8px; }
th, td { border:1px solid #dbe2f0; padding:10px; text-align:left; }
th { background:#eef2ff; }
.total { margin-top:10px; font-weight:700; color:#1e3a8a; }
.section-title { margin-top:14px; font-weight:700; color:#334155; }
.pagination { margin-top:8px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
.pagination button { width:auto; padding:8px 12px; font-size:14px; background:#6366f1; }
.pagination button:disabled { opacity:.45; cursor:not-allowed; }
.pagination .info { color:#475569; font-size:14px; }
.hover-top-zone { position: fixed; top: 0; left: 0; right: 0; height: 82px; z-index: 40; display:flex; justify-content:center; }
.floating-actions { margin-top:8px; display:flex; gap:10px; align-items:center; padding:10px 14px; border:1px solid #dbe2f0; border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 10px 24px rgba(30,64,175,.18); opacity:0; transform:translateY(-20px); pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
.hover-top-zone:hover .floating-actions, .floating-actions:focus-within { opacity:1; transform:translateY(0); pointer-events:auto; }
@media (hover:none){ .floating-actions{ opacity:1; transform:translateY(0); pointer-events:auto; } }
</style>
</head>
<body>
<div class="hover-top-zone">
  <div class="floating-actions">
    <button onclick="location.href='/'">回預約頁</button>
    <button onclick="location.href='/settings'">系統設定</button>
    <button onclick="location.href='/purposes'">資料設定</button>
    <button onclick="location.href='/extra-income'">額外收入登記</button>
    <button onclick="logoutAdmin()">登出管理員</button>
  </div>
</div>
<div class="wrap">
  <div class="top">
    <h1>預約費用統計</h1>
  </div>
  <div class="card">
    <div class="filters">
      <div><div>開始日期</div><input id="start-date" type="date"/></div>
      <div><div>結束日期</div><input id="end-date" type="date"/></div>
      <div><div>姓名</div><input id="customer-filter" placeholder="留空=全部"/></div>
      <button id="query-btn">查詢</button>
      <button id="export-btn">匯出 Excel</button>
    </div>
    <div class="section-title">預約收入明細</div>
    <table id="report-table"></table>
    <div id="booking-pagination" class="pagination"></div>
    <div class="section-title">額外收入明細</div>
    <table id="extra-income-table"></table>
    <div id="extra-pagination" class="pagination"></div>
    <div class="total" id="grand-total"></div>
  </div>
</div>
<script>
let adminPassword = '';
let bookingPage = 1;
let extraIncomePage = 1;
const PAGE_SIZE = 10;
const ADMIN_PASSWORD_KEY = 'booking_admin_password';
const ADMIN_EXPIRES_KEY = 'booking_admin_expires_at';
const ADMIN_SESSION_TTL_MS_KEY = 'booking_admin_session_ttl_ms';
const DEFAULT_ADMIN_SESSION_TTL_MS = 2 * 60 * 60 * 1000;

function getAdminSessionTtlMs() {
  const raw = Number(localStorage.getItem(ADMIN_SESSION_TTL_MS_KEY) || 0);
  if (!raw || raw < 60 * 1000) return DEFAULT_ADMIN_SESSION_TTL_MS;
  return raw;
}

function saveAdminPassword(password) {
  localStorage.setItem(ADMIN_PASSWORD_KEY, password);
  localStorage.setItem(ADMIN_EXPIRES_KEY, String(Date.now() + getAdminSessionTtlMs()));
}

function loadAdminPassword() {
  const password = localStorage.getItem(ADMIN_PASSWORD_KEY) || '';
  const expiresAt = Number(localStorage.getItem(ADMIN_EXPIRES_KEY) || 0);
  if (!password || !expiresAt || Date.now() >= expiresAt) {
    clearAdminPassword();
    return '';
  }
  return password;
}

function clearAdminPassword() {
  localStorage.removeItem(ADMIN_PASSWORD_KEY);
  localStorage.removeItem(ADMIN_EXPIRES_KEY);
}

function logoutAdmin() {
  clearAdminPassword();
  adminPassword = '';
  alert('已登出管理員');
}

function saveSessionTtl() {
  const minutes = Number(document.getElementById('session-ttl-minutes').value || 0);
  if (!minutes || minutes < 1) {
    alert('請輸入大於等於 1 的分鐘數');
    return;
  }
  localStorage.setItem(ADMIN_SESSION_TTL_MS_KEY, String(minutes * 60 * 1000));
  if (adminPassword) saveAdminPassword(adminPassword);
  alert('登入時效已更新');
}

async function login() {
  const pw = prompt('請輸入管理員密碼：');
  if (pw === null) return false;
  const resp = await fetch('/api/admin/login', {
    method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: pw})
  });
  if (!resp.ok) { alert('密碼錯誤'); return false; }
  adminPassword = pw;
  saveAdminPassword(pw);
  return true;
}

async function refreshReport() {
  if (!adminPassword) adminPassword = loadAdminPassword();
  if (adminPassword) {
    const check = await fetch('/api/admin/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({password: adminPassword})});
    if (!check.ok) {
      clearAdminPassword();
      adminPassword = '';
    }
  }
  if (!adminPassword) {
    const ok = await login();
    if (!ok) return;
  }
  const start = document.getElementById('start-date').value;
  const end = document.getElementById('end-date').value;
  const customer = document.getElementById('customer-filter').value.trim();
  const resp = await fetch('/api/reports/fees', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      admin_password: adminPassword,
      start_date: start,
      end_date: end,
      customer,
      booking_page: bookingPage,
      extra_income_page: extraIncomePage,
      page_size: PAGE_SIZE,
    }),
  });
  const data = await resp.json();
  if (!resp.ok) { alert(data.error || '查詢失敗'); return; }

  const table = document.getElementById('report-table');
  table.innerHTML = '<tr><th>姓名</th><th>用途</th><th>開始時間</th><th>結束時間</th><th>新增時間</th><th>預約費用</th></tr>' +
    data.booking_records.map(row => `<tr><td>${row.customer}</td><td>${row.purpose}</td><td>${row.start_time}</td><td>${row.end_time}</td><td>${row.created_at || ''}</td><td>$${Number(row.price).toFixed(0)}</td></tr>`).join('');
  renderPagination('booking-pagination', 'booking', data.booking_page, data.booking_total_pages, data.booking_total_records);

  const extraTable = document.getElementById('extra-income-table');
  extraTable.innerHTML = '<tr><th>時間</th><th>姓名</th><th>項目</th><th>金額</th><th>詳細/備註</th></tr>' +
    data.extra_income_records.map(row => {
      const details = row.item === '球拍'
        ? [
            row.contact_phone ? `電話：${row.contact_phone}` : '',
            row.racket_model ? `穿線：${row.racket_model}` : '',
            row.string_tension ? `磅數：${row.string_tension}` : '',
            row.payment_status ? `收費：${row.payment_status}` : '',
            row.racket_status ? `球拍：${row.racket_status}` : '',
            row.pickup_date ? `取回日：${row.pickup_date}` : '',
            row.note ? `備註：${row.note}` : '',
          ].filter(Boolean).join('｜')
        : (row.note || '');
      return `<tr><td>${row.income_time}</td><td>${row.customer}</td><td>${row.item}</td><td>$${Number(row.amount).toFixed(0)}</td><td>${details}</td></tr>`;
    }).join('');
  renderPagination('extra-pagination', 'extra', data.extra_income_page, data.extra_income_total_pages, data.extra_income_total_records);

  document.getElementById('grand-total').textContent = `總計（預約）：$${Number(data.booking_grand_total).toFixed(0)}｜總計（額外收入）：$${Number(data.extra_income_grand_total).toFixed(0)}｜整體總計：$${Number(data.grand_total).toFixed(0)}`;
}

function renderPagination(containerId, type, page, totalPages, totalRecords) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const safeTotalPages = Math.max(1, Number(totalPages || 1));
  const safePage = Math.min(Math.max(1, Number(page || 1)), safeTotalPages);
  const disabledPrev = safePage <= 1 ? 'disabled' : '';
  const disabledNext = safePage >= safeTotalPages ? 'disabled' : '';
  container.innerHTML = `
    <button ${disabledPrev} data-type="${type}" data-action="prev">上一頁</button>
    <button ${disabledNext} data-type="${type}" data-action="next">下一頁</button>
    <span class="info">第 ${safePage} / ${safeTotalPages} 頁（共 ${Number(totalRecords || 0)} 筆）</span>
  `;
}



async function exportReport() {
  if (!adminPassword) adminPassword = loadAdminPassword();
  if (!adminPassword) {
    const ok = await login();
    if (!ok) return;
  }
  const start = document.getElementById('start-date').value;
  const end = document.getElementById('end-date').value;
  const customer = document.getElementById('customer-filter').value.trim();
  const resp = await fetch('/api/reports/fees/export', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ admin_password: adminPassword, start_date: start, end_date: end, customer }),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({ error: '匯出失敗' }));
    alert(data.error || '匯出失敗');
    return;
  }
  const blob = await resp.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  const customerPart = customer ? `_${customer}` : '';
  a.href = url;
  a.download = `費用統計_${start}_${end}${customerPart}.xls`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

document.getElementById('query-btn').addEventListener('click', () => {
  bookingPage = 1;
  extraIncomePage = 1;
  refreshReport();
});
document.getElementById('export-btn').addEventListener('click', exportReport);
document.addEventListener('click', (event) => {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const type = button.dataset.type;
  const action = button.dataset.action;
  if (type === 'booking') {
    bookingPage = Math.max(1, bookingPage + (action === 'next' ? 1 : -1));
  } else if (type === 'extra') {
    extraIncomePage = Math.max(1, extraIncomePage + (action === 'next' ? 1 : -1));
  }
  refreshReport();
});
(function init() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const ymd = d => d.toISOString().slice(0, 10);
  document.getElementById('start-date').value = ymd(start);
  document.getElementById('end-date').value = ymd(now);
})();
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
        if parsed.path in ["/options", "/settings"]:
            self._send_html(OPTIONS_PAGE)
            return
        if parsed.path == "/purposes":
            self._send_html(PURPOSES_PAGE)
            return
        if parsed.path == "/reports":
            self._send_html(REPORT_PAGE)
            return
        if parsed.path == "/extra-income":
            self._send_html(EXTRA_INCOME_PAGE)
            return
        if parsed.path == "/string-items":
            self._send_html(STRING_ITEMS_PAGE)
            return
        if parsed.path == "/api/venues":
            with manager_lock:
                venues = [v.__dict__ for v in manager.list_venues()]
            self._send_json(venues)
            return
        if parsed.path == "/api/purposes":
            with manager_lock:
                purposes = [purpose_to_dict(p) for p in manager.list_purposes()]
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
            if secrets.compare_digest(password, get_admin_password()):
                self._send_json({"ok": True})
            else:
                self._send_json({"error": "密碼錯誤"}, status=HTTPStatus.UNAUTHORIZED)
            return

        if parsed.path == "/api/system-settings":
            try:
                self._check_admin_password(payload)
                new_password = str(payload.get("new_admin_password", "")).strip()
                if len(new_password) < 4:
                    raise ValueError("新管理員密碼至少 4 碼")
                with manager_lock:
                    manager.set_setting("admin_password", new_password)
                self._send_json({"ok": True})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/string-items":
            try:
                self._check_admin_password(payload)
                with manager_lock:
                    item = manager.add_string_item(
                        name=str(payload.get("name", "")),
                        amount=payload.get("amount", 0),
                    )
                self._send_json(string_item_to_dict(item), status=HTTPStatus.CREATED)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/string-items/query":
            try:
                self._check_admin_password(payload)
                with manager_lock:
                    items = [string_item_to_dict(item) for item in manager.list_string_items()]
                self._send_json({"items": items})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
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
                        item = manager.add_purpose(name, payload.get("price", 0))
                        self._send_json(item.__dict__, status=HTTPStatus.CREATED)
                return
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

        if parsed.path == "/api/extra-incomes":
            try:
                self._check_admin_password(payload)
                with manager_lock:
                    income = manager.add_extra_income(
                        customer=str(payload.get("customer", "")),
                        item=str(payload.get("item", "")),
                        amount=payload.get("amount", 0),
                        income_time=str(payload.get("income_time", "")),
                        note=str(payload.get("note", "")),
                        contact_phone=str(payload.get("contact_phone", "")),
                        racket_model=str(payload.get("racket_model", "")),
                        string_tension=payload.get("string_tension", None),
                        payment_status=str(payload.get("payment_status", "")),
                        racket_status=str(payload.get("racket_status", "")),
                        pickup_date=str(payload.get("pickup_date", "")),
                    )
                self._send_json(extra_income_to_dict(income), status=HTTPStatus.CREATED)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/extra-incomes/query":
            try:
                self._check_admin_password(payload)
                start_date = str(payload.get("start_date", "")).strip()
                end_date = str(payload.get("end_date", "")).strip()
                customer = str(payload.get("customer", "")).strip()
                with manager_lock:
                    items = [
                        extra_income_to_dict(item)
                        for item in manager.list_extra_incomes(start_date=start_date, end_date=end_date, customer=customer)
                    ]
                self._send_json({"items": items})
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/reports/fees/export":
            try:
                self._check_admin_password(payload)
                start_date = str(payload.get("start_date", "")).strip()
                end_date = str(payload.get("end_date", "")).strip()
                if not start_date or not end_date:
                    raise ValueError("請提供開始與結束日期")
                customer = str(payload.get("customer", "")).strip()
                with manager_lock:
                    booking_items = manager.summarize_fees(start_date, end_date, customer)
                    all_bookings = [booking_to_dict(item) for item in manager.list_bookings()]
                    all_extra_records = [
                        extra_income_to_dict(item)
                        for item in manager.list_extra_incomes(start_date=start_date, end_date=end_date, customer=customer)
                    ]

                booking_records = []
                for row in all_bookings:
                    booking_date = row["start_time"][:10]
                    if booking_date < start_date or booking_date > end_date:
                        continue
                    if customer and row["customer"] != customer:
                        continue
                    booking_records.append(row)

                extra_records = []
                for row in all_extra_records:
                    if row["item"] != "球拍":
                        extra_records.append(row)
                        continue
                    if row["payment_status"] == "結清" and row["pickup_date"]:
                        extra_records.append(row)

                booking_map = {
                    item["customer"]: {
                        "customer": item["customer"],
                        "booking_total": float(item["total_fee"]),
                        "extra_income_total": 0.0,
                    }
                    for item in booking_items
                }
                for row in extra_records:
                    if row["customer"] not in booking_map:
                        booking_map[row["customer"]] = {
                            "customer": row["customer"],
                            "booking_total": 0.0,
                            "extra_income_total": 0.0,
                        }
                    booking_map[row["customer"]]["extra_income_total"] += float(row["amount"])

                summary_rows = []
                for item in booking_map.values():
                    total_fee = float(item["booking_total"] + item["extra_income_total"])
                    summary_rows.append((item["customer"], item["booking_total"], item["extra_income_total"], total_fee))
                summary_rows.sort(key=lambda row: (-row[3], row[0]))

                booking_grand_total = sum(float(item["total_fee"]) for item in booking_items)
                extra_income_grand_total = sum(float(row["amount"]) for row in extra_records)
                grand_total = booking_grand_total + extra_income_grand_total

                def build_racket_details(row: Dict[str, Any]) -> str:
                    if row["item"] != "球拍":
                        return row["note"] or ""
                    return "｜".join(
                        part for part in [
                            f"電話：{row['contact_phone']}" if row["contact_phone"] else "",
                            f"穿線：{row['racket_model']}" if row["racket_model"] else "",
                            f"磅數：{row['string_tension']}" if row["string_tension"] else "",
                            f"收費：{row['payment_status']}" if row["payment_status"] else "",
                            f"球拍：{row['racket_status']}" if row["racket_status"] else "",
                            f"取回日：{row['pickup_date']}" if row["pickup_date"] else "",
                            f"備註：{row['note']}" if row["note"] else "",
                        ]
                        if part
                    )

                html_parts = [
                    "<html><head><meta charset='utf-8'>",
                    "<style>",
                    "body{font-family:'Microsoft JhengHei',Arial,sans-serif;color:#0f172a;padding:14px;}",
                    "h2{color:#1e3a8a;margin:0 0 10px;}",
                    "h3{color:#334155;margin:18px 0 8px;}",
                    "table{border-collapse:collapse;width:100%;margin-bottom:10px;}",
                    "th,td{border:1px solid #94a3b8;padding:8px 10px;text-align:left;}",
                    "th{background:#e2e8f0;font-weight:700;}",
                    ".total{font-weight:700;color:#1e3a8a;margin:8px 0 12px;}",
                    "</style></head><body>",
                    f"<h2>預約費用統計（{escape(start_date)} ~ {escape(end_date)}）</h2>",
                    "<h3>預約收入明細</h3>",
                    "<table><tr><th>姓名</th><th>用途</th><th>開始時間</th><th>結束時間</th><th>新增時間</th><th>預約費用</th><th>備註</th></tr>",
                ]
                for row in booking_records:
                    html_parts.append(
                        "<tr>"
                        f"<td>{escape(str(row['customer']))}</td>"
                        f"<td>{escape(str(row['purpose']))}</td>"
                        f"<td>{escape(str(row['start_time']))}</td>"
                        f"<td>{escape(str(row['end_time']))}</td>"
                        f"<td>{escape(str(row.get('created_at', '')))}</td>"
                        f"<td>${float(row['price']):.0f}</td>"
                        f"<td>{escape(str(row.get('note', '')))}</td>"
                        "</tr>"
                    )
                html_parts.append("</table>")
                html_parts.append("<h3>客戶合計（預約 + 額外收入）</h3>")
                html_parts.append("<table><tr><th>姓名</th><th>預約費用</th><th>額外收入</th><th>合計</th></tr>")
                for row in summary_rows:
                    html_parts.append(
                        "<tr>"
                        f"<td>{escape(str(row[0]))}</td>"
                        f"<td>${row[1]:.0f}</td>"
                        f"<td>${row[2]:.0f}</td>"
                        f"<td>${row[3]:.0f}</td>"
                        "</tr>"
                    )
                html_parts.append("</table>")
                html_parts.append("<h3>額外收入明細</h3>")
                html_parts.append("<table><tr><th>時間</th><th>姓名</th><th>項目</th><th>金額</th><th>詳細/備註</th></tr>")
                for row in extra_records:
                    html_parts.append(
                        "<tr>"
                        f"<td>{escape(str(row['income_time']))}</td>"
                        f"<td>{escape(str(row['customer']))}</td>"
                        f"<td>{escape(str(row['item']))}</td>"
                        f"<td>${float(row['amount']):.0f}</td>"
                        f"<td>{escape(build_racket_details(row))}</td>"
                        "</tr>"
                    )
                html_parts.append("</table>")
                html_parts.append(
                    f"<div class='total'>總計（預約）：${booking_grand_total:.0f}｜總計（額外收入）：${extra_income_grand_total:.0f}｜整體總計：${grand_total:.0f}</div>"
                )
                html_parts.append("</body></html>")

                body = "".join(html_parts).encode("utf-8-sig")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/vnd.ms-excel; charset=utf-8")
                self.send_header("Content-Disposition", "attachment; filename=fee_report.xls")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path == "/api/reports/fees":
            try:
                self._check_admin_password(payload)
                start_date = str(payload.get("start_date", "")).strip()
                end_date = str(payload.get("end_date", "")).strip()
                if not start_date or not end_date:
                    raise ValueError("請提供開始與結束日期")
                customer = str(payload.get("customer", "")).strip()
                page_size = max(1, min(100, int(payload.get("page_size", 10) or 10)))
                booking_page = max(1, int(payload.get("booking_page", 1) or 1))
                extra_income_page = max(1, int(payload.get("extra_income_page", 1) or 1))
                with manager_lock:
                    booking_items = manager.summarize_fees(start_date, end_date, customer)
                    all_bookings = [booking_to_dict(item) for item in manager.list_bookings()]
                    all_extra_records = [
                        extra_income_to_dict(item)
                        for item in manager.list_extra_incomes(start_date=start_date, end_date=end_date, customer=customer)
                    ]

                booking_records = []
                for row in all_bookings:
                    booking_date = row["start_time"][:10]
                    if booking_date < start_date or booking_date > end_date:
                        continue
                    if customer and row["customer"] != customer:
                        continue
                    booking_records.append(row)

                extra_records = []
                for row in all_extra_records:
                    if row["item"] != "球拍":
                        extra_records.append(row)
                        continue
                    if row["payment_status"] == "結清" and row["pickup_date"]:
                        extra_records.append(row)

                booking_map = {
                    item["customer"]: {
                        "customer": item["customer"],
                        "booking_total": float(item["total_fee"]),
                        "extra_income_total": 0.0,
                    }
                    for item in booking_items
                }
                for row in extra_records:
                    if row["customer"] not in booking_map:
                        booking_map[row["customer"]] = {
                            "customer": row["customer"],
                            "booking_total": 0.0,
                            "extra_income_total": 0.0,
                        }
                    booking_map[row["customer"]]["extra_income_total"] += float(row["amount"])

                items = []
                for item in booking_map.values():
                    total_fee = float(item["booking_total"] + item["extra_income_total"])
                    items.append({
                        "customer": item["customer"],
                        "booking_total": float(item["booking_total"]),
                        "extra_income_total": float(item["extra_income_total"]),
                        "total_fee": total_fee,
                    })
                items.sort(key=lambda row: (-row["total_fee"], row["customer"]))

                booking_grand_total = sum(float(item["total_fee"]) for item in booking_items)
                extra_income_grand_total = sum(float(row["amount"]) for row in extra_records)
                grand_total = booking_grand_total + extra_income_grand_total

                booking_total_records = len(booking_records)
                extra_income_total_records = len(extra_records)
                booking_total_pages = max(1, (booking_total_records + page_size - 1) // page_size)
                extra_income_total_pages = max(1, (extra_income_total_records + page_size - 1) // page_size)
                booking_page = min(booking_page, booking_total_pages)
                extra_income_page = min(extra_income_page, extra_income_total_pages)

                booking_start_idx = (booking_page - 1) * page_size
                booking_end_idx = booking_start_idx + page_size
                extra_start_idx = (extra_income_page - 1) * page_size
                extra_end_idx = extra_start_idx + page_size

                self._send_json({
                    "items": items,
                    "booking_items": booking_items,
                    "booking_records": booking_records[booking_start_idx:booking_end_idx],
                    "extra_income_records": extra_records[extra_start_idx:extra_end_idx],
                    "booking_total_records": booking_total_records,
                    "extra_income_total_records": extra_income_total_records,
                    "booking_page": booking_page,
                    "extra_income_page": extra_income_page,
                    "booking_total_pages": booking_total_pages,
                    "extra_income_total_pages": extra_income_total_pages,
                    "booking_grand_total": booking_grand_total,
                    "extra_income_grand_total": extra_income_grand_total,
                    "grand_total": grand_total,
                })
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        if parsed.path != "/api/bookings":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            for field in ["customer", "start", "end"]:
                if not str(payload.get(field, "")).strip():
                    raise ValueError(f"缺少必要欄位：{field}")

            raw_venue_ids = payload.get("venue_ids")
            if isinstance(raw_venue_ids, list) and raw_venue_ids:
                venue_ids = [int(v) for v in raw_venue_ids]
            else:
                if not str(payload.get("venue_id", "")).strip():
                    raise ValueError("缺少必要欄位：venue_id")
                venue_ids = [int(payload["venue_id"])]

            created = []
            with manager_lock:
                for venue_id in venue_ids:
                    created.extend(
                        manager.add_bookings_for_purpose(
                            venue_id=venue_id,
                            customer=payload["customer"],
                            purpose=payload.get("purpose", ""),
                            price=payload.get("price", 0),
                            start=payload["start"],
                            end=payload["end"],
                            note=str(payload.get("note", "")),
                        )
                    )
            first = created[0]
            response = booking_to_dict(first)
            response["created_count"] = len(created)
            self._send_json(response, status=HTTPStatus.CREATED)
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
                    self._send_json(item.__dict__)
                    return
                if parsed.path == "/api/purposes":
                    item = manager.update_purpose(int(payload.get("purpose_id", 0)), str(payload.get("name", "")), payload.get("price", 0))
                    self._send_json(item.__dict__)
                    return
                if parsed.path == "/api/bookings":
                    item = manager.update_booking(
                        booking_id=int(payload.get("booking_id", 0)),
                        venue_id=int(payload.get("venue_id", 0)),
                        customer=str(payload.get("customer", "")),
                        purpose=str(payload.get("purpose", "")),
                        price=payload.get("price", 0),
                        start=str(payload.get("start", "")),
                        end=str(payload.get("end", "")),
                        note=str(payload.get("note", "")),
                    )
                    self._send_json(booking_to_dict(item))
                    return
                if parsed.path == "/api/string-items":
                    item = manager.update_string_item(
                        string_item_id=int(payload.get("string_item_id", 0)),
                        name=str(payload.get("name", "")),
                        amount=payload.get("amount", 0),
                    )
                    self._send_json(string_item_to_dict(item))
                    return
                if parsed.path == "/api/extra-incomes":
                    item = manager.update_extra_income(
                        income_id=int(payload.get("income_id", 0)),
                        customer=str(payload.get("customer", "")),
                        item=str(payload.get("item", "")),
                        amount=payload.get("amount", 0),
                        income_time=str(payload.get("income_time", "")),
                        note=str(payload.get("note", "")),
                        contact_phone=str(payload.get("contact_phone", "")),
                        racket_model=str(payload.get("racket_model", "")),
                        string_tension=payload.get("string_tension", None),
                        payment_status=str(payload.get("payment_status", "")),
                        racket_status=str(payload.get("racket_status", "")),
                        pickup_date=str(payload.get("pickup_date", "")),
                    )
                    self._send_json(extra_income_to_dict(item))
                    return
                self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
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
                elif parsed.path == "/api/bookings":
                    ok = manager.cancel_booking(int(payload.get("booking_id", 0)))
                elif parsed.path == "/api/string-items":
                    ok = manager.delete_string_item(int(payload.get("string_item_id", 0)))
                elif parsed.path == "/api/extra-incomes":
                    ok = manager.delete_extra_income(int(payload.get("income_id", 0)))
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
        if not secrets.compare_digest(password, get_admin_password()):
            raise ValueError("管理員密碼錯誤")


def run_web_app(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), BookingWebHandler)
    print(f"伺服器已啟動：http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_web_app()
