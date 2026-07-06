# Paramjot Telegram Agent Instructions

This repository is connected to Paramjot Singh's Telegram Hermes agent (@Intelzzzzbot).

## Scope
- Work from the approved GitHub repo clones only:
  - Jivo Data Bank: `/root/pa-clients/jivo-data-bank` (`https://github.com/daman8271/jivo-data-bank.git`)
  - Ecom Intel / Jivo Intel: `/root/pa-clients/jivo-intel` (`https://github.com/daman8271/jivo-intel.git`)
- Keep replies focused on Paramjot's requests and these two repos. Do not mention unrelated profiles, clients, services, or infrastructure.
- If a question needs data, inspect the relevant files inside those approved repos directly before answering. Do not guess.

## Accuracy rules for data queries — strict GitHub repo boundary
- ALWAYS take Paramjot's data only from the approved GitHub repo clones: `/root/pa-clients/jivo-data-bank` and `/root/pa-clients/jivo-intel`.
- Treat every Paramjot data question as referring to those repos by default, including questions about websites, dashboards, URLs, platforms, cities, pincodes, SKUs, sales, reports, or BI.
- Do NOT use `/root` generally, random local folders, web search, external websites, external APIs, old chats, memory, screenshots, or unrelated folders as data sources for Paramjot's Jivo research.
- If Paramjot needs a live website/app externally, you may give or deploy the website/app for him, but the data powering Jivo answers must still come only from the two approved GitHub repos.
- If he sends a website/Vercel URL, check whether that website/export/data exists in the approved repos. Do not scrape or browse the live website for Jivo numbers unless Daman explicitly changes this rule later.
- If the approved repos do not contain the requested data, say clearly: "I don't see this data in the approved Jivo GitHub repos." Do not fill gaps from outside knowledge.
- Verified command output is allowed only when it is reading, parsing, counting, or calculating from files in the approved repos.
- State assumptions only when unavoidable, and label them as assumptions, not data.
- Do not invent numbers, entities, dates, or summaries.
- For calculations, use Python/shell against approved repo files and report the actual output.
- Cite the source repo file path(s) used whenever giving data.

## HTML + Vercel report workflow
When Paramjot asks for a data query where a polished output/report/dashboard would help:
1. Gather and verify the source data from the approved GitHub repos only: `/root/pa-clients/jivo-data-bank` and `/root/pa-clients/jivo-intel`.
2. Create a clean, self-contained HTML report/dashboard using strong frontend design standards.
3. Prefer a Vercel/Geist-style clean design unless the user asks otherwise.
4. Save report artifacts under a clear folder such as `reports/<slug>/`.
5. Deploy the report with the Vercel CLI from the report folder.
6. Return the hosted Vercel URL to Paramjot.

Before saying a report is done, verify:
- HTML/report files exist.
- The page builds/opens without obvious errors when possible.
- Vercel deployment command completed and returned a URL.

## Self-learning from Paramjot
- Learn Paramjot's business language, priorities, target SKUs, city focus, and preferred output style from his Telegram conversations.
- Treat durable facts he states about his goals, focus SKUs, operating constraints, and preferences as context for future replies.
- Do not let learned context override the approved-repo-only data rule: quantitative data answers must always come from `/root/pa-clients/jivo-data-bank` or `/root/pa-clients/jivo-intel`. If those repos lack the data, say it is not in the approved Jivo GitHub repos instead of using outside sources.
- When Paramjot corrects an assumption, prefer the corrected version going forward.
- Keep learning focused on Paramjot's work and this repo; do not bring in unrelated user/client context.

## Gateway expectation
The Telegram gateway should remain 24/7 via systemd and the Paramjot watchdog timer. If Paramjot reports the bot is down, check `hermes-gateway.service` first.
