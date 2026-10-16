# Monthly QR Coupon System / ወርሃዊ የQR ኩፖን ስርዓት

## Start on Windows
1. Install Python 3.11+ and select "Add Python to PATH".
2. Extract this ZIP.
3. Double-click `run_windows.bat`.
4. On the host computer, open http://127.0.0.1:5000

## Demo logins (for testing only)
- Super Admin: `admin` / `ChangeMeAdmin123!`
- Merchant: `merchant` / `ChangeMeMerchant123!`
- Demo employee: `emp004` / `ChangeMeEmployee123!`

Change/remove these demo credentials before using real information. This prototype does not yet provide a password-change screen.

## Local network
To access from other devices on the same LAN, use the host computer's IPv4 address from `ipconfig`, e.g. `http://192.168.x.x:5000`. Allow the port only on Windows Firewall's Private network profile. Do not expose it to the public internet.

## Implemented
- Three roles: administrator, one merchant, employees.
- English/Amharic language toggle.
- Admin creates accounts, prepares monthly allocation as working days × rate, and releases allocations.
- Permanent employee QR image containing an opaque token.
- Merchant charges quantity; employee balance decreases and merchant monthly balance increases in one database transaction.
- Employee dashboard shows allocation, spending, remaining balance and history.
- Admin monthly close stores total and transaction count; history is preserved.
- Merchant balance is monthly; the next month's record starts at zero.

## Prototype limitations — do not use for live official data yet
This is a workflow prototype using SQLite. It does not yet include in-browser camera scanning, password-change/reset, CSRF protection, HTTPS, full admin correction/reversal workflow, or production-grade deployment hardening. For 500+ employees and concurrent use, migrate to PostgreSQL and deploy behind a production WSGI server. Add backups, HTTPS, security review, and formal approval rules before real deployment. Employee allocations only become spendable after the administrator releases them.
