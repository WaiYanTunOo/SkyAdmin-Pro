from .types import Snippet

CHECKLISTS_2: tuple[Snippet, ...] = (
    Snippet(
        "Courier Pack",
        "Outgoing courier checklist:\n"
        "1. Client name (as in passport), phone, delivery address\n"
        "2. List of originals in the envelope\n"
        "3. Cover note — Burmese to the client\n"
        "4. Tracking number logged in SkyAdmin Pro\n"
        "5. Driver: Grab / Lalamove / Kerry / other\n"
        "6. Message the client in Burmese with the tracking number\n",
    ),
    Snippet(
        "Monthly Tax Filing (WHT & VAT)",
        "Monthly tax & compliance workflow:\n"
        "1. [1st-5th] Collect & reconcile: bank statements, purchase invoices, sales "
        "receipts, expense claims, payroll summaries. Audit tax invoices (name, address, "
        "tax ID). Flag missing items.\n"
        "2. [6th-8th] Compute: P.N.D.1 (salaries), P.N.D.3 (individuals), P.N.D.53 "
        "(corporates), P.P.30 VAT net payable/refundable. Generate drafts.\n"
        "3. [9th-11th] Review & authorize: Manager sign-off, tax summary email to client, "
        "explicit written authorization before filing.\n"
        "4. [by 15th] E-file & pay: Revenue e-Filing portal, submit, Pay-in Slip, pay or "
        "forward to client immediately.\n"
        "5. [16th-20th] Archive: upload final forms + calculation sheets + official "
        "e-Receipts to the client's 'Tax Returns' folder by month/year; mark the month "
        "'Closed'; cross-link to monthly financials.",
    ),
    Snippet(
        "Independent Audit Prep & Handover",
        "Year-end audit preparation:\n"
        "1. Year-end close: reconcile all bank/credit-card/petty-cash to the exact "
        "year-end date; record adjusting entries (depreciation, amortization, prepaids, "
        "accruals); draft Trial Balance, P&L and Balance Sheet for Manager review.\n"
        "2. Lead schedules: AR aging, AP aging, inventory valuation, fixed asset "
        "register; reconcile intercompany (Bangkok-Yangon); tie every schedule to the TB.\n"
        "3. Data room: create read-only 'Audit Data Room [Year]'; upload working papers, "
        "draft financials, GL export, 12 months of filed tax returns, bank statements, "
        "payroll summaries and vendor contracts.\n"
        "4. Handover: send secure links to the audit firm with a summary of significant "
        "changes; set the 48-hour query-response SLA.\n"
        "5. Query management: log all inquiries and dates provided; review proposed "
        "adjustments with Manager and client; post final audit entries. Never make "
        "retroactive changes after the Trial Balance handover.",
    ),
    Snippet(
        "Payroll & Statutory Deductions",
        "Monthly payroll cycle:\n"
        "1. [20th-25th] Collect data: timesheets, OT logs, leave records, bonus/commission "
        "schedules; note new hires and resignations; verify written approval for variable pay.\n"
        "2. [26th-27th] Compute: gross pay (incl. OT/allowances/proration), SSF 5% up to "
        "the capped threshold, P.N.D.1 progressive withholding; draft Payroll Register.\n"
        "3. [28th-29th] Authorize: Manager review, then password-protected register to "
        "the client's decision-maker; obtain written authorization of net payout.\n"
        "4. [last working day] Disburse: bulk-payment file to the corporate banking "
        "portal; distribute password-protected digital payslips.\n"
        "5. [by 15th next month] File: P.N.D.1 e-filing + Pay-in Slip; SSF SSO report + "
        "payment slip; download e-Receipts and archive in 'Payroll & Tax'.",
    ),
)
