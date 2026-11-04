#!/usr/bin/env python3
"""Staffing client finder: the people search and the sorted lead list.

  python3 finder.py people-url <account_list_id>
      The Sales Navigator lead search inside your account list, with the titles in CLIENTS.md.
  python3 finder.py sort <export.json> [--csv lists/x.csv] [--md lists/x.md]
      Sorts an Evaboot lead export: hiring manager or talent leader, company checks, the hiring signal,
      who to contact first at each company, and a first message per person.

Python 3.9+, standard library only.
"""
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent


def config(path=ROOT / "CLIENTS.md"):
    """Every `- key: value` line of CLIENTS.md. Lists are separated by `;`."""
    cfg = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^- ([a-z_0-9]+): (.*)$", line.strip())
        if m:
            cfg[m.group(1)] = m.group(2).strip()
    return cfg


def items(cfg, key):
    return [x.strip() for x in cfg.get(key, "").split(";") if x.strip()]


def boolean_titles(cfg):
    titles = items(cfg, "hiring_manager_titles") + items(cfg, "talent_titles")
    q = lambda t: f'"{t}"' if " " in t else t
    text = "(" + " OR ".join(q(t) for t in titles) + ")"
    excl = items(cfg, "exclude_title_words")
    if excl:
        text += " NOT (" + " OR ".join(q(t) for t in excl) + ")"
    return text


def people_url(list_id, cfg):
    query = (f"(filters:List((type:ACCOUNT_LIST,values:List((id:{list_id},selectionType:INCLUDED))),"
             f"(type:CURRENT_TITLE,values:List((text:{quote(boolean_titles(cfg), safe='')},selectionType:INCLUDED)))))")
    return "https://www.linkedin.com/sales/search/people?query=" + quote(query, safe="()")


def num(v):
    try:
        return float(str(v).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def departments(p):
    """'Engineering: 69\\nSales: 35' -> {'Engineering': 69, 'Sales': 35}"""
    out = {}
    for line in str(p.get("Department Headcounts") or "").splitlines():
        if ":" in line:
            k, v = line.rsplit(":", 1)
            out[k.strip()] = int(num(v) or 0)
    return out


def norm(s):
    """Lower case, punctuation and "of" removed: "VP, Engineering" and "VP of Engineering" read "vp engineering"."""
    s = re.sub(r"[^a-z0-9&]+", " ", str(s).lower())
    return " " + re.sub(r"\s+", " ", re.sub(r"\bof\b", " ", s)).strip() + " "


def has_any(text, words):
    """The words found in text, whole words only."""
    text = norm(text)
    return [w for w in words if norm(w) in text]


def persona(title, cfg):
    if has_any(title, items(cfg, "exclude_title_words")):
        return None
    if has_any(title, items(cfg, "talent_titles")):
        return "talent"
    if has_any(title, items(cfg, "hiring_manager_titles")):
        return "hiring manager"
    return None


def rank(title, cfg):
    """Position of the title in hiring_manager_order: lower = contact first."""
    order = items(cfg, "hiring_manager_order")
    hits = [i for i, w in enumerate(order) if has_any(title, [w])]
    return min(hits) if hits else len(order)


def tenure(p):
    """Years and months in the role, read together (Months alone is the remainder, not the total)."""
    y, m = int(num(p.get("Years in Position")) or 0), int(num(p.get("Months in Position")) or 0)
    return f"{y} y {m} m" if y else f"{m} m"


def sort(export_path, cfg):
    data = json.loads(Path(export_path).read_text())
    prospects = data.get("prospects") or data.get("result", {}).get("prospects") or []
    ranges = items(cfg, "employee_ranges")
    growth_min = num(cfg.get("growth_min")) or 0
    team_deps = items(cfg, "team_departments")
    rows = []
    for p in prospects:
        title = str(p.get("Current Job") or "").strip()
        company = p.get("Company Name") or ""
        deps = departments(p)
        g1, g6 = num(p.get("Company Employee Growth 1 Year (%)")), num(p.get("Company Employee Growth 6 Months (%)"))
        role = persona(title, cfg)
        about = f"{p.get('Company Description') or ''} {p.get('Company Specialities') or ''}"
        drop = ""
        if not role:
            drop = "title is not a hiring manager or a talent leader"
        elif ranges and p.get("Company Employee Range") not in ranges:
            drop = f"company size {p.get('Company Employee Range')}, outside your account search"
        elif g1 is None or g1 < growth_min:
            drop = f"headcount growth {'unknown' if g1 is None else f'{g1:g}%'} in a year, under {growth_min:g}%"
        elif has_any(about, items(cfg, "competitor_words")):
            drop = f"a recruiting business ({', '.join(has_any(about, items(cfg, 'competitor_words')))}), a competitor"
        rows.append({
            "keep": "no" if drop else "yes", "why": drop, "persona": role or "", "first": "",
            "name": p.get("Full Name") or "", "first_name": p.get("First Name") or "", "title": title,
            "company": company, "employees": p.get("Company Employee Range") or "",
            "growth_6m": "" if g6 is None else f"{g6:g}", "growth_1y": "" if g1 is None else f"{g1:g}",
            "team": sum(deps.get(d, 0) for d in team_deps), "hr": deps.get("Human Resources", 0),
            "in_role": tenure(p), "location": p.get("Location") or "",
            "email": p.get("Email") or "", "email_status": p.get("Email Status") or "not found",
            "open_profile": "yes" if str(p.get("Is Open Profile")).lower() == "true" else "no",
            "linkedin": p.get("Linkedin URL Public") or p.get("Sales Navigator URL") or "",
            "_rank": rank(title, cfg),
        })
    kept = [r for r in rows if r["keep"] == "yes"]
    # One hiring manager and one talent leader to contact first per company.
    for comp in {r["company"] for r in kept}:
        for who in ("hiring manager", "talent"):
            group = sorted((r for r in kept if r["company"] == comp and r["persona"] == who),
                           key=lambda r: (r["_rank"], r["email_status"] != "safe"))
            if group:
                group[0]["first"] = "yes"
    for r in kept:
        tpl = cfg.get("hiring_manager_message" if r["persona"] == "hiring manager" else "talent_message", "")
        r["message"] = tpl.format(first_name=r["first_name"], company=r["company"], growth_1y=r["growth_1y"],
                                  growth_6m=r["growth_6m"], employees=r["employees"], team=r["team"], hr=r["hr"],
                                  desk=cfg.get("desk", ""), region=cfg.get("region", ""), proof=cfg.get("proof", ""))
    for r in rows:
        r.setdefault("message", "")
        r.pop("_rank")
    rows.sort(key=lambda r: (r["keep"] != "yes", -(num(r["growth_1y"]) or 0), r["company"], r["first"] != "yes"))
    return rows


COLS = ["keep", "first", "persona", "name", "title", "company", "employees", "growth_6m", "growth_1y", "team", "hr",
        "in_role", "location", "email", "email_status", "open_profile", "linkedin", "why", "message"]


def table(rows):
    lines = ["| keep | first | persona | title | company | growth 1y | eng+IT | email | why |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['keep']} | {r['first']} | {r['persona']} | {r['title']} | {r['company']} | "
                     f"{r['growth_1y']}% | {r['team']} | {r['email_status']} | {r['why']} |")
    kept = [r for r in rows if r["keep"] == "yes"]
    lines.append(f"\n{len(kept)} of {len(rows)} people kept, at {len({r['company'] for r in kept})} companies.")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2 or argv[0] not in ("people-url", "sort"):
        print(__doc__)
        return 1
    cfg = config()
    if argv[0] == "people-url":
        print(people_url(argv[1], cfg))
        return 0
    rows = sort(argv[1], cfg)
    print(table(rows))
    if "--csv" in argv:
        out = Path(argv[argv.index("--csv") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    if "--md" in argv:
        out = Path(argv[argv.index("--md") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        body = [table(rows), "\n## First messages\n"]
        for r in rows:
            if r["keep"] == "yes":
                body.append(f"**{r['name']}**, {r['title']} at {r['company']} ({r['persona']}"
                            f"{', contact first' if r['first'] else ''}):\n\n> {r['message']}\n")
        out.write_text("\n".join(body))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
