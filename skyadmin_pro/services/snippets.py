"""Quick replies and checklists.

Clients receive Burmese. Thai suppliers get simple English plus krub / 🙏
(no Thai script).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import NamedTuple

from skyadmin_pro.config import SETTING_SNIPPET_OVERRIDES


class Snippet(NamedTuple):
    label: str
    text: str


CLIENT_REPLIES: tuple[Snippet, ...] = (
    Snippet(
        "Need clear photo",
        "မင်္ဂလာပါ။\n\n"
        "ဒီစာရွက်စာတမ်းကို ပိုပြီးရှင်းလင်းတဲ့ ဓာတ်ပုံ ပို့ပေးပါ။\n\n"
        "ကျေးဇူးပြု၍:\n"
        "- စာမျက်နှာ အပြည့်ပေါ်နေအောင်\n"
        "- စာလုံးတွေ ဖတ်လို့ရအောင် (မမှုန်ရ၊ အလင်းမပြန်ရ)\n"
        "- အရောင်ဓာတ်ပုံ (မိတ္တူကို ပြန်ရိုက်တာ မဟုတ်)\n"
        "- လက်ချောင်းတွေ ဖုံးမနေရ\n\n"
        "ကျေးဇူးတင်ပါတယ်။",
    ),
    Snippet(
        "Documents received",
        "မင်္ဂလာပါ။\n\nစာရွက်စာတမ်းများ လက်ခံရရှိပါပြီ။ ကျေးဇူးတင်ပါတယ်။\nဖိုင်ကို စစ်ဆေးနေပါသည်။ မကြာမီ အကြောင်းပြန်ပေးပါမည်။",
    ),
    Snippet(
        "Waiting for signature",
        "မင်္ဂလာပါ။\n\n"
        "လက်မှတ်ထိုးရန် စာရွက်များ အဆင်သင့်ရှိပါပြီ။\n"
        "မှတ်သားထားသော နေရာတွင် လက်မှတ်ထိုးပြီး ယနေ့ စကင်ဖတ် ပို့ပေးနိုင်ရင် ကျေးဇူးပါ။\n"
        "မူရင်းစာရွက်များကို နောက်မှ ကူရီယာနဲ့ ပို့နိုင်ပါတယ်။",
    ),
    Snippet(
        "Passport page missing",
        "မင်္ဂလာပါ။\n\n"
        "ကျေးဇူးပြု၍ အောက်ပါ အရောင်ဓာတ်ပုံများ ပို့ပေးပါ:\n"
        "၁။ နိုင်ငံကူးလက်မှတ် ဓာတ်ပုံစာမျက်နှာ (အမည်နှင့် နံပါတ်)\n"
        "၂။ နောက်ဆုံး ဗီဇာ စာမျက်နှာ\n"
        "၃။ နောက်ဆုံး ဝင်ရောက်တံဆိပ် (entry stamp)\n\n"
        "ယခင်ပို့ထားသော ဖိုင် မပြည့်စုံသေးပါ။",
    ),
    Snippet(
        "Name spelling check",
        "မင်္ဂလာပါ။\n\n"
        "တရားဝင်ဖောင်များအတွက် သင့်အမည် စာလုံးပေါင်းကို အတည်ပြုပေးပါ။\n"
        "မြန်မာ နိုင်ငံကူးလက်မှတ်နှင့် အတိအကျ တူရပါမည် (အလယ်အမည်များ အပါအဝင်)။",
    ),
    Snippet(
        "Processing at Immigration",
        "မင်္ဂလာပါ။\n\nလူဝင်မှုကြီးကြပ်ရေးသို့ ဖိုင်တင်ပြီးပါပြီ။\nရလဒ်ထွက်လျှင် သို့မဟုတ် စာရွက် ထပ်တောင်းလျှင် ချက်ချင်း အကြောင်းကြားပါမည်။",
    ),
    Snippet(
        "Ready for pickup / courier",
        "မင်္ဂလာပါ။\n\n"
        "သင့်စာရွက်စာတမ်းများ အဆင်သင့်ရှိပါပြီ။ ကျေးဇူးပြု၍ ပြောပြပါ:\n"
        "- ရုံးမှ လာယူမလား၊ Grab / Lalamove နဲ့ ပို့ပေးရမလား။\n"
        "- ပို့ရမည့် လိပ်စာနှင့် ဖုန်းနံပါတ်\n\n"
        "ကျေးဇူးတင်ပါတယ်။",
    ),
    Snippet(
        "Invoice attached",
        "မင်္ဂလာပါ။\n\nငွေတောင်းခံလွှာ ပူးတွဲပို့လိုက်ပါသည်။\nငွေလွှဲပြီး စလစ် ပို့ပေးပါ။ ပြေစာ ထုတ်ပေးပါမည်။\n\nကျေးဇူးတင်ပါတယ်။",
    ),
    Snippet(
        "Payment received",
        "မင်္ဂလာပါ။\n\nငွေလက်ခံရရှိပါပြီ။ ကျေးဇူးတင်ပါတယ်။\nနောက်တစ်ဆင့် ဆက်လုပ်ပြီး အကြောင်းပြန်ပါမည်။",
    ),
    Snippet(
        "Expiry reminder",
        "မင်္ဂလာပါ။\n\nသတိပေးချက်: ဖိုင်ထဲရှိ နိုင်ငံကူးလက်မှတ်၊ ဗီဇာ သို့မဟုတ် အလုပ်ပါမစ် သက်တမ်းကုန်ခါနီးပါပြီ။\nသက်တမ်းတိုး ပေးစေချင်ရင် ပြောပေးပါ။",
    ),
    Snippet(
        "Need original document",
        "မင်္ဂလာပါ။\n\n"
        "ဓာတ်ပုံ/စကင် နဲ့ စတင်လုပ်လို့ ရပါတယ်။\n"
        "လူဝင်မှုကြီးကြပ်ရေး သို့မဟုတ် အစိုးရရုံးက မူရင်းစာရွက် လိုအပ်ပါမည်။\n"
        "မူရင်းကို ကူရီယာနဲ့ ပို့ပြီး tracking number မျှဝေပေးပါ။",
    ),
    Snippet(
        "Follow up",
        "မင်္ဂလာပါ။\n\nယခင်စာ ရရှိပါသလား။ အချိန်ရရင် ပြန်ကြားပေးပါ။\nမရှင်းလင်းတာ ရှိရင် ထပ်ရှင်းပြပေးပါမည်။ ကျေးဇူးတင်ပါတယ်။",
    ),
    Snippet(
        "Missing docs — initial request",
        "Subject: Action Required: Missing Documentation for [Month/Year] Accounting - [Client Company Name]\n\n"
        "Dear [Client Contact Name],\n\n"
        "We are currently preparing the monthly financial reports and tax filings for "
        "[Client Company Name]. To ensure all records are accurate and compliant, we "
        "kindly request your assistance in providing the following missing documents:\n\n"
        "- [Date]: Tax Invoice for transaction of [Amount] to [Vendor Name].\n"
        "- [Date]: Explanation and supporting receipt for bank outflow of [Amount].\n\n"
        "Please upload these documents to your designated cloud folder or reply directly "
        "to this email by [Deadline Date].\n\n"
        "Thank you for your prompt assistance.\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Missing docs — first follow-up",
        "Subject: RE: Action Required: Missing Documentation for [Month/Year] Accounting - [Client Company Name]\n\n"
        "Dear [Client Contact Name],\n\n"
        "I am following up on the email below regarding the missing documentation for "
        "[Month/Year]. As our tax filing deadline is approaching on the 15th, please "
        "provide the requested files by [New Deadline, e.g. Tomorrow at 12:00 PM] so we "
        "can process your returns without incurring any late penalties.\n\n"
        "Thank you,\n[Your Name]",
    ),
    Snippet(
        "Filing delayed — client liability",
        "Subject: Filing of [Form] — [Month/Year]\n\n"
        "Dear [Client Contact Name],\n\n"
        "As the required supporting document ([Document]) was not provided by the filing "
        "deadline, we will proceed without claiming the related deduction/credit for the "
        "period. Please be aware that you assume responsibility for any resulting late "
        "fees or lost tax benefits.\n\n"
        "We remain at your disposal for any questions.\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Documents received — confirmed",
        "Subject: RE: [Missing documents] — Received\n\n"
        "Dear [Client Contact Name],\n\n"
        "Thank you. We confirm receipt of the requested documents for [Month/Year]. The "
        "matter is now closed.\n\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Invoice payment reminder",
        "Subject: Invoice [Invoice Number] — Payment Reminder\n\n"
        "Dear [Client Contact Name],\n\n"
        "We are writing to kindly check if the attached invoice has been scheduled for "
        "payment. The amount of [Amount] was due on [Due Date].\n\n"
        "If payment has already been made, please disregard this message. Otherwise, we "
        "would appreciate confirmation of the expected transfer date.\n\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Welcome to accounting",
        "Subject: Welcome to Sky Biz Hub Accounting — [Client Company Name]\n\n"
        "Dear [Client Contact Name],\n\n"
        "Welcome! We are pleased to manage the accounting and tax compliance for "
        "[Client Company Name]. Please note our operational deadlines:\n\n"
        "- All sales and purchase invoices must be uploaded by the 5th of each month.\n"
        "- This ensures timely tax filing by the 15th.\n\n"
        "Use your designated upload folder: [Folder link]. Please upload documents as "
        "PDFs with clear file names. We will send the first monthly financial package "
        "after your first close and will schedule a short review call.\n\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Audit — weekly status update",
        "Subject: Audit Update — [Client Company Name] — Week of [Date]\n\n"
        "Dear [Client Contact Name],\n\n"
        "A quick update on the independent audit for [Fiscal Year]:\n"
        "- Status: [In progress / Finalizing]\n"
        "- Pending queries: [Count / None]\n"
        "- Expected completion: [Date]\n\n"
        "We will keep you informed of any action items.\n\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
    Snippet(
        "Audit — query acknowledgment",
        "Subject: RE: Auditor Query #[Number]\n\n"
        "Dear [Auditor Contact],\n\n"
        "Thank you for your query. We acknowledge receipt and will respond within 48 "
        "hours with the requested documentation.\n\n"
        "Best regards,\n[Your Name]\nAccount Admin, Sky Biz Hub Co., Ltd.",
    ),
)

SUPPLIER_REPLIES: tuple[Snippet, ...] = (
    Snippet(
        "Please send tax invoice",
        "Hello krub 🙏\n\n"
        "Please send tax invoice krub.\n\n"
        "Need:\n"
        "- Invoice no. + date\n"
        "- Company name, tax ID, address\n"
        "- Description\n"
        "- Amount (ex-VAT, VAT, total)\n\n"
        "Thank you krub 🙏",
    ),
    Snippet(
        "Confirm PO / price",
        "Hello krub 🙏\n\n"
        "Please confirm this PO na krub:\n"
        "- Item / service\n"
        "- Qty\n"
        "- Price / total\n"
        "- Delivery date\n\n"
        "We proceed after you confirm krub 🙏",
    ),
    Snippet(
        "Delivery date please",
        "Hello krub 🙏\n\n"
        "Please confirm delivery date and courier/driver na krub.\n"
        "When out for delivery, send tracking number too krub 🙏\n\n"
        "Thank you krub 🙏",
    ),
    Snippet(
        "Need English on documents",
        "Hello krub 🙏\n\n"
        "Please put English on quotation / invoice / receipt na krub.\n"
        "Our client file is in English krub 🙏\n\n"
        "Thank you krub 🙏",
    ),
    Snippet(
        "Payment will be made",
        "Hello krub 🙏\n\n"
        "Thank you krub. We will transfer payment as agreed.\n"
        "Please send bank account (account name, bank, account no.) if not yet na krub 🙏\n\n"
        "Thank you krub 🙏",
    ),
    Snippet(
        "Documents received — thanks",
        "Hello krub 🙏\n\n"
        "Got the documents already krub. Thank you 🙏\n"
        "We will check and message if anything missing na krub.\n\n"
        "Thank you krub 🙏",
    ),
)

REPLIES: tuple[Snippet, ...] = CLIENT_REPLIES

CHECKLISTS: tuple[Snippet, ...] = (
    Snippet(
        "Visa Renewal (Burmese client)",
        "Visa renewal for Myanmar client — documents usually needed:\n"
        "1. Myanmar passport (photo page + latest visa + entry stamps)\n"
        "2. Current visa / permit and expiry date\n"
        "3. Company letter / employment letter (signed, company stamp)\n"
        "4. Latest work permit (if any)\n"
        "5. TM.30 / TM.47 as applicable\n"
        "6. Photos as required by the office\n"
        "7. Proof of address in Thailand\n"
        "8. Company affidavit / DBD papers if requested\n"
        "9. Payment / fee confirmation\n\n"
        "Send the client the Burmese reply. Ask for colour scans first; originals later.",
    ),
    Snippet(
        "Company Setup",
        "New company setup — typical pack:\n"
        "1. Proposed company name (English; Thai name we arrange with the supplier)\n"
        "2. Business activities\n"
        "3. Registered address in Thailand\n"
        "4. Myanmar passport copies of directors / shareholders (Thai ID if any Thai partner)\n"
        "5. Shareholding and capital\n"
        "6. Director consent and who can sign\n"
        "7. Memorandum / articles (we draft)\n"
        "8. VAT / social security after incorporation if needed\n\n"
        "Confirm passport spelling in Burmese/English before any government form is typed.",
    ),
    Snippet(
        "Work Permit Pack",
        "Work permit for Myanmar national — typical documents:\n"
        "1. Passport + current visa\n"
        "2. Education certificates / CV (English translation if the original is Burmese)\n"
        "3. Company affidavit, DBD printout, VAT certificate\n"
        "4. Employment contract / job description\n"
        "5. Office map and photos\n"
        "6. WP forms (we prepare)\n"
        "7. Medical certificate if requested\n"
        "8. Company letter on letterhead with stamp\n\n"
        "Confirm job title and start date as they should appear on the permit.",
    ),
    Snippet(
        "Monthly Accounting Close",
        "Month-end accounting pack:\n"
        "1. Bank statements (all accounts)\n"
        "2. Sales invoices issued\n"
        "3. Supplier invoices / tax invoices from Thai vendors (chase in English + krub)\n"
        "4. Payroll summary and social security\n"
        "5. Expense claims / petty cash\n"
        "6. VAT support\n"
        "7. New contracts, loans, or asset purchases\n\n"
        "Follow up Thai suppliers before cutoff if tax invoice is missing.",
    ),
    Snippet(
        "Foreign / BOI notes",
        "Myanmar / foreign shareholder notes:\n"
        "1. Parent or personal documents (passport, incorporation papers)\n"
        "2. Translations (Burmese originals → English)\n"
        "3. Legalisation plan if papers are issued in Myanmar\n"
        "4. Power of attorney if signing in Thailand\n"
        "5. Thai / foreign share split and capital\n"
        "6. Lease or title for the registered office\n\n"
        "Flag any documents still in Myanmar so we can plan embassy / MFA timing.",
    ),
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

SERVICE_REPLIES: tuple[Snippet, ...] = (
    Snippet(
        "VAT Address Update — Docs",
        "Could you please provide the following documents for the VAT address update:\n\n"
        "1. Company Affidavit (issued within the last 6 months)\n"
        "2. List of Shareholders — Bor Or Jor. 5 (issued within the last 6 months)\n"
        "3. Company stamp\n"
        "4. Lease agreement with required stamp duty affixed, plus:\n"
        "   • Landlord's ID card\n"
        "   • Land title deed\n"
        "   • House registration (landlord as owner)\n"
        "5. Photos of the new business location:\n"
        "   • Exterior — house number and acrylic company signboard\n"
        "   • Interior of premises and surrounding areas\n"
        "6. Graphic map of the new business address\n\n"
        "[notes]",
    ),
    Snippet(
        "Work Permit Renewal — Docs",
        "Required documents for Non-B work permit renewal:\n\n"
        "1. Copy of passport\n"
        "2. Copy of current work permit\n"
        "3. Passport-size photo — white background, PNG format\n"
        "4. Company Affidavit (within 6 months) + receipt\n"
        "5. List of Shareholders — Bor Or Jor 5 + receipt\n"
        "6. Medical Certificate (700 THB via agent)\n"
        "7. Latest 3 months' PP.30 (VAT) filings\n"
        "8. PND.91 — Tax Return + Tax Payment Receipt\n"
        "9. 2025 Financial Statements + Sor Bor Chor 3\n"
        "10. PND.50 — Tax Return + Tax Payment Receipt\n\n"
        "[notes]",
    ),
    Snippet(
        "VAT Address Update — Acrylic Sign Reminder",
        "Your company signboard must be made of durable acrylic (not paper). "
        "Please replace it before taking photos for the VAT address update.\n\n"
        "Photos needed:\n"
        "• Exterior showing house number and acrylic signboard\n"
        "• Interior of the premises\n"
        "• Surrounding areas\n\n"
        "[notes]",
    ),
)

SNIPPET_SECTIONS: dict[str, tuple[Snippet, ...]] = {
    "client": CLIENT_REPLIES,
    "supplier": SUPPLIER_REPLIES,
    "checklist": CHECKLISTS,
    "service": SERVICE_REPLIES,
}


def apply_snippet_overrides(section: str, overrides: dict[str, dict[str, str]] | None) -> tuple[Snippet, ...]:
    """Merge saved overrides over the built-in defaults for one section.

    Overrides are keyed by the snippet's original label::
        {"Need clear photo": {"label": "Clear photo", "text": "..."}}

    Keys that do not match any built-in snippet are user-added messages; they
    are appended (sorted by label) at the end of the section.
    """
    defaults = SNIPPET_SECTIONS.get(section, ())
    if not overrides:
        return defaults
    default_labels = {snippet.label for snippet in defaults}
    merged = []
    for snippet in defaults:
        override = overrides.get(snippet.label)
        if override:
            merged.append(
                Snippet(
                    label=(override.get("label") or snippet.label).strip() or snippet.label,
                    text=(override.get("text") or snippet.text).strip() or snippet.text,
                )
            )
        else:
            merged.append(snippet)
    extras = []
    for key, value in overrides.items():
        if key in default_labels:
            continue
        label = (value.get("label") or key).strip() or key
        text = (value.get("text") or "").strip()
        if text:
            extras.append(Snippet(label=label, text=text))
    extras.sort(key=lambda snippet: snippet.label.lower())
    return tuple([*merged, *extras])


def effective_text(section: str, label: str, overrides: dict[str, dict[str, dict[str, str]]] | None = None) -> str:
    """Return the effective (override-aware) text for one snippet, or ''."""
    items = apply_snippet_overrides(section, (overrides or {}).get(section) or {})
    for snippet in items:
        if snippet.label == label:
            return snippet.text
    return ""


def load_snippet_overrides(get_setting) -> dict:
    """Safely read + parse the snippet-overrides setting.

    `get_setting` is a callable (e.g. ``db.get_setting``). Corrupt or
    non-dict JSON never raises — it degrades to no overrides.
    """
    raw = ""
    try:
        raw = get_setting(SETTING_SNIPPET_OVERRIDES) or ""
        parsed = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


SNIPPET_PACK_FORMAT = "skyadmin-snippets"
SNIPPET_PACK_VERSION = 1


def pack_snippet_pack(active: dict, history: list[dict]) -> dict:
    """Bundle active messages + version history into a portable JSON dict."""
    return {
        "format": SNIPPET_PACK_FORMAT,
        "version": SNIPPET_PACK_VERSION,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active": active,
        "history": [
            {
                "created_at": item.get("created_at") or "",
                "note": item.get("note") or "",
                "snapshot": item.get("snapshot") or {},
            }
            for item in history
        ],
    }


def _clean_section(value) -> dict[str, dict[str, str]]:
    """Coerce one section of overrides to {label: {label, text}}, dropping junk."""
    if not isinstance(value, dict):
        return {}
    clean: dict[str, dict[str, str]] = {}
    for key, entry in value.items():
        if not isinstance(entry, dict):
            continue
        clean[str(key)] = {
            "label": str(entry.get("label") or ""),
            "text": str(entry.get("text") or ""),
        }
    return clean


def unpack_snippet_pack(data: dict) -> dict:
    """Validate an exported pack and return {'active', 'history'}."""
    if not isinstance(data, dict):
        raise ValueError("Not a messages pack.")
    if data.get("format") != SNIPPET_PACK_FORMAT:
        raise ValueError("Not a SkyAdmin messages file.")
    version = data.get("version")
    if version != SNIPPET_PACK_VERSION:
        raise ValueError(f"Unsupported messages file version: {version}.")
    active = data.get("active") or {}
    history = data.get("history") or []
    if not isinstance(active, dict) or not isinstance(history, list):
        raise ValueError("Messages file is corrupt.")
    clean_active = {section: _clean_section(section_value) for section, section_value in active.items()}
    clean_history = []
    for item in history:
        if not isinstance(item, dict):
            continue
        snapshot = item.get("snapshot")
        if not isinstance(snapshot, dict):
            continue
        clean_snapshot = {section: _clean_section(section_value) for section, section_value in snapshot.items()}
        clean_history.append(
            {
                "created_at": item.get("created_at") or "",
                "note": item.get("note") or "",
                "snapshot": clean_snapshot,
            }
        )
    return {"active": clean_active, "history": clean_history}
