# Turning this repo into Upwork work

Everything here is copy you can paste and steps you can follow. Replace the
bracketed placeholders and the demo URL with your own.

---

## 1. Ship the demo somewhere public

A portfolio item that a client can *click* converts far better than screenshots.
The app is one container with no external services, so any of these work:

| Host | Free tier | Setup |
|---|---|---|
| Railway | yes, sleeps | connect repo, add env vars, deploy |
| Render | yes, sleeps | Docker service, add a disk for `/srv/data` |
| Fly.io | small allowance | `fly launch`, add a volume for `/srv/data` |
| A $5 VPS | no | `docker compose up -d` behind Caddy |

Deploy in **demo mode first** (`LLM_PROVIDER=demo`) — no key, no bill, and it
never falls over from a spend limit on the day a client looks at it. Switch to
Claude or GPT only when you want the live version in a call.

Before you publish, change `ADMIN_TOKEN` in `.env`. The dashboard is real, and
the default token is in this repo.

Then run `python -m scripts.seed_demo` once so the dashboard has traffic in it.

---

## 2. The portfolio item

**Title**

> AI Support Agent That Answers From Your Docs and Routes Hot Leads to Your CRM

**Description** (Upwork allows ~600 characters — this fits)

> An e-commerce brand was answering the same 40 questions a day by hand, and
> real buying enquiries were getting lost in the same inbox.
>
> I built a website chat agent that answers from the company's own documents
> (RAG over their FAQ and policies), scores every conversation for buying
> intent, and pushes hot leads straight into Slack and the CRM through n8n —
> with the full transcript attached. Cold leads get logged and a 24-hour
> follow-up email instead.
>
> Stack: Python/FastAPI, hybrid BM25 + embedding retrieval, Claude/GPT, n8n,
> SQLite, vanilla-JS embeddable widget. Live demo and full source below.

**Skills to tag** — pick from what Upwork offers, in this order:

`Chatbot Development` · `AI Agent Development` · `n8n` · `API Integration` ·
`Python` · `FastAPI` · `OpenAI API` · `Automation` · `RAG` · `Ecommerce`

**Cover image** — the storefront with the chat panel open, mid-conversation.

---

## 3. Screenshots to take

Take these at 1440px wide, in this order. The order tells a story: problem →
answer → money → proof.

1. **Storefront, chat open, shipping question answered** with the source chips
   visible underneath. This is the one that shows grounding.
2. **The wholesale question**, with the contact form appearing under the answer.
   This is the one that shows it makes money, not just deflects tickets.
3. **The ops dashboard** — KPI row, the leads table with hot/warm pills, one
   transcript open beside it.
4. **The n8n canvas** with `lead-routing.json` imported. Clients recognise n8n
   even when they cannot read Python.
5. **The smoke test output** — twenty green checks. Almost nobody does this, and
   it reads as "this person tests their work".

A 60–90 second Loom is worth more than all five. Script: ask a support question,
ask a wholesale question, fill the form, cut to the dashboard, cut to n8n
firing. No talking-head intro, start on the product.

---

## 4. Your profile has a gap worth closing

Your title says *WordPress, React & AI Automation* but your overview is entirely
automation and AI — n8n, RAG, chatbots, API integrations. The two do not match,
and Upwork's search ranks on your **skill tags**, which currently list Web
Development, Ecommerce Website, HTML Newsletter and CSS Grid. None of those pull
in the jobs your overview is written for.

Concretely:

- **Title** → `AI Automation Developer | n8n, Chatbots & API Integrations`
- **Add skill tags**: n8n, Chatbot Development, AI Agent Development, Python,
  API Integration, Automation, OpenAI API. Drop CSS Grid and HTML Newsletter.
- **First line of the overview** is what shows in search results. Make it the
  outcome, not the toolset: *"I build AI agents and n8n automations that answer
  customer questions and route real leads to your sales team."*

**On the $9/hr rate.** It filters you into the bracket where clients expect data
entry, and it is below what an n8n + RAG build is worth. Once this demo is live,
stop selling hours and sell the outcome:

| Package | Price | Scope |
|---|---|---|
| Pilot | $350–500 | Their docs indexed, widget installed, demo mode → real LLM |
| Standard | $900–1,400 | Above + n8n routing to their CRM/Slack + dashboard |
| Retainer | $200–400/mo | Knowledge updates, monitoring, monthly report |

If you want to keep an hourly rate visible, $25–35/hr is defensible the moment
you can point at a working system. Raise it after each 5-star review rather than
all at once.

---

## 5. Proposal template

Upwork proposals get skimmed for about eight seconds. Lead with the demo link.

> Hi [name] — I built almost exactly this last month. Working demo:
> [your-demo-url] (open the chat, ask about shipping, then ask about wholesale
> pricing — watch what happens when it detects buying intent).
>
> For [their company] I would:
> 1. Index your [FAQ / policy pages / product docs] so answers come only from
>    your content, never invented.
> 2. Score each conversation for intent and push the commercial ones to
>    [Slack / HubSpot / their tool] through n8n, with the transcript attached.
> 3. Give you a dashboard showing what customers actually ask — usually the most
>    useful part after week one.
>
> One question: [a specific question about their setup that proves you read the
> post — e.g. "is your product data in Shopify metafields or a separate PIM?"].
>
> Source for the demo is public here: [your-repo-url]

Rules that matter more than the wording: send it within the first hour, ask
exactly one question, never paste the same first line as your last proposal, and
do not mention your rate before they mention their budget.

---

## 6. Job searches that fit this build

Save these as Upwork search alerts:

- `n8n` — small, low-competition, the highest-intent feed for you
- `chatbot knowledge base` / `RAG chatbot`
- `AI customer support automation`
- `Shopify AI assistant`
- `lead qualification automation`
- `OpenAI API integration` filtered to Fixed-price $500+

Skip anything that says "must have 100% JSS" while you are building your first
reviews, and skip unpaid trial tasks — you already have a demo that does the
same job.

---

## 7. Discovery questions for the first call

Answer these and the build is ~4 hours of configuration, not a project:

1. Where does your answer content live today, and who keeps it current?
2. What are the five questions you answer most often?
3. What counts as a lead worth waking someone up for?
4. Where should a hot lead land — Slack, email, CRM? Which CRM exactly?
5. What must the bot never do? (quote prices, promise dates, discuss refunds)
6. Who reviews conversations the bot could not answer?

Question 5 is the one that prevents the only kind of failure that loses a
client.
