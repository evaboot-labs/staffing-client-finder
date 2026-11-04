# Agent instructions

This repo finds clients for a staffing or recruiting agency on LinkedIn. It runs a Sales Navigator account search for companies that are hiring now (Hiring on LinkedIn, headcount growth), saves them as an account list with Evaboot, exports the hiring managers and talent leaders inside it with verified emails, then sorts them: who to contact first at each company, recruiting businesses out, and a first message grounded in each company's hiring signal. The user does the outreach. When the user asks to find clients for their agency, companies that are hiring, or hiring managers to pitch:

1. Follow the skill in `skills/staffing-client-finder/SKILL.md` step by step.
2. Read `CLIENTS.md` for the desk, the account search, the titles, the checks and the messages. If it says `Status: EXAMPLE`, ask the user and update it.
3. Use `finder.py` to build the people search and sort the leads. The Evaboot MCP server does the Sales Navigator work (`.mcp.json`).
4. If the user is not connected yet, follow `docs/connect-your-agent.md` with them.
5. If the user wants n8n instead, follow `docs/n8n.md` with them one step at a time: you cannot click inside n8n, so say exactly what to do and wait for their confirmation.

Exports cost 1 Evaboot credit per lead. Confirm with the user before every export and before saving an account list. Never contact anyone yourself. Never ask for or handle an API key: the user writes it into `.env`. Never commit `.env`, `data/` or `lists/`: they hold real people's data.
