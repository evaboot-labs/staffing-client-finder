---
name: staffing-client-finder
description: Find clients for a staffing or recruiting agency on LinkedIn - run a Sales Navigator account search for companies that are hiring now (Hiring on LinkedIn, headcount growth) through Evaboot, save them as an account list, export the hiring managers and talent leaders inside it with verified emails, then sort them with finder.py (who to contact first at each company, competitors out) and write a first message grounded in each company's hiring signal. Use when the user asks to find clients for a staffing agency, recruitment agency business development, companies that are hiring, or hiring managers to pitch.
---

# Staffing client finder

This skill runs inside a clone of https://github.com/evaboot-labs/staffing-client-finder: it uses the repo's `finder.py`, `CLIENTS.md` and `docs/`. If `finder.py` is not in the working directory, clone the repo and work from there.

You do the Sales Navigator and Evaboot work through the Evaboot MCP server (`https://mcp.evaboot.com/mcp`). Every tool named below is an Evaboot MCP tool. `finder.py` builds the people search and sorts the leads, the same way every time.

## Rules

- **You never contact anyone.** The list and the messages are drafts; the user reviews and sends them from any outreach tool (lemlist, for example).
- Confirm with the user before each `export_sn_search_or_list` and each `create_account_list_from_search`. Show the search and the cost (1 Evaboot credit per exported person; saving an account list costs no credit but writes a list on their Sales Navigator seat), then wait for a yes.
- Never invent a fact about a company or a person. A message only states what the export holds (headcount growth, department headcounts) and what the search filtered on (Hiring on LinkedIn). Never name a job opening you have not seen.
- Never search with Seniority, Function or lead-search Industry: LinkedIn guesses them. Titles go in the Title filter, built by `finder.py` from `CLIENTS.md`.
- Never ask for or paste an API key. The user writes `EVABOOT_API_KEY` into `.env` and exports it before starting the agent (`docs/connect-your-agent.md`).
- Print every Sales Navigator URL as a Markdown link with the URL in angle brackets: `[Open in Sales Navigator](<url>)`.

## Step 0: check the setup

1. If the Evaboot MCP tools are not in this session, walk the user through `docs/connect-your-agent.md`, then ask them to restart the agent from this folder.
2. Otherwise call `get_daily_export_quota`. If `has_valid_salesnav` is false, ask the user to sign in to Evaboot in Chrome, open any Sales Navigator search with the Evaboot extension, and click Export with Evaboot, then call it again.
3. Run `mkdir -p data lists`.
4. Read `CLIENTS.md`. If it says `Status: EXAMPLE`, ask the user: which roles they place (their desk), in which region, which companies hire those roles (headquarters, industry, size), and one line of proof (roles filled for similar teams). Rewrite the desk, the account search, the hiring manager titles and `hiring_manager_order` for that desk, `team_departments` (the departments that hire those roles) and both messages (they say "engineering and IT"), then set `Status: yours`.

## Step 1: the account search (companies hiring now)

1. Build it with `build_sn_search_from_prompt`: say **account search, companies only, no keywords**, with the headquarters, industry and headcount from `CLIENTS.md`. Ask the user how many companies they want to work this week (25 is a good start) and pass it as `max_results`. When it answers `building`, poll `get_search_build`.
2. Add the hiring filters the builder leaves out. Insert each one right after `filters%3AList(` (or `filters:List(` if the URL is not encoded), followed by `%2C`:
   - Hiring on LinkedIn: `(type%3AJOB_OPPORTUNITIES%2Cvalues%3AList((id%3AJO1%2CselectionType%3AINCLUDED)))`
   - headcount growth, at least 10% in a year: `(type%3ACOMPANY_HEADCOUNT_GROWTH%2CrangeValue%3A(min%3A10))`

   If the builder added a `keywords` part, remove it. Show the URL as a link so the user can open it and see the count.
3. On a yes, save the companies: `create_account_list_from_search` with the URL, `max_results` and a name such as `Staffing client finder <date>`. Poll `get_list_from_search_status` until `complete`, and keep `result.lists[0].list_id`.

## Step 2: the hiring managers and talent leaders

1. `python3 finder.py people-url <list_id>` prints the lead search inside that list, with the titles from `CLIENTS.md`. Show it as a link.
2. On a yes, export it with `export_sn_search_or_list` and `max_results` (10 to start), and poll `get_export` with `limit: 0` until the status is `EXECUTED`.
3. Save it:

```bash
set -a; [ -n "$EVABOOT_API_KEY" ] || . ./.env; set +a
curl -s -H "Authorization: Bearer $EVABOOT_API_KEY" \
  https://api.evaboot.com/v1/extractions/<extraction_id>/ > data/leads-$(date +%F).json
```

## Step 3: sort and draft

1. `python3 finder.py sort data/leads-$(date +%F).json --csv lists/leads-$(date +%F).csv --md lists/leads-$(date +%F).md`
2. Show the table: kept people first (fastest-growing companies first), `first` marks the hiring manager and the talent leader to contact first at each company, then the dropped people with the reason (title, company size, growth, or a recruiting business that is a competitor).
3. Read each kept company's description. If one is a recruiting business `finder.py` missed, say so.
4. Show the first messages from the `.md` file. If `proof` in `CLIENTS.md` still holds the placeholder, ask the user for their line of proof and run `sort` again.

## Every week

Offer the n8n version (`docs/n8n.md`): every Monday it saves the companies of the account search, exports the hiring managers and talent leaders, sorts them and adds the new ones, with their first message, to a Google Sheet.
