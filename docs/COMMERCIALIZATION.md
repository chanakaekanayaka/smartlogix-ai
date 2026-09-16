# SmartLogix — Commercialization & Pricing Model

> This document is the commercialization strategy required by the IT3041
> assignment brief (System Requirement 5: pricing model, target users/market,
> deployment ideas). It is written for the project report / viva and is
> grounded in what SmartLogix actually does today, not generic filler.
>
> Figures below are **illustrative estimates for this academic project**,
> reasoned from the system's real cost drivers (LLM calls, hosting). They
> match the pricing model already presented at Mid Evaluation - not sourced
> from live market data. Say so plainly if asked in the viva; a reasoned
> estimate is the expected answer at this stage, not real pricing research.

## 1. What SmartLogix sells

SmartLogix itself is **not** the thing being sold to end customers - it is
the AI system a logistics business runs so *its own* customers get instant,
explained delivery quotes. The product being commercialized is:

> **"SmartLogix for Business"** - a multi-agent AI logistics assistant,
> licensed to courier companies, warehouses and e-commerce sellers, that
> turns a plain-English delivery request into a warehouse decision, a
> vehicle/route/cost plan, and a plain-language, policy-grounded explanation
> - in seconds, with a built-in Responsible AI trail.

This maps directly onto the existing pipeline (`agents/coordinator.py`):
Query -> Inventory -> Warehouse -> Route -> Retrieval, plus the standalone
Retrieval Agent microservice and the security layer (auth, input
sanitisation) already built into the codebase.

## 2. Target market

| Segment | Who | Pain point today | Why SmartLogix |
|---|---|---|---|
| **Primary** - Small/medium couriers & 3PLs (Sri Lanka) | Local delivery/courier firms with 1-15 warehouses, currently dispatching by phone/spreadsheet | No AI-assisted quoting, no consistent pricing, no audit trail for "why this cost/route" | Instant, explainable, fairly-priced quotes without hiring a data team |
| **Secondary** - E-commerce sellers & marketplaces | Online sellers who need a shipping-cost estimate at checkout | Generic couriers give flat/manual rates; no real-time warehouse-aware routing | Embed the `/api/delivery` pipeline behind their checkout via the API tier |
| **Tertiary (enterprise)** - Large logistics/3PL providers | Big dispatch teams wanting an AI copilot, under data-protection / auditability pressure | Off-the-shelf global logistics SaaS is expensive, not localized, and rarely explainable | On-prem/private deployment + built-in fairness/explainability for compliance |

## 3. Competitive landscape (brief)

- **Status quo (most local SMEs today):** manual dispatch - spreadsheets and
  phone calls. Free, but slow, inconsistent, and gives no explanation to the
  customer.
- **Global logistics SaaS platforms:** capable, but priced for large
  markets, not localized to Sri Lankan cities/warehouses/pricing, and rarely
  explain *why* a price or route was chosen.
- **Generic chatbot/FAQ vendors:** answer policy questions but have no
  logistics domain reasoning (no warehouse selection, no route/cost engine).

**SmartLogix's edge:** purpose-built for Sri Lankan logistics data, a real
multi-agent decision pipeline (not just a chatbot), Responsible AI baked in
from day one (see `coordinator.py`'s `fairness_note` / `explanation` /
`estimate_warning`), and a free tier plus SME-friendly pricing that
undercuts enterprise global logistics SaaS.

## 4. Pricing model

The tiered **SaaS subscription** presented at Mid Evaluation, priced by
monthly delivery-plan queries (the unit that actually drives LLM cost - each
query makes at least two Groq calls: entity extraction in `query_agent` and
the grounded explanation in the Retrieval Agent).

| Tier | Price | Included | For |
|---|---|---|---|
| **Free** | $0 | 10 delivery estimates / month, chat widget (`/api/chat`) | Very small businesses |
| **Basic** | $29 / month | Higher monthly query volume, 1 warehouse, email support | Small delivery companies |
| **Pro** | $99 / month | Unlimited delivery-plan queries, multiple warehouses, own knowledge-base content, usage dashboard, priority support | Medium businesses, unlimited use |
| **Enterprise** | Custom | Unlimited everything, private/on-prem deployment, SLA-backed uptime, dedicated account manager, white-label branding | Large logistics companies |
| **API licensing** | $0.10-0.20 / request | Direct, usage-based access to `/api/delivery` - no dashboard/seat | Other apps embedding SmartLogix (e.g. a checkout-time quote widget) |

This mirrors the *shape* of the pricing already built into the product
itself - `route_agent.py`'s per-shipment cost formula (base fee + usage-based
charges + a mode multiplier) - applied one level up, to the SaaS subscription
instead of a single delivery.

## 5. Revenue streams

1. **Recurring subscriptions** (Basic/Pro/Enterprise - the standard SaaS
   MRR/ARR model).
2. **API licensing** - per-request revenue from other applications
   embedding the pipeline directly, independent of the dashboard tiers.
3. **Free-to-paid conversion** - the Free tier's 10-estimate/month cap is
   the funnel: it costs little to serve (a handful of LLM calls) and
   converts naturally to Basic/Pro as a business's delivery volume grows.
4. **Consulting/training** for logistics companies adopting AI dispatch for
   the first time (a natural upsell given the target market's low AI
   maturity today).

## 6. Cost structure (what the pricing has to cover)

| Cost driver | Where it comes from |
|---|---|
| LLM API usage (Groq) | `query_agent.py` (extraction) + Retrieval Agent (explanation, chat) - the two real per-query LLM calls |
| Vector search / embeddings | ChromaDB + sentence-transformers, run inside the Retrieval Agent service |
| Hosting | 3 services in production: backend API, Retrieval Agent microservice, frontend - plus the vector DB |
| Support & maintenance | Tiered by plan (email -> priority -> dedicated account manager) |

Keeping the Retrieval Agent as its own microservice (see
`agents/retrieval_service.py`) also means it can be scaled or billed
independently of the rest of the pipeline as usage grows - useful context
for the "deployment ideas" requirement below.

## 7. Deployment options

- **Cloud SaaS (multi-tenant)** - default for Free/Basic/Pro. Fastest
  onboarding, lowest cost, SmartLogix hosts everything.
- **Private cloud / on-premise (Enterprise)** - for clients needing data
  residency or stricter compliance. The Retrieval Agent's separation into
  its own HTTP service makes a hybrid split practical: e.g. the client hosts
  the Retrieval Agent + their own knowledge base in their own environment
  while SmartLogix manages the rest.
- **Embedded/API** - no dashboard, just the `/api/delivery` and `/api/chat`
  endpoints behind a client's own app (e-commerce checkout use case).

## 8. Go-to-market plan

1. **Free tier as the funnel:** the Free plan's 10 estimates/month is the
   on-ramp - low cost to serve, easy to try, and converts to Basic/Pro as a
   business's delivery volume outgrows the cap.
2. **Pilot programme:** onboard 2-3 local courier SMEs on Basic/Pro for a
   case study and testimonials.
3. **Partnerships:** integrate with e-commerce seller communities and
   delivery-company networks via the API licensing tier.
4. **Direct outreach:** SME logistics/courier associations, local tech and
   logistics expos.

## 9. Responsible AI as a market differentiator

This isn't only an assignment requirement - it's a sales argument. Every
SmartLogix response already carries:

- `fairness_note` - proof of uniform pricing rules across all regions.
- `explanation` (+ `explanation_source`, `grounded_in_policy_count`) -
  an auditable "why" for every decision.
- `is_approximate_estimate` / `estimate_warning` - transparent about what
  is an estimate vs. a firm figure.

For Enterprise buyers facing data-protection and AI-governance pressure,
"explainable by default" is a concrete procurement advantage over opaque
competitors - worth stating explicitly in the report's Responsible AI and
commercialization sections together.

## 10. Future opportunities (optional, for report depth)

- Aggregated, anonymised logistics analytics as a paid insights add-on
  (regional demand trends, common delivery delays).
- Expansion beyond Sri Lanka using the same architecture with a new
  dataset/knowledge base per country.
