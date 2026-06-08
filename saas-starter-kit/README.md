# AI Agent Lab — SaaS Starter Kit

Control plane for the hosted AI Agent Lab SaaS: sign-in, subscription billing, and a
per-tenant provisioning hook. Single-file Flask; pairs with your landing page.

## Functionalities

| Area | Routes | Notes |
|------|--------|-------|
| Auth | `/login` · `/callback` · `/logout` | Auth0 via Authlib |
| Billing | `/config` · `/checkout` · `/billing` | Stripe subscription Checkout + Customer Portal |
| Store | — | SQLite `users` (`user_id, email, subscription, timestamp`) |
| Email | `send_mail()` | SMTP helper |
| Pages | `/` · `/dashboard` | placeholder templates — swap in your landing |
| Webhook | `/webhooks/stripe` | stub — provision / deprovision the tenant's lab here (your `TODO`) |

`/checkout` tags the Stripe subscription with `metadata.user_id`; `active_subscription()`
looks it up by that, so auth and billing stay joined.

## Run it

On a normal host, in a virtualenv:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .sample.env .env            # fill in Auth0 + Stripe keys
.venv/bin/python app.py        # http://localhost:5000
```

`.env` keys:
- **Auth0** — domain, client id/secret. Add your callback to **Allowed Callback URLs**,
  matching the URL you browse to exactly (e.g. `http://localhost:5000/callback`).
- **Stripe** — secret + publishable keys, a subscription **Price ID**, and a webhook
  secret (`stripe listen --forward-to localhost:5000/webhooks/stripe`).
- **SMTP** (optional).

Deploy: `gunicorn app:app` with `IS_PRODUCTION=True`.

## Files

```
app.py            auth + Stripe + webhook stub
requirements.txt  flask, authlib, stripe, dotenv, gunicorn
.sample.env       keys to set
templates/        index.html · dashboard.html
```
