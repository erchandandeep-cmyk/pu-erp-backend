# University-wide upgrade — Phase 1 (data model foundation)

This is the first phase of turning ME-ERP from a single-department app
into something that can grow to cover the whole university without a
rewrite each time. It does **not** try to build admissions, fees,
exams, hostels, etc. in one shot — see "What Phase 1 deliberately does
NOT do" below.

## What changed

1. **New `institutions` app** (`institutions/models.py`) — one
   `Institution` model represents the university, regional centres,
   constituent colleges, neighbourhood campuses, affiliated colleges,
   and departments, all as a single tree (`parent` field). Add
   Punjabi University's real regional centres/constituent colleges/
   campuses/departments any time from `/admin/` under
   **University Structure -> Institutions / Units** — no code changes,
   no new migrations, ever again for this part.

2. **`accounts.User` gained an `institution` field** — a real link
   into that tree, alongside the old `department` text field (kept for
   backward compatibility; it now auto-syncs from `institution` once
   set).

3. **Generic file uploads** (`common/validators.py`) — every
   attachment field (applications, announcements, documents) now
   accepts `.pdf .doc .docx .xls .xlsx .jpg .jpeg .png`, capped at
   15 MB, with a clear error if someone tries another type. Signatures
   stay image-only, capped at 5 MB.

4. **Application IDs are no longer hardcoded to `MECH`** — they now
   use the applicant's institution code (falls back to `MECH` for
   existing accounts not yet linked).

5. **CSV bulk-import** accepts an optional `institution_code` column
   so office staff anywhere in the university can bulk-import their
   own users once their department/college exists in
   Institutions/Units.

6. **API**: added a read-only `/api/institutions/` endpoint (filter
   with `?kind=DEPARTMENT` or `?parent=<id>`) so the Android app can
   show pickers as the tree grows, and `institution`/`institution_name`
   were added to the user payload.

## How to apply this to your existing data (run once)

```
python manage.py makemigrations institutions accounts applications announcements documents
python manage.py migrate
python manage.py seed_institutions
```

`seed_institutions` creates the Punjabi University root node, creates
a Department row for "Mechanical Engineering" (and for any other
department text already in your user data), and links your existing
users to it. It is safe to re-run and never deletes or overwrites your
existing `department` text.

## What Phase 1 deliberately does NOT do

It does not add admissions, examinations, results, fee collection, HR/
payroll, hostel, library, transport, or affiliation-management
modules for 200+ colleges. Those are each substantial projects on
their own. The point of Phase 1 is that when you're ready to build any
of them, they can plug into the same Institution tree and the same
file-upload rules instead of each needing its own one-off department
model — build one module at a time, test it, then move to the next.
