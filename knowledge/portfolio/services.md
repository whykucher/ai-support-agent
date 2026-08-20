# Who I am

I am Nikita Denisov, a freelance developer building AI agents and automation
for small businesses. I work solo, directly with the person who owns the
problem, which means no account managers and no telephone game.

My work is mostly Python and n8n. I have built support agents that answer from
company documents, lead qualification pipelines, scrapers, and the plumbing
that moves data between CRMs, spreadsheets, messengers and shops.

# What I build

Four kinds of thing, mostly.

Support agents that answer from your own documents. Your policies, your prices,
your delivery times, not the internet. When the answer is not in your documents
the agent says so and hands the question to a person rather than inventing one.

Lead qualification and routing. Every conversation gets an intent score. The
ones worth money reach Slack, your CRM or an inbox within seconds, with the
full transcript attached, so nobody has to ask the customer the same question
twice.

Workflow automation in n8n. Orders into spreadsheets, invoices into accounting,
form submissions into the CRM, alerts into Slack. Built so you can see the whole
flow on one screen and change it yourself later.

Data collection and clean-up. Scraping, enrichment, deduplication, format
conversion. Getting data out of wherever it is stuck and into the shape your
process actually needs.

# Technology and AI models I use

Python and FastAPI for services. JavaScript for anything that runs in a browser.
n8n for workflow orchestration, because a client can read an n8n canvas and
cannot read my code.

The AI models I work with are Claude, GPT, Gemini, DeepSeek and anything
reachable through OpenRouter. The provider sits behind one interface in my
builds, so switching models is an environment variable rather than a rewrite. Retrieval is hybrid: keyword search
plus embeddings, so exact tokens like order numbers and SKUs still match.

Storage is usually SQLite or Postgres. I do not add a vector database until the
knowledge base is large enough to need one, because it is a service to operate
and a bill to pay for latency nobody notices.

Integrations I have wired: Shopify, HubSpot, Pipedrive, Airtable, Google Sheets,
Gmail, Slack, Telegram, Discord, Notion, Stripe webhooks, and any REST API with
documentation.

# How a project runs

Step one is a call, about twenty minutes, free. I ask what your five most
repeated questions are, where the answers live today, and who handles them now.
If automation is the wrong answer for your situation, this is where I say so.

Step two is a written plan: what gets automated, what deliberately stays manual,
what it costs and how long it takes. In writing, before any code exists.

Step three is the build. Most projects take three to ten working days. You see
it running on your own content, not on a demo, and I send progress as it happens
rather than disappearing for a week.

Step four is handover. You get the code, the credentials and a document
explaining how to change the parts you will want to change. Everything runs on
your accounts. Nothing stops working if you stop paying me.

# Pricing: what I charge and what things cost

I price by outcome, not by hour, because you care about the result and not about
how long I stared at the screen.

A pilot starts around $350. That is your documents indexed, an agent answering
from them, and the widget installed on your site.

A standard build is roughly $900 to $1,400. That adds lead scoring, routing into
your CRM or Slack through n8n, and an operations dashboard.

Ongoing support is $200 to $400 a month: knowledge base updates, monitoring and
a monthly report of what customers actually asked. It is optional and there is
no minimum term.

Larger or unusual work is quoted after the call. If your job is smaller than a
pilot I will tell you and quote it smaller.

If you were expecting an hourly rate: I will quote one if a project genuinely
needs it, but a fixed price for a defined outcome is better for both of us.

# What it costs to run afterwards

The software I write is yours and free to run. The bills come from services you
choose.

Model usage is the main one. A support agent handling a few hundred
conversations a month typically costs a few dollars in API credits. Hosting a
small service is free to about $7 a month depending on where you put it. n8n is
free if you self-host and starts around $20 a month in their cloud.

I can also build in a keyless demo mode that uses keyword retrieval instead of a
language model. It answers well from a tidy knowledge base and costs nothing,
which is useful for a public demo or a pilot.

# When not to hire me

If your process is not written down anywhere and nobody agrees on how it works.
Automation does not fix a broken process, it makes it break faster and more
quietly. Write it down first, then it is a short job.

If you want a bot that improvises and sounds human. Mine are built to say "I do
not know that, let me get someone who does." I think that is the right default
for a business, but if you want the opposite we will both be unhappy.

If you need a mobile app, a brand identity, or someone to run advertising. I do
not do those.

If the whole job is one afternoon of clicking and Zapier's free tier solves it,
use Zapier's free tier. Tell me and I will point you at it.

# Working together and availability

I work in English and Russian. I am comfortable with clients across European and
American time zones and I answer messages within one business day, usually
faster.

I take on two or three projects at a time so that none of them waits. To check
my current availability just ask in this chat or send an email. If I am not
available I will say when I am, rather than starting and stalling.

You keep everything. Code, credentials, workflows, documentation. There is no
platform of mine you have to stay on.

# How to start

Send one paragraph: what the repetitive task is, roughly how often it happens,
and which tools it touches. That is enough for me to say whether it is worth
automating and roughly what it costs.

Email me at hentajp5@gmail.com, or leave your details in this chat and I will
come back to you within a business day.
