from .types import Snippet

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
