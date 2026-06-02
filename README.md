# AI Agent Lab — SaaS

> Run the AI Agent Lab as a hosted service for your customers.

The **AI Agent Lab** is a complete environment where an AI agent (Claude Code) works alongside a time-series database (QuestDB) and live dashboards (Grafana).

This repo is for the **SaaS entrepreneur**: instead of asking customers to install and operate anything, **you host the AI Agent Lab** and deliver it as an online service. Your customers simply sign up and use it in the browser — no servers, no setup, no operations on their side. You handle the hosting, scaling, updates, and customer support; they get the product.

## Where to start

Full setup and docs live in each repo:

- **[AI Agent Lab](https://github.com/quantiota/AI-Agent-Lab)** — the core lab. Start here.
- **[AI Agent Host](https://github.com/quantiota/AI-Agent-Host)** — the production-ready, Claude Code-powered edition.

## Why offer it as a SaaS

- **Zero friction for customers** — they access it over the web; nothing to install or maintain.
- **You own the service** — host it, brand it, run it as your own product.
- **Open source (MIT)** — free to build your SaaS on top of.

## What I provide

A **SaaS template** built on the AI Agent Lab — the starting base for your service.

The template does **not** include billing or cloud infrastructure. You add those for your business:

- **Payment gateway** — your subscription/billing integration.
- **AWS backend** — provisioning of customer instances and backups.