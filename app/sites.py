"""Content and identity for the demo businesses.

Each entry below is a whole website: its palette, its typeface pairing, its
layout variant and its copy. One template renders all of them, which is the
point - a client is buying the ability to stand this up for *their* business,
and the honest way to show that is to stand up six and let them look.

They must not read as one template with the colours swapped, so the differences
are structural as well as chromatic: three hero layouts, three section shapes,
six typeface pairings, light and dark. Anything that only varies the accent
would be a worse demonstration than saying nothing.
"""
from typing import Any

# Google Fonts families used below. Kept in one place so the template can build
# a single stylesheet request instead of one per business.
FONTS = [
    "Anton",
    "Inter+Tight:wght@400;500;600",
    "Plus+Jakarta+Sans:wght@400;500;600;800",
    "Fraunces:opsz,wght@9..144,400..700",
    "Inter:wght@400;500;600",
    "Instrument+Serif:ital@0;1",
    "Karla:wght@400;500;700",
    "Manrope:wght@400;500;700;800",
    "JetBrains+Mono:wght@400;500",
]

PAGES: dict[str, dict[str, Any]] = {

    # ---------------------------------------------------------------- agency
    "agency": {
        "brand": "Halyard Digital",
        "mark": "HALYARD",
        "url_label": "halyarddigital.example",
        "theme": {
            "mode": "dark",
            "bg": "#0B0E12",
            "surface": "#141920",
            "ink": "#F2F5F7",
            "muted": "#8B98A5",
            "line": "#222A34",
            "accent": "#C8F53C",
            "accent_ink": "#0B0E12",
            "radius": "2px",
            "display": "Anton",
            "display_weight": "400",
            "display_tracking": "-.01em",
            "display_transform": "uppercase",
            "body": "Inter Tight",
        },
        "layout": "stacked",
        "nav": ["Services", "Pricing", "Results", "Contact"],
        "hero": {
            "eyebrow": "Performance marketing · Manchester",
            "title": "Spend less.\nSell more.\nKnow why.",
            "lead": "Paid media, SEO and lifecycle email for brands doing £1m to "
                    "£30m. Eleven people, eighteen clients, no white-label.",
            "cta": "Get a free audit call",
            "cta2": "See pricing",
        },
        "stats": [
            ("12%", "of ad spend, no media markup"),
            ("18", "clients, and that is the cap"),
            ("15", "working days to first changes live"),
            ("£4.5k", "fixed-fee audit, yours to keep"),
        ],
        "sections": [
            {
                "kicker": "What we run",
                "title": "Four channels, done properly",
                "intro": "We would rather run four channels well than eight badly. "
                         "Everything runs inside your own ad accounts.",
                "items": [
                    ("Paid search", "Google Ads",
                     "Structure, bidding, feed hygiene and the negative-keyword work "
                     "nobody enjoys and everybody skips."),
                    ("Paid social", "Meta · TikTok · LinkedIn",
                     "Creative testing against a real hypothesis, not twelve variants "
                     "of the same image."),
                    ("Organic", "Technical and content SEO",
                     "Six to nine months before it is worth judging. Anyone promising "
                     "faster is selling you something."),
                    ("Lifecycle", "Klaviyo · HubSpot",
                     "The flows that make paid traffic worth buying twice."),
                ],
            },
            {
                "kicker": "How we bill",
                "title": "Priced so you can predict it",
                "intro": "Management fee only. Media goes on your card, billed to you "
                         "by the platforms.",
                "items": [
                    ("Paid media", "12% of spend, £2,400 minimum",
                     "Below about £20k a month the percentage stops making sense and "
                     "we quote a flat fee."),
                    ("SEO retainer", "from £3,200 a month",
                     "Technical, content and digital PR, reported against revenue "
                     "rather than rankings."),
                    ("Standalone audit", "£4,500 fixed",
                     "Three weeks, you keep the document, no obligation to retain us. "
                     "About half of audit clients do."),
                ],
            },
        ],
        "band": {
            "title": "We will tell you if we cannot help",
            "body": "Under £8,000 a month in media, you are better off in-house for "
                    "now, and we will say so on the first call rather than after the "
                    "third invoice.",
            "cta": "Book the 30 minutes",
        },
        "footer": "Halyard Digital · 22 Tib Street, Manchester M4 · hello@halyarddigital.example",
    },

    # ------------------------------------------------------------------ saas
    "saas": {
        "brand": "Latchkey",
        "mark": "Latchkey",
        "url_label": "latchkey.example",
        "theme": {
            "mode": "light",
            "bg": "#F6F8FB",
            "surface": "#FFFFFF",
            "ink": "#111827",
            "muted": "#64748B",
            "line": "#E2E8F0",
            "accent": "#4338CA",
            "accent_ink": "#FFFFFF",
            "radius": "12px",
            "display": "Plus Jakarta Sans",
            "display_weight": "800",
            "display_tracking": "-.03em",
            "display_transform": "none",
            "body": "Plus Jakarta Sans",
        },
        "layout": "split",
        "nav": ["Product", "Pricing", "Security", "Docs"],
        "hero": {
            "eyebrow": "Scheduling and dispatch for field service",
            "title": "Every van, every job, one screen.",
            "lead": "Latchkey schedules the work, tracks the parts, invoices the "
                    "customer and tells you which engineer is running late. Used by "
                    "1,400 companies with five to eighty engineers.",
            "cta": "Start the 14-day trial",
            "cta2": "Talk to sales",
        },
        "stats": [
            ("1,400", "companies dispatching daily"),
            ("$29", "per user, per month, to start"),
            ("14 days", "trial, no card required"),
            ("eu-west-1", "where your data stays"),
        ],
        "sections": [
            {
                "kicker": "Plans",
                "title": "Per active user. Deactivate a seat, stop paying for it.",
                "intro": "Annual billing is two months free. No setup fee, no minimum "
                         "contract on monthly plans.",
                "items": [
                    ("Starter", "$29 / user / month",
                     "Scheduling, job cards, customer records and the mobile app. "
                     "Minimum three users."),
                    ("Growth", "$49 / user / month",
                     "Adds invoicing, parts and stock, recurring jobs, custom job "
                     "forms and the customer portal."),
                    ("Scale", "$79 / user / month",
                     "Adds the REST API, SSO, custom roles, audit logs and a named "
                     "account manager."),
                ],
            },
            {
                "kicker": "The questions procurement asks",
                "title": "Answered before you have to ask them",
                "intro": "",
                "items": [
                    ("Hosting", "AWS eu-west-1",
                     "Daily encrypted backups kept 35 days. Encrypted in transit and "
                     "at rest."),
                    ("Compliance", "ISO 27001 · SOC 2 Type II",
                     "Report under NDA. Security questionnaires answered in three "
                     "working days."),
                    ("Exit", "Export everything, any time",
                     "CSV or API, no export fee. Your data is yours and leaving is "
                     "not a negotiation."),
                ],
            },
        ],
        "band": {
            "title": "Migrating from spreadsheets or something worse",
            "body": "Growth and Scale include guided migration: customers, sites, job "
                    "history and recurring schedules. Five to ten working days, and "
                    "cleaning the data is the slow part, not loading it.",
            "cta": "See how migration works",
        },
        "footer": "Latchkey · Bristol and remote across Europe · hello@latchkey.example",
    },

    # ---------------------------------------------------------------- realty
    "realty": {
        "brand": "Kestrel Property",
        "mark": "Kestrel",
        "url_label": "kestrelproperty.example",
        "theme": {
            "mode": "light",
            "bg": "#F4F1EC",
            "surface": "#FBFAF7",
            "ink": "#1F2420",
            "muted": "#6E7368",
            "line": "#DFDAD0",
            "accent": "#2F5D3F",
            "accent_ink": "#FBFAF7",
            "radius": "3px",
            "display": "Fraunces",
            "display_weight": "600",
            "display_tracking": "-.02em",
            "display_transform": "none",
            "body": "Inter",
        },
        "layout": "panel",
        "nav": ["Buying", "Selling", "Lettings", "Valuation"],
        "hero": {
            "eyebrow": "Independent estate agency · Bristol",
            "title": "We will tell you what it is worth, and what it will sell for.",
            "lead": "Those are not always the same number, and the agents who only "
                    "quote the first one are the reason your neighbour's house has "
                    "been on the market since March.",
            "cta": "Book a free valuation",
            "cta2": "Register as a buyer",
        },
        "stats": [
            ("1.2%", "sole agency commission plus VAT"),
            ("34 days", "average listing to agreed sale"),
            ("£412k", "average sale price on our books"),
            ("0", "charged if it does not sell"),
        ],
        "sections": [
            {
                "kicker": "Selling",
                "title": "What the commission actually covers",
                "intro": "Nothing up front, nothing if the property does not sell.",
                "items": [
                    ("Marketing", "Included",
                     "Professional photography, floor plan, EPC if you need one, and "
                     "listings on Rightmove and Zoopla."),
                    ("Viewings", "Accompanied",
                     "A negotiator attends. Evenings until 19:30 and Saturdays, "
                     "because most buyers work."),
                    ("The sale", "Through to completion",
                     "Negotiation, chain management and chasing solicitors, which is "
                     "most of the job after the offer."),
                ],
            },
            {
                "kicker": "Lettings",
                "title": "Managed, or find-only",
                "intro": "Tenants pay no agency fees beyond deposit and first month, "
                         "as the Tenant Fees Act requires.",
                "items": [
                    ("Full management", "10% of rent plus VAT",
                     "Marketing, referencing, deposit protection, rent collection, "
                     "arrears chasing, inspections and repairs."),
                    ("Tenant find", "60% of first month's rent",
                     "We market, reference and paper the tenancy, then hand it over "
                     "to you."),
                    ("Deposits", "Five weeks, DPS protected",
                     "Held in the Deposit Protection Service, never in our account."),
                ],
            },
        ],
        "band": {
            "title": "Thinking about it rather than doing it",
            "body": "A valuation takes 45 minutes and commits you to nothing. Most "
                    "people who book one are eight months away from moving, and that "
                    "is a perfectly good time to have the conversation.",
            "cta": "Book the valuation",
        },
        "footer": "Kestrel Property · 88 Whiteladies Road, Bristol BS8 · 0117 496 0188",
    },

    # -------------------------------------------------------------- coaching
    "coaching": {
        "brand": "Northlight Coaching",
        "mark": "Northlight",
        "url_label": "northlightcoaching.example",
        "theme": {
            "mode": "light",
            "bg": "#FBF7F4",
            "surface": "#FFFFFF",
            "ink": "#241E27",
            "muted": "#6F6572",
            "line": "#E8DFE2",
            "accent": "#7A4A6B",
            "accent_ink": "#FFFFFF",
            "radius": "999px",
            "display": "Instrument Serif",
            "display_weight": "400",
            "display_tracking": "-.01em",
            "display_transform": "none",
            "body": "Karla",
        },
        "layout": "centred",
        "nav": ["Programmes", "Approach", "Pricing", "Book a call"],
        "hero": {
            "eyebrow": "Coaching for first-time leaders",
            "title": "You were promoted for the work. Now the work is other people.",
            "lead": "Northlight helps senior individual contributors make the shift "
                    "into leadership without pretending it is easy. Two coaches, both "
                    "former engineering and operations managers.",
            "cta": "Book a free 30 minutes",
            "cta2": "See the programmes",
        },
        "stats": [
            ("40", "clients a year, deliberately"),
            ("8 weeks", "the Foundations programme"),
            ("1 in 4", "first calls end with 'not yet'"),
            ("£0", "for that call, always"),
        ],
        "sections": [
            {
                "kicker": "Programmes",
                "title": "Three ways in",
                "intro": "Payment plans on anything over £1,000: three instalments at "
                         "no extra cost.",
                "items": [
                    ("Foundations", "£1,450 · group of eight",
                     "Eight weeks, 90 minutes a week, a workbook and a private channel "
                     "between sessions."),
                    ("One-to-one", "£220 a session · £1,900 for ten",
                     "Fortnightly, 50 minutes, for a specific situation rather than a "
                     "general improvement."),
                    ("The Intensive", "£3,800 · six months",
                     "Twelve sessions, a 360 exercise with your colleagues, and email "
                     "access between them."),
                ],
            },
            {
                "kicker": "Honesty",
                "title": "What this is not",
                "intro": "",
                "items": [
                    ("Not interview prep", "We will refer you",
                     "CV rewrites and interview coaching are a different craft and "
                     "other people do them better."),
                    ("Not therapy", "Different discipline",
                     "If what is in the way is not work, coaching is the wrong tool "
                     "and we will say so."),
                    ("Not passive", "You do the work",
                     "People who do nothing between sessions get very little, and we "
                     "tell them that before they pay."),
                ],
            },
        ],
        "band": {
            "title": "The first call is a conversation, not a pitch",
            "body": "Thirty minutes, free, and about one in four ends with us saying "
                    "coaching is not what you need right now. That is a good outcome.",
            "cta": "Find a time",
        },
        "footer": "Northlight Coaching · Remote, UK and Europe · hello@northlightcoaching.example",
    },

    # ------------------------------------------------------------ recruiting
    "recruiting": {
        "brand": "Havenridge Talent",
        "mark": "HAVENRIDGE",
        "url_label": "havenridge.example",
        "theme": {
            "mode": "dark",
            "bg": "#101418",
            "surface": "#181E24",
            "ink": "#EDF1F4",
            "muted": "#8D9AA6",
            "line": "#252D35",
            "accent": "#FF6B4A",
            "accent_ink": "#101418",
            "radius": "6px",
            "display": "Manrope",
            "display_weight": "800",
            "display_tracking": "-.035em",
            "display_transform": "none",
            "body": "Manrope",
        },
        "layout": "split",
        "nav": ["For employers", "For candidates", "Sectors", "Contact"],
        "hero": {
            "eyebrow": "Engineering, data and product recruitment",
            "title": "Five CVs, and we have spoken to all five.",
            "lead": "Havenridge places software engineers, data and product people "
                    "across the UK and remote Europe. Seven consultants, 143 "
                    "placements last year, no CV spraying.",
            "cta": "Brief us on a role",
            "cta2": "Send your CV",
        },
        "stats": [
            ("18%", "of first-year salary, permanent"),
            ("31 days", "average brief to signed offer"),
            ("12 weeks", "replacement guarantee"),
            ("£0", "charged to candidates, ever"),
        ],
        "sections": [
            {
                "kicker": "For employers",
                "title": "What the fee buys",
                "intro": "Invoiced on the candidate's first day, payable in 30 days. "
                         "Exclusivity is not required.",
                "items": [
                    ("Contingent", "18% of base salary",
                     "Longlist in five working days, shortlist of three to five in "
                     "ten, each with a written summary."),
                    ("Retained", "22%, in three stages",
                     "On brief, on shortlist, on start. Worth it above about £90k "
                     "where the search is genuinely harder."),
                    ("Contract", "12–18% margin, disclosed",
                     "You always see what the contractor gets and what we take. "
                     "Weekly self-billing, paid the Friday after approval."),
                ],
            },
            {
                "kicker": "For candidates",
                "title": "Rules we actually keep",
                "intro": "",
                "items": [
                    ("Every application gets a reply", "Within three working days",
                     "Including the rejections. Especially the rejections."),
                    ("Your CV moves nowhere without a yes", "Named company, each time",
                     "If an agency has ever done otherwise to you, you will know why "
                     "we say it out loud."),
                    ("Salary stays yours", "Until you share it",
                     "Your expectations are confidential from the employer until you "
                     "decide otherwise."),
                ],
            },
        ],
        "band": {
            "title": "We will tell you why you are losing candidates",
            "body": "Usually it is a band set below market, a four-stage process with "
                    "a week between stages, or feedback that takes longer than 48 "
                    "hours. Saying so beats billing you for a search that cannot close.",
            "cta": "Book a briefing call",
        },
        "footer": "Havenridge Talent · London and remote Europe · hello@havenridge.example",
    },
}


def page(site: str) -> dict[str, Any] | None:
    return PAGES.get(site)


def has_page(site: str) -> bool:
    return site in PAGES
