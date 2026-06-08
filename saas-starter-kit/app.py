"""
SaaS Starter Kit — control plane for the AI Agent Lab SaaS.

Auth + Stripe-subscription scaffolding for the hosted SaaS, with a SQLite
user store. It pairs with your existing landing page.

WHAT'S WIRED (ready to use):
  - Auth:    Auth0 / Authlib   ->  /login  /callback  /logout
  - Billing: Stripe            ->  /config  /checkout  /billing (Customer Portal)
  - Store:   SQLite users table (user_id, email, subscription, timestamp)
  - Email:   send_mail() helper (SMTP)

WHAT YOU BUILD (stubs with TODOs below — the lab-specific 40%):
  - /webhooks/stripe  ->  provision a lab instance on subscribe, tear it down on cancel
  - admin role / dashboard (optional)

Run locally:  python app.py     (fill .env first — see .env.sample)
Deploy:       gunicorn app:app
"""

import sqlite3
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from os import environ as env
from urllib.parse import quote_plus, urlencode

import stripe
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import (
    Flask, redirect, render_template, session, url_for, request, jsonify,
)

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

STRIPE_PRICE_ID = env.get("STRIPE_PRICE_ID", "")   # your Stripe subscription Price ID
DB_PATH = env.get("DB_PATH", "saas.db")

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY", "dev-only-change-me")

# Auth0 (Authlib) — managed auth; do NOT hand-roll passwords
oauth = OAuth(app)
oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{env.get('AUTH0_DOMAIN')}/.well-known/openid-configuration",
)

# Stripe
stripe.api_key = env.get("STRIPE_SECRET_KEY")

# ---------------------------------------------------------------------------
# user store (SQLite — swap for Postgres if you outgrow it)
# ---------------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   user_id      TEXT PRIMARY KEY,
                   email        TEXT,
                   subscription TEXT,
                   timestamp    TEXT
               )"""
        )

def upsert_user(user_id, email=None, subscription=None):
    if not user_id:
        return
    with db() as conn:
        conn.execute(
            "INSERT INTO users (user_id, email, subscription, timestamp) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  email=COALESCE(excluded.email, users.email), "
            "  subscription=COALESCE(excluded.subscription, users.subscription), "
            "  timestamp=excluded.timestamp",
            (user_id, email, subscription, datetime.utcnow().isoformat()),
        )

init_db()

# ---------------------------------------------------------------------------
# email (SMTP — minimal; swap for Postmark/MailerSend/SES if you prefer)
# ---------------------------------------------------------------------------
def send_mail(to_email, subject, html):
    host = env.get("MAIL_SERVER")
    if not host:
        print(f"[mail disabled] would send to {to_email}: {subject}")
        return False
    msg = MIMEText(html, "html")
    msg["Subject"] = subject
    msg["From"] = env.get("MAIL_FROM", env.get("MAIL_USERNAME", ""))
    msg["To"] = to_email
    try:
        with smtplib.SMTP_SSL(host, int(env.get("MAIL_PORT", "465"))) as s:
            s.login(env.get("MAIL_USERNAME"), env.get("MAIL_PASSWORD"))
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"[mail error] {e}")
        return False

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def current_user():
    return (session.get("user") or {}).get("userinfo")

def active_subscription(user_id):
    """Return the active Stripe subscription for this user, or None."""
    try:
        subs = stripe.Subscription.search(
            query=f"status:'active' AND metadata['user_id']:'{user_id}'"
        )
        return subs["data"][0] if subs["data"] else None
    except Exception as e:
        print(f"[stripe] {e}")
        return None

# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    user = current_user()
    subscription = active_subscription(user["sub"]) if user else None
    if user:
        upsert_user(user["sub"], user.get("email"),
                    subscription["status"] if subscription else "none")
    return render_template("index.html", user=user, subscription=subscription)

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=user,
                           subscription=active_subscription(user["sub"]))

# ---------------------------------------------------------------------------
# auth (Auth0 / Authlib)
# ---------------------------------------------------------------------------
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(redirect_uri=url_for("callback", _external=True))

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    info = token["userinfo"]
    upsert_user(info["sub"], info.get("email"))
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN", "") + "/v2/logout?"
        + urlencode(
            {"returnTo": url_for("index", _external=True),
             "client_id": env.get("AUTH0_CLIENT_ID")},
            quote_via=quote_plus,
        )
    )

# ---------------------------------------------------------------------------
# billing (Stripe)
# ---------------------------------------------------------------------------
@app.route("/config", methods=["POST"])
def config():
    return jsonify(env.get("STRIPE_PUBLISHABLE_KEY"))

@app.route("/checkout", methods=["POST"])
def checkout():
    user = current_user()
    if not user:
        return jsonify({"error": "not authenticated"}), 401
    try:
        cs = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=user.get("email"),
            success_url=url_for("dashboard", _external=True),
            cancel_url=url_for("index", _external=True),
            # The link between the auth user and the Stripe subscription:
            subscription_data={"metadata": {"user_id": user["sub"]}},
        )
        return jsonify({"sessionId": cs["id"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/billing", methods=["POST"])
def billing():
    """Stripe Customer Portal — self-service billing, no UI to build."""
    user = current_user()
    if not user:
        return jsonify({"error": "not authenticated"}), 401
    sub = active_subscription(user["sub"])
    if not sub:
        return jsonify({"error": "no active subscription"}), 400
    portal = stripe.billing_portal.Session.create(
        customer=sub["customer"],
        return_url=url_for("dashboard", _external=True),
    )
    return jsonify({"url": portal["url"]})

# ---------------------------------------------------------------------------
# Stripe webhook  ──  ⚠️  THE PART YOU BUILD (lab-specific provisioning)
# ---------------------------------------------------------------------------
@app.route("/webhooks/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, env.get("STRIPE_WEBHOOK_SECRET")
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    etype = event["type"]
    obj = event["data"]["object"]
    meta = obj.get("metadata") or {}
    user_id = meta.get("user_id")

    if etype in ("checkout.session.completed", "customer.subscription.created"):
        print(f"[provision] TODO: spin up a lab for user_id={user_id}")
        upsert_user(user_id, subscription="active")

    elif etype == "customer.subscription.deleted":
        # TODO: DEPROVISION — tear down the tenant's instance (stop billing AWS),
        # optionally keep a final backup for a grace period.
        print(f"[deprovision] TODO: tear down lab for user_id={user_id}")
        upsert_user(user_id, subscription="cancelled")

    return jsonify({"received": True})

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=env.get("IS_PRODUCTION") != "True", port=int(env.get("PORT", "5000")))
