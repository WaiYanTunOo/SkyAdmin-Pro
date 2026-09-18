from .types import Snippet

CLIENT_REPLIES_2: tuple[Snippet, ...] = (
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
