"""Quick replies and checklists.

Clients receive Burmese. Thai suppliers get simple English plus krub / 🙏
(no Thai script).
"""

from __future__ import annotations

from typing import NamedTuple


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
        "မင်္ဂလာပါ။\n\n"
        "စာရွက်စာတမ်းများ လက်ခံရရှိပါပြီ။ ကျေးဇူးတင်ပါတယ်။\n"
        "ဖိုင်ကို စစ်ဆေးနေပါသည်။ မကြာမီ အကြောင်းပြန်ပေးပါမည်။",
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
        "မင်္ဂလာပါ။\n\n"
        "လူဝင်မှုကြီးကြပ်ရေးသို့ ဖိုင်တင်ပြီးပါပြီ။\n"
        "ရလဒ်ထွက်လျှင် သို့မဟုတ် စာရွက် ထပ်တောင်းလျှင် ချက်ချင်း အကြောင်းကြားပါမည်။",
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
        "မင်္ဂလာပါ။\n\n"
        "ငွေတောင်းခံလွှာ ပူးတွဲပို့လိုက်ပါသည်။\n"
        "ငွေလွှဲပြီး စလစ် ပို့ပေးပါ။ ပြေစာ ထုတ်ပေးပါမည်။\n\n"
        "ကျေးဇူးတင်ပါတယ်။",
    ),
    Snippet(
        "Payment received",
        "မင်္ဂလာပါ။\n\n"
        "ငွေလက်ခံရရှိပါပြီ။ ကျေးဇူးတင်ပါတယ်။\n"
        "နောက်တစ်ဆင့် ဆက်လုပ်ပြီး အကြောင်းပြန်ပါမည်။",
    ),
    Snippet(
        "Expiry reminder",
        "မင်္ဂလာပါ။\n\n"
        "သတိပေးချက်: ဖိုင်ထဲရှိ နိုင်ငံကူးလက်မှတ်၊ ဗီဇာ သို့မဟုတ် အလုပ်ပါမစ် သက်တမ်းကုန်ခါနီးပါပြီ။\n"
        "သက်တမ်းတိုး ပေးစေချင်ရင် ပြောပေးပါ။",
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
        "မင်္ဂလာပါ။\n\n"
        "ယခင်စာ ရရှိပါသလား။ အချိန်ရရင် ပြန်ကြားပေးပါ။\n"
        "မရှင်းလင်းတာ ရှိရင် ထပ်ရှင်းပြပေးပါမည်။ ကျေးဇူးတင်ပါတယ်။",
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
)
