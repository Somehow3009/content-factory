"""Xoay ENCRYPTION_KEY: giải mã tokens bằng key cũ -> mã hóa lại bằng key mới.
Usage:
  $env:OLD_ENCRYPTION_KEY="<key-cu-trong-.env>"
  python scripts/rekey.py   # in ra key mới, tự cập nhật DB
Sau đó thay ENCRYPTION_KEY trong .env bằng key mới in ra.
"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet
from sqlalchemy import select

old = os.environ.get("OLD_ENCRYPTION_KEY", "")
if not old:
    raise SystemExit("thiếu OLD_ENCRYPTION_KEY")

from app.database.db import SessionLocal
from app.database.models import OAuthToken

new_key = Fernet.generate_key().decode()
f_old, f_new = Fernet(old.encode()), Fernet(new_key.encode())

db = SessionLocal()
n = 0
for t in db.scalars(select(OAuthToken)).all():
    if t.access_token_encrypted and not t.access_token_encrypted.startswith("mock"):
        t.access_token_encrypted = f_new.encrypt(
            f_old.decrypt(t.access_token_encrypted.encode())).decode()
    if t.refresh_token_encrypted and not t.refresh_token_encrypted.startswith("mock"):
        try:
            t.refresh_token_encrypted = f_new.encrypt(
                f_old.decrypt(t.refresh_token_encrypted.encode())).decode()
        except Exception:
            t.refresh_token_encrypted = ""
    n += 1
db.commit()
db.close()
print("re-encrypted tokens:", n)
print("NEW_ENCRYPTION_KEY=" + new_key)
