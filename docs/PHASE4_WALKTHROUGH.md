# Phase 4 — Windows UI walkthrough

Structured manual QA for an **installed** build (`SkyAdminPro-Setup-*.exe` on a clean PC). Run each section at **1100×700** first, then repeat at **1920×1080**. Toggle **Dark** and **Light** in Settings between passes.

**Pass criteria:** no clipped labels, readable inputs while typing, tables scroll, buttons reachable without overlap.

---

## 0. Launch & shell

| Step | Action | Pass? |
|------|--------|-------|
| 0.1 | Launch from **Start Menu → SkyAdmin Pro** — no console flash, window opens | ☐ |
| 0.2 | Sidebar shows 6 nav items; active item highlighted | ☐ |
| 0.3 | Status bar path wraps on narrow width (resize to 1100px) | ☐ |
| 0.4 | Settings → Theme **Dark** → visit each view → inputs have visible borders | ☐ |
| 0.5 | Settings → Theme **Light** → repeat; text contrast OK | ☐ |

---

## 1. Dashboard

| Step | Action | Pass? |
|------|--------|-------|
| 1.1 | Stat card labels wrap; no text stacked on numbers | ☐ |
| 1.2 | Onboard client field stretches (`sticky=ew`) | ☐ |
| 1.3 | Expiry / overdue / supplier trees readable; row colors distinct | ☐ |
| 1.4 | Tax overview tab loads without layout jump | ☐ |
| 1.5 | Monthly report export dialog opens | ☐ |

---

## 2. Document Hub

| Step | Action | Pass? |
|------|--------|-------|
| 2.1 | Open each tab: Smart Renamer, Image to PDF, Agent Bundle, Portal Upload, Archive & Clean, Financial Docs | ☐ |
| 2.2 | Amount / PDF name / financial search fields — themed, readable | ☐ |
| 2.3 | Drop zones visible; no controls hidden below fold at 1100×700 | ☐ |

---

## 3. Database & Tasks

### Tasks

| Step | Action | Pass? |
|------|--------|-------|
| 3.1 | Form sidebar ≥320px; labels above fields | ☐ |
| 3.2 | Client combo + title/category fields expand | ☐ |

### Courier

| Step | Action | Pass? |
|------|--------|-------|
| 3.3 | Same form layout as Tasks | ☐ |

### Clients

| Step | Action | Pass? |
|------|--------|-------|
| 3.4 | Search box themed; table refreshes on type (debounced) | ☐ |
| 3.5 | Add/Edit client dialog — themed entries | ☐ |
| 3.6 | With 50+ clients, search feels responsive | ☐ |

### Renewals

| Step | Action | Pass? |
|------|--------|-------|
| 3.7 | Company row 1, Service row 2; combos full width | ☐ |
| 3.8 | Checklist checkboxes visible when service selected | ☐ |

### Pipeline

| Step | Action | Pass? |
|------|--------|-------|
| 3.9 | Client + Service combos stretch; hint wraps on row 2 | ☐ |

### Suppliers (Directory / Services / Payments)

| Step | Action | Pass? |
|------|--------|-------|
| 3.10 | Each sub-tab opens; form fields themed | ☐ |

### Company Details (embedded)

| Step | Action | Pass? |
|------|--------|-------|
| 3.11 | Selector: company combo row 1, summary row 2 | ☐ |
| 3.12 | General / Tax IDs tabs — themed entries | ☐ |
| 3.13 | VO & CSH tab — address, providers, shareholders themed | ☐ |
| 3.14 | Financial docs add dialog — amount + description themed | ☐ |
| 3.15 | Service renewal dialog — note field themed | ☐ |

---

## 4. Office Hub

| Step | Action | Pass? |
|------|--------|-------|
| 4.1 | Contacts — search + category filter | ☐ |
| 4.2 | Client credentials — password field masked; show/hide works | ☐ |
| 4.3 | Office credentials — same | ☐ |
| 4.4 | Notebook — search field themed | ☐ |

---

## 5. Utilities

| Step | Action | Pass? |
|------|--------|-------|
| 5.1 | Subtitle wraps on resize | ☐ |
| 5.2 | Snippet cards copy to clipboard | ☐ |
| 5.3 | Edit snippets dialog — label entry + textbox themed | ☐ |
| 5.4 | Placeholder fill dialog — token fields themed | ☐ |
| 5.5 | Translator direction + text areas readable | ☐ |

---

## 6. Settings

| Step | Action | Pass? |
|------|--------|-------|
| 6.1 | License line wraps; Sync Now button not crushed | ☐ |
| 6.2 | Data sync line shows last pull + conflict count | ☐ |
| 6.3 | Pricing matrix — form fields stretch; charge-line dialog themed | ☐ |
| 6.4 | Renewal checklists — list picker, add row, inline rows themed | ☐ |
| 6.5 | Encrypted backup — success shows file size | ☐ |
| 6.6 | Restore — preview dialog before confirm; success shows sizes + safety path | ☐ |
| 6.7 | Check database integrity — passes on healthy DB | ☐ |
| 6.8 | Mobile Viewer button opens `/viewer` in browser | ☐ |

---

## 7. Activation (modal)

| Step | Action | Pass? |
|------|--------|-------|
| 7.1 | Settings → Activate / Manage License | ☐ |
| 7.2 | Email + code fields themed; hint text wraps | ☐ |
| 7.3 | Passcode field accepts SKYPASS1 paste | ☐ |

---

## 8. DPI (optional)

| Step | Action | Pass? |
|------|--------|-------|
| 8.1 | Windows Display → 125% scaling | ☐ |
| 8.2 | Repeat steps 1.1, 3.1, 6.1 — no overlap | ☐ |

---

## Sign-off

| | Dark 1100×700 | Light 1100×700 | Dark 1920×1080 |
|--|:---:|:---:|:---:|
| Dashboard | ☐ | ☐ | ☐ |
| Document Hub | ☐ | ☐ | ☐ |
| Database & Tasks | ☐ | ☐ | ☐ |
| Office Hub | ☐ | ☐ | ☐ |
| Utilities | ☐ | ☐ | ☐ |
| Settings | ☐ | ☐ | ☐ |

**Tester:** _______________  **Date:** _______________  **Build:** `dist\SkyAdminPro-Setup-<version>.exe`
