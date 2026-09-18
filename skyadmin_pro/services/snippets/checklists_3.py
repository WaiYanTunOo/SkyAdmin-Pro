from .types import Snippet

CHECKLISTS_3: tuple[Snippet, ...] = (
    Snippet(
        "Cross-Border Remittance & FX",
        "Multi-currency checklist:\n"
        "1. FX rate: official central bank daily rate for the exact transaction date "
        "(preceding business day if weekend/holiday); save screenshot/PDF as supporting "
        "evidence attached to the invoice.\n"
        "2. Intercompany billing: confirm agreed currency (USD/THB/MMK) and clear service "
        "description; at month-end reconcile AR-Yangon vs AP-Bangkok to net exactly zero.\n"
        "3. Outward remittance: deduct cross-border withholding tax (P.N.D.54 / P.P.36) "
        "before transfer; reverse-charge VAT where applicable; prepare bank forms "
        "(gross, deducted tax, net payable); packet = commercial invoice + contract + "
        "tax calculation sheet.\n"
        "4. Month-end FX: book realized gain/loss on executed payments; revalue unpaid "
        "FX A/R and A/P at the month-end closing rate.\n"
        "5. Archive in 'Multi-Currency & Remittance'; naming convention: "
        "20260805_YangonOffice_USD5000_Invoice_and_FXRate.",
    ),
    Snippet(
        "Visa & Work Permit Renewal",
        "Financial documents for visa/work permit renewal:\n"
        "1. [60-90 days before] Initiate: get the document checklist from the visa agent; "
        "confirm the reporting period (last 3-6 months).\n"
        "2. [45-60 days] Extract: 3-6 months P.N.D.1 and P.P.30 each with Pay-in Slip + "
        "e-Receipt; SSF contribution reports + receipts; latest audited financial "
        "statement; most recent P.N.D.50.\n"
        "3. [30-45 days] Certify: print every document; check out the corporate seal; "
        "stamp every page; Director signs every page in blue ink.\n"
        "4. [25-30 days] Handover: QA that the P.N.D.1 name matches the passport exactly "
        "and salary meets the legal minimum; waterproof pack; trackable courier; log "
        "dispatch in the Physical Asset Register.\n"
        "5. Post-renewal: request scans of the new visa stamp + work permit booklet; "
        "upload to the employee file; update the new expiry dates in the tracker.",
    ),
    Snippet(
        "New Client Accounting Onboarding",
        "New client onboarding:\n"
        "1. [Days 1-2] Setup: create '[Client Name] - Accounting Records' root folder "
        "with subfolders Tax Returns / Bank Statements / Monthly Financials / Payroll / "
        "Corporate Documents; create the software profile (tax ID, address, currency).\n"
        "2. [Days 3-5] Handover: obtain final Trial Balance, Balance Sheet and GL from "
        "the previous accountant; map the COA to the standardized framework; request "
        "leases, loan schedules, asset registers and BOI certificates.\n"
        "3. [Days 6-8] Opening balances: input strictly from finalized documents; verify "
        "opening bank balances vs physical statements; load AR/AP aging; Manager sign-off.\n"
        "4. [Days 9-10] Welcome packet: 'Welcome to Accounting' email, secure upload "
        "links, deadlines (invoices by the 5th, tax filing by the 15th), and templates "
        "for report requests.\n"
        "5. [Month 1 close] Trial run: execute close + filing per SOP; monitor deadline "
        "adherence and correct behavior early; 15-minute review call after the first "
        "financial package.",
    ),
)
