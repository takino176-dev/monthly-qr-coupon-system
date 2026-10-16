# Before real deployment
- Replace demo credentials and set a long random COUPON_SECRET_KEY environment variable.
- Use HTTPS even on the internal network and restrict firewall access to trusted devices.
- Add password change/reset, CSRF protection, rate limiting, backups, and audited reversals.
- Use PostgreSQL and a production WSGI server for 500+ users/concurrent transactions.
- Confirm month cutoff, holiday/working-day policy, and treatment of unused employee coupons with the organization.
