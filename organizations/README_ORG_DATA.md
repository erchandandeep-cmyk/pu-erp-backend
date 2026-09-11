# Populating the university's real structure

`org_units_starter_template.csv` in this folder has 4 example rows only
(Vice-Chancellor, Registrar, Dean Academics, and your existing Mechanical
Engineering department) so you can see the CSV format and test the import.

It is **not** a verified list of the university's 70+ departments,
5+ regional centres, 10+ constituent colleges, 10+ neighbourhood campuses,
or 200+ affiliated colleges. Do not treat it as official.

**Why I didn't scrape the university website and fill this in for you:**
a wrong department name, wrong reporting line, or wrong office under a
real Vice-Chancellor/Registrar is worse than an empty template - it looks
official and spreads bad information about a real institution. The
university's own administration (Registrar's office / e-office team) is
the correct source of truth for this list, and they should approve it
before it goes into a system that issues real approvals.

## How to fill it in for real
1. Get the current, approved list of departments/centres/colleges/offices
   from the university (e-office team, Registrar's office, or the
   official website's "Departments"/"Colleges" pages) - as a spreadsheet.
2. Convert it to this CSV's column format:
   `code,name,unit_type,parent_code,contact_email,contact_phone,address`
   - `unit_type` must be one of: TEACHING_DEPT, RESEARCH_CENTRE,
     REGIONAL_CENTRE, CONSTITUENT_COLLEGE, NEIGHBOURHOOD_CAMPUS,
     AFFILIATED_COLLEGE, ADMIN_OFFICE
   - `code` is any short unique code you choose (e.g. MECH, RC-BTI, VC).
   - `parent_code` is optional - use it to show reporting lines
     (e.g. a Regional Centre's departments report up to that centre).
3. Import it (see cmd steps in the main reply). Re-running the same file
   later updates existing codes instead of duplicating them, so you can
   add colleges in batches over time.
4. Ask me for help converting a spreadsheet you already have (e.g. the
   university's own department list) into this CSV format - that's a
   much safer way to get from 1 department to the whole university than
   me guessing at it from search results.
