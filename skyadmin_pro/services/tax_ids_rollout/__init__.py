"""Wave C — discover accounting clients and infer Tax IDs contract fields."""

from __future__ import annotations

from .funcs import (
    apply_pricing_tier,
    enrich_setup_row,
    infer_service_type_from_documents,
    infer_service_types,
    list_accounting_setup_rows,
    parse_document_types,
    setup_missing_fields,
    setup_status_label,
)
