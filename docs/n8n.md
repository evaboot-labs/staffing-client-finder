# Run it in n8n

[`n8n/staffing-client-finder.json`](../n8n/staffing-client-finder.json) is the same client finder for n8n. Every Monday at 8 it saves the companies of your account search into a new account list, exports the hiring managers and talent leaders inside it, sorts them like `finder.py sort`, and adds the new people, with their first message, to a Google Sheet. No AI model and no extra key: the sorting is a Code node. `n8n/build_workflow.py` regenerates the JSON from `CLIENTS.md`.

## What runs

1. **Every Monday at 8** (or **Run now**) and **Your settings**: the account search, how many companies and people per run, the tab URL, and the profile (titles, checks, messages from `CLIENTS.md`).
2. **People already in your sheet** (Google Sheets): the people of earlier runs, so each run only adds new ones.
3. **Save the accounts** and **Check the account list** (Evaboot MCP): the companies of the account search, saved as an account list on your Sales Navigator seat, waited for every 30 seconds.
4. **People search** (Code): the lead search inside that list, with your titles, like `finder.py people-url`.
5. **Export the people** and **Check the people export** (Evaboot MCP): those people with verified emails.
6. **Sort the leads** (Code): persona, company checks, who to contact first, first message. **Add to Leads** writes one row per person, kept or not, with the reason.

## Set it up

1. **Make the sheet:** one Google Sheet with a `Leads` tab, header row:
   `Date, Keep, First, Persona, Name, Title, Company, Growth 1y %, Eng + IT, People team, Email, Email status, LinkedIn, Why, Message`
2. **Import** the JSON in n8n: *Workflows > Import from file*.
3. **Add two credentials:**
   - **Bearer Auth** named `Evaboot MCP (Bearer)`: your key from [dash.evaboot.com/dash/api/](https://dash.evaboot.com/dash/api/). Select it on the four Evaboot MCP nodes.
   - **Google Sheets** on the two sheet nodes.
4. **Fill in Your settings:** `account_search_url` (your Sales Navigator account search; the example is UK software companies of 51 to 500 people, hiring on LinkedIn, growing 10% or more), `accounts_per_run`, `people_per_run`, and `leads_tab_url` (with its `gid`). `profile` holds the titles, checks and messages: edit `CLIENTS.md` and run `python3 n8n/build_workflow.py`, or edit the JSON in the field. Replace the `proof` placeholder before the first real run.
5. **Test:** set `accounts_per_run` to 10 and `people_per_run` to 5, click **Execute workflow** on **Run now**, and read the tab.
6. **Publish** the workflow to run it every Monday.

## Good to know

- Each run spends 1 Evaboot credit per exported person. Saving the account list costs no credit, but each run writes a new list on your Sales Navigator seat: delete old ones under *Accounts > Lists* from time to time.
- LinkedIn serves a search in a changing order, so a weekly run can return people you already have: they cost a credit but are not added twice.
- A run stops with an error when Sales Navigator saves no company or no new person is found: widen the account search or raise `accounts_per_run`.

Back to the [README](../README.md).
