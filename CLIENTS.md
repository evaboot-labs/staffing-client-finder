# The clients you look for

Status: EXAMPLE

The agent and `finder.py` read this file before every run. The example is a tech staffing agency that places software engineers in the UK. Replace it with your own desk, then set `Status: yours`.

## Your desk

- desk: software engineers
- region: the UK
- proof: PASTE ONE LINE OF PROOF, for example the roles you filled for similar teams this year

## Account search (Sales Navigator filters)

- Headquarters location: United Kingdom
- Industry: Software Development
- Company headcount: 51-200; 201-500
- Company headcount growth: at least 10% in one year
- Spotlight, Job opportunities: Hiring on LinkedIn

Sales Navigator no longer offers a department headcount growth filter in the account search. `finder.py` reads the department headcounts from the export instead.

## Who to reach (read by finder.py)

- hiring_manager_titles: CTO; Chief Technology Officer; VP Engineering; Vice President of Engineering; Head of Engineering; Director of Engineering; Engineering Director; Engineering Manager
- talent_titles: Head of Talent; Talent Acquisition; Head of People; Head of Recruitment; Recruitment Manager
- hiring_manager_order: Head of Engineering; VP; Vice President; Director of Engineering; Engineering Director; CTO; Chief Technology Officer; Engineering Manager
- exclude_title_words: Assistant; Intern; Coordinator

## Checks on each company (read by finder.py)

- employee_ranges: 51 to 200; 201 to 500
- growth_min: 10
- team_departments: Engineering; Information Technology
- competitor_words: recruitment agency; recruiting agency; staffing; recruiter; recruiters; talent marketplace; hiring platform; executive search; headhunt

A lead is kept when the title is a hiring manager or a talent leader, the company size is in `employee_ranges`, the one-year headcount growth is at least `growth_min`, and the company description has no `competitor_words` word (a recruiting business is a competitor, not a client).

## First messages (read by finder.py)

- hiring_manager_message: Hi {first_name}, {company} grew {growth_1y}% in a year and is hiring on LinkedIn, with {team} people in engineering and IT today. Teams growing that fast usually have more open roles than interview slots. We place {desk} in {region}: {proof}. Worth 15 minutes on the role you most need filled?
- talent_message: Hi {first_name}, {company} grew {growth_1y}% in a year and is hiring on LinkedIn, with a people team of {hr} covering it. When the hiring plan grows faster than the team, an agency on the hardest roles takes the pressure off. We place {desk} in {region}: {proof}. Open to a short call about the roles that stay open longest?

Placeholders: `{first_name}`, `{company}`, `{growth_1y}`, `{growth_6m}`, `{employees}`, `{team}` (the sum of `team_departments`), `{hr}` (Human Resources), `{desk}`, `{region}`, `{proof}`.
