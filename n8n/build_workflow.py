"""Builds n8n/staffing-client-finder.json. Run: python3 n8n/build_workflow.py

Every Monday at 8 (or on Run now), Evaboot saves the companies of your Sales Navigator account search (hiring on
LinkedIn, growing) into a new account list, exports the hiring managers and talent leaders inside that list with
verified emails, a Code node sorts them like finder.py (persona, company checks, who to contact first, first
message), skips the people already in your sheet, and the new leads land in your Google Sheet.
"""
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MCP = "https://mcp.evaboot.com/mcp"
EVABOOT_CRED = {"httpBearerAuth": {"id": "", "name": "Evaboot MCP (Bearer)"}}
SHEETS_CRED = {"googleSheetsOAuth2Api": {"id": "", "name": "Google Sheets account"}}
ACCOUNT_SEARCH = ("https://www.linkedin.com/sales/search/company?query=(filters%3AList((type%3ACOMPANY_HEADCOUNT%2Cvalues"
                  "%3AList((id%3AD%2Ctext%3A51-200%2CselectionType%3AINCLUDED)%2C(id%3AE%2Ctext%3A201-500%2CselectionType"
                  "%3AINCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A101165590%2Ctext%3AUnited%2520Kingdom%2CselectionType"
                  "%3AINCLUDED)))%2C(type%3AINDUSTRY%2Cvalues%3AList((id%3A4%2Ctext%3ASoftware%2520Development%2CselectionType"
                  "%3AINCLUDED)))%2C(type%3AJOB_OPPORTUNITIES%2Cvalues%3AList((id%3AJO1%2Ctext%3AHiring%2520on%2520Linkedin"
                  "%2CselectionType%3AINCLUDED)))%2C(type%3ACOMPANY_HEADCOUNT_GROWTH%2CrangeValue%3A(min%3A10))))")


def clients_md():
    """The profile comes from CLIENTS.md, so the n8n version and finder.py use the same titles, checks and messages."""
    cfg = {}
    for line in (ROOT / "CLIENTS.md").read_text().splitlines():
        m = re.match(r"^- ([a-z_0-9]+): (.*)$", line.strip())
        if m:
            cfg[m.group(1)] = m.group(2).strip()
    lists = ["hiring_manager_titles", "talent_titles", "hiring_manager_order", "exclude_title_words",
             "employee_ranges", "team_departments", "competitor_words"]
    out = {k: [x.strip() for x in cfg[k].split(";") if x.strip()] for k in lists}
    out.update({k: cfg[k] for k in ("desk", "region", "proof", "hiring_manager_message", "talent_message")})
    out["growth_min"] = float(cfg["growth_min"])
    return out


nodes, connections = [], {}


def node(name, type_, version, params, pos, creds=None, **extra):
    n = {"parameters": params, "id": str(uuid.uuid4()), "name": name, "type": type_,
         "typeVersion": version, "position": pos, **extra}
    if creds:
        n["credentials"] = creds
    nodes.append(n)


def link(a, b, out=0):
    connections.setdefault(a, {}).setdefault("main", [])
    while len(connections[a]["main"]) <= out:
        connections[a]["main"].append([])
    connections[a]["main"][out].append({"node": b, "type": "main", "index": 0})


def mcp_call(name, tool, json_expr, pos):
    node(name, "@n8n/n8n-nodes-langchain.mcpClient", 1.1, {
        "endpointUrl": MCP, "authentication": "bearerAuth",
        "tool": {"__rl": True, "mode": "list", "value": tool, "cachedResultName": tool},
        "inputMode": "json", "jsonInput": json_expr, "options": {"timeout": 120000},
    }, pos, EVABOOT_CRED, executeOnce=True)


def code(name, js, pos, **extra):
    node(name, "n8n-nodes-base.code", 2, {"jsCode": js}, pos, **extra)


def is_equal(name, left, right, pos):
    node(name, "n8n-nodes-base.if", 2.2, {"conditions": {
        "options": {"caseSensitive": False, "typeValidation": "loose", "version": 2},
        "conditions": [{"id": str(uuid.uuid4()), "leftValue": left, "rightValue": right,
                        "operator": {"type": "string", "operation": "equals"}}],
        "combinator": "and"}, "options": {}}, pos)


def sheet(name, op, pos, **params):
    p = {"operation": op,
         "documentId": {"__rl": True, "mode": "url", "value": "={{ $('Your settings').first().json.%s }}" % params.pop("tab")},
         "options": {}, **params}
    p["sheetName"] = {"__rl": True, "mode": "url", "value": p["documentId"]["value"]}
    extra = {"alwaysOutputData": True, "executeOnce": True} if op == "read" else {}
    node(name, "n8n-nodes-base.googleSheets", 4.7, p, pos, SHEETS_CRED, **extra)


def poll(prefix, launch, check_tool, id_expr, done_value, pos):
    """Wait, check the job, loop until it is done; stop on a failed job."""
    x, y = pos
    node(f"Wait 30 s ({prefix})", "n8n-nodes-base.wait", 1.1, {"amount": 30}, [x, y])
    mcp_call(f"Check the {prefix}", check_tool, "={{ JSON.stringify(%s) }}" % id_expr, [x + 220, y])
    is_equal(f"{prefix.capitalize()} done?", "={{ $json.structuredContent.result.status }}", done_value, [x + 440, y])
    code(f"Still running? ({prefix})", r"""
// Stop instead of waiting forever when the job failed.
const r = $json.structuredContent.result;
if (r.failure_reason || r.error_message || /FAIL|ERROR|CANCEL/i.test(r.status || '')) throw new Error(`The job stopped: ${r.status} ${r.failure_reason || r.error_message || ''}`);
return [$input.first()];
""", [x + 440, y + 180])
    link(launch, f"Wait 30 s ({prefix})")
    link(f"Wait 30 s ({prefix})", f"Check the {prefix}")
    link(f"Check the {prefix}", f"{prefix.capitalize()} done?")
    link(f"{prefix.capitalize()} done?", f"Still running? ({prefix})", out=1)
    link(f"Still running? ({prefix})", f"Wait 30 s ({prefix})")


PEOPLE_JS = r"""
// Same as finder.py people-url: the hiring managers and talent leaders inside this week's account list.
const P = JSON.parse($('Your settings').first().json.profile);
const lists = $json.structuredContent.result.result.lists || [];
if (!lists.length || !lists[0].list_id) throw new Error('Sales Navigator saved no account: widen the account search.');
const q = t => t.includes(' ') ? `"${t}"` : t;
let titles = '(' + [...P.hiring_manager_titles, ...P.talent_titles].map(q).join(' OR ') + ')';
if (P.exclude_title_words.length) titles += ' NOT (' + P.exclude_title_words.map(q).join(' OR ') + ')';
const enc = s => encodeURIComponent(s).replace(/\(/g, '%28').replace(/\)/g, '%29');
const query = `(filters:List((type:ACCOUNT_LIST,values:List((id:${lists[0].list_id},selectionType:INCLUDED))),`
  + `(type:CURRENT_TITLE,values:List((text:${enc(titles)},selectionType:INCLUDED)))))`;
const url = 'https://www.linkedin.com/sales/search/people?query=' + encodeURIComponent(query).replace(/%28/g, '(').replace(/%29/g, ')');
return [{ json: { url, accounts: lists[0].count } }];
"""

SORT_JS = r"""
// Same as finder.py sort: persona, company checks, who to contact first, first message.
const P = JSON.parse($('Your settings').first().json.profile);
const seen = new Set($('People already in your sheet').all().map(i => String(i.json.LinkedIn || '')).filter(Boolean));
const norm = s => ' ' + String(s || '').toLowerCase().replace(/[^a-z0-9&]+/g, ' ').replace(/\bof\b/g, ' ').replace(/\s+/g, ' ').trim() + ' ';
const hasAny = (text, words) => words.filter(w => norm(text).includes(norm(w)));
const num = v => { const n = parseFloat(String(v ?? '').replace(/[,%]/g, '')); return isNaN(n) ? null : n; };
const deps = p => Object.fromEntries(String(p['Department Headcounts'] || '').split('\n').filter(l => l.includes(':'))
  .map(l => { const i = l.lastIndexOf(':'); return [l.slice(0, i).trim(), parseInt(l.slice(i + 1)) || 0]; }));
const rank = t => { const h = P.hiring_manager_order.map((w, i) => hasAny(t, [w]).length ? i : 99); return Math.min(...h); };
const today = $now.toFormat('yyyy-MM-dd');
const rows = [];
for (const p of $json.structuredContent.result.prospects || []) {
  const linkedin = p['Linkedin URL Public'] || p['Sales Navigator URL'] || '';
  if (seen.has(linkedin)) continue;
  const title = String(p['Current Job'] || '').trim(), d = deps(p);
  const g1 = num(p['Company Employee Growth 1 Year (%)']), g6 = num(p['Company Employee Growth 6 Months (%)']);
  const persona = hasAny(title, P.exclude_title_words).length ? '' : hasAny(title, P.talent_titles).length ? 'talent'
    : hasAny(title, P.hiring_manager_titles).length ? 'hiring manager' : '';
  const about = `${p['Company Description'] || ''} ${p['Company Specialities'] || ''}`;
  let why = '';
  if (!persona) why = 'title is not a hiring manager or a talent leader';
  else if (P.employee_ranges.length && !P.employee_ranges.includes(p['Company Employee Range'])) why = `company size ${p['Company Employee Range']}, outside your account search`;
  else if (g1 === null || g1 < P.growth_min) why = `headcount growth ${g1 === null ? 'unknown' : g1 + '%'} in a year, under ${P.growth_min}%`;
  else if (hasAny(about, P.competitor_words).length) why = `a recruiting business (${hasAny(about, P.competitor_words).join(', ')}), a competitor`;
  const team = P.team_departments.reduce((s, k) => s + (d[k] || 0), 0), hr = d['Human Resources'] || 0;
  const tpl = persona === 'hiring manager' ? P.hiring_manager_message : P.talent_message;
  const message = why ? '' : tpl.replace(/\{(\w+)\}/g, (m, k) => ({ first_name: p['First Name'] || '', company: p['Company Name'] || '',
    growth_1y: g1 ?? '', growth_6m: g6 ?? '', employees: p['Company Employee Range'] || '', team, hr, desk: P.desk, region: P.region, proof: P.proof })[k] ?? m);
  rows.push({ Date: today, Keep: why ? 'no' : 'yes', First: '', Persona: persona, Name: p['Full Name'] || '', Title: title,
    Company: p['Company Name'] || '', 'Growth 1y %': g1 ?? '', 'Eng + IT': team, 'People team': hr,
    Email: p['Email'] || '', 'Email status': p['Email Status'] || 'not found', LinkedIn: linkedin, Why: why, Message: message,
    _rank: rank(title) });
}
if (!rows.length) throw new Error('No new person in this run: everyone is already in your sheet.');
for (const who of ['hiring manager', 'talent']) {
  const firsts = {};
  for (const r of rows.filter(r => r.Keep === 'yes' && r.Persona === who)
    .sort((a, b) => a._rank - b._rank || (a['Email status'] !== 'safe') - (b['Email status'] !== 'safe')))
    if (!firsts[r.Company]) { firsts[r.Company] = true; r.First = 'yes'; }
}
return rows.sort((a, b) => (a.Keep !== 'yes') - (b.Keep !== 'yes') || (b['Growth 1y %'] || 0) - (a['Growth 1y %'] || 0)
  || a.Company.localeCompare(b.Company) || (a.First !== 'yes') - (b.First !== 'yes'))
  .map(({ _rank, ...r }) => ({ json: r }));
"""

node("Every Monday at 8", "n8n-nodes-base.scheduleTrigger", 1.2, {"rule": {"interval": [
    {"field": "weeks", "triggerAtDay": [1], "triggerAtHour": 8}]}}, [0, 0])
node("Run now", "n8n-nodes-base.manualTrigger", 1, {}, [0, 200])
node("Your settings", "n8n-nodes-base.set", 3.4, {"assignments": {"assignments": [
    {"id": str(uuid.uuid4()), "name": k, "type": t, "value": v} for k, t, v in [
        ("account_search_url", "string", ACCOUNT_SEARCH),
        ("accounts_per_run", "number", 25),
        ("people_per_run", "number", 10),
        ("leads_tab_url", "string", "PASTE_THE_LEADS_TAB_URL_WITH_GID"),
        ("profile", "string", json.dumps(clients_md(), ensure_ascii=False)),
    ]]}, "options": {}}, [220, 100])
sheet("People already in your sheet", "read", [440, 100], tab="leads_tab_url")
mcp_call("Save the accounts", "create_account_list_from_search",
         "={{ JSON.stringify({ search_url: $('Your settings').first().json.account_search_url, "
         "max_results: $('Your settings').first().json.accounts_per_run, "
         "name: 'Staffing client finder ' + $now.toFormat('yyyy-MM-dd') }) }}", [660, 100])
poll("account list", "Save the accounts", "get_list_from_search_status",
     "{ job_id: $('Save the accounts').first().json.structuredContent.result.job_id }", "complete", [880, 100])
code("People search", PEOPLE_JS, [220, 520], executeOnce=True)
mcp_call("Export the people", "export_sn_search_or_list",
         "={{ JSON.stringify({ search_url: $json.url, max_results: $('Your settings').first().json.people_per_run, "
         "name: 'Staffing client finder people ' + $now.toFormat('yyyy-MM-dd') }) }}", [440, 520])
poll("people export", "Export the people", "get_export",
     "{ extraction_id: $('Export the people').first().json.structuredContent.result.extraction_id, limit: 1000 }",
     "EXECUTED", [660, 520])
code("Sort the leads", SORT_JS, [1320, 520])
sheet("Add to Leads", "append", [1540, 520], tab="leads_tab_url",
      columns={"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []})

for a, b in [("Every Monday at 8", "Your settings"), ("Run now", "Your settings"),
             ("Your settings", "People already in your sheet"),
             ("People already in your sheet", "Save the accounts"),
             ("People search", "Export the people"), ("Sort the leads", "Add to Leads")]:
    link(a, b)
link("Account list done?", "People search", out=0)
link("People export done?", "Sort the leads", out=0)

workflow = {"name": "Staffing client finder (Evaboot MCP)", "nodes": nodes, "connections": connections,
            "settings": {"executionOrder": "v1"}, "pinData": {}}
out = Path(__file__).with_name("staffing-client-finder.json")
out.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n")
print(out, len(nodes), "nodes")
