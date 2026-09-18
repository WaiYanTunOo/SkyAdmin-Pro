from .types import Snippet

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
