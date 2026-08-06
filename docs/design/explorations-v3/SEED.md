# SEED — the bare minimum brief (given to every generator, nothing else)

Build a single-page website for this product:

UGMI (ugmi.ca) is a free, searchable list of internships. 1,427 open
listings right now, mostly Canadian. No account, no email, no paywall on
the list. There is one paid thing: for $15/month CAD you get a list of 10
hand-picked internships every Monday, matched to you, each with a named
contact person. It is built and run by one university student at Waterloo.
Payment goes through Stripe. Instagram: @sleppyeric.

Sample listings you may use (invent similar ones if you need more):

| Company | Role | Location | Pay | Closes | Added |
|---|---|---|---|---|---|
| Shopify | Software Engineering Intern | Remote, Canada | $34/hr CAD | in 3 days | 2d ago |
| Amazon | SDE Intern | Vancouver | $41/hr CAD | in 5 days | 2w ago |
| RBC | Amplify Developer Intern | Toronto | $31/hr CAD | in 6 days | today |
| Stripe | Software Engineer Intern | Remote, US | not listed | in 9 days | 5d ago |
| Wealthsimple | Data Science Intern | Toronto | not listed | in 11 days | 4d ago |
| OpenText | Software Developer Co-op | Waterloo | $30/hr CAD | in 13 days | 1w ago |
| ecobee | Embedded Systems Intern | Toronto | $29/hr CAD | Aug 31 | 1d ago |
| TELUS | Network Engineering Co-op | Vancouver | $28/hr CAD | Sep 2 | 6d ago |
| Sanctuary AI | Robotics Software Intern | Vancouver | not listed | Sep 8 | 6d ago |
| BC Hydro | Engineering Co-op | Vancouver | $27/hr CAD | Sep 12 | 3d ago |
| Google | STEP Intern | Waterloo | not listed | Sep 19 | 2d ago |
| Ubisoft | Gameplay Programmer Intern | Montreal | $30/hr CAD | none listed | 1w ago |

Hard technical requirements (non-negotiable):
- ONE self-contained .html file. Inline CSS + JS. Zero external requests:
  no CDNs, no webfonts, no remote images, no analytics. Must render
  offline via file://. System font stacks only.
- Mobile-first at 390px wide, then desktop. No horizontal scroll.
- File starts with `<!-- INTERNAL DESIGN MOCKUP - sample listing data -->`.
- Any visual assets must be inline (CSS shapes, inline SVG you write).

Everything else — layout, sections, tone, copy, colors, type, how the paid
thing is pitched, whether there are filters — is entirely your call.
Design it however you believe is best.
