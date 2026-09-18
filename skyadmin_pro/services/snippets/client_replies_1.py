from .types import Snippet

CLIENT_REPLIES_1: tuple[Snippet, ...] = (
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
)
