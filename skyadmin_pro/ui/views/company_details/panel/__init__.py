import customtkinter as ctk

from skyadmin_pro.services.file_ops import copy_file
from skyadmin_pro.services.snippets import effective_text, load_snippet_overrides
from skyadmin_pro.services.workflow import copy_to_clipboard, create_client_workspace
from skyadmin_pro.ui.views.company_details.constants import (
    SUBTAB_FILING,
    SUBTAB_FINANCIAL_DOCS,
    SUBTAB_GENERAL,
    SUBTAB_NAMES,
    SUBTAB_TAX_IDS,
    SUBTAB_VO_CSH,
)
from skyadmin_pro.ui.views.company_details.filing_tab import FilingTabMixin
from skyadmin_pro.ui.views.company_details.financial_docs_tab import FinancialDocsTabMixin
from skyadmin_pro.ui.views.company_details.general_tab import GeneralTabMixin
from skyadmin_pro.ui.views.company_details.tax_ids_tab import TaxIdsTabMixin
from skyadmin_pro.ui.views.company_details.vo_csh_tab import VoCshTabMixin

from .chunk_0 import CompanyDetailsPanelMixin0
from .chunk_1 import CompanyDetailsPanelMixin1
from .chunk_2 import CompanyDetailsPanelMixin2
from .chunk_3 import CompanyDetailsPanelMixin3
from .chunk_4 import CompanyDetailsPanelMixin4
from .chunk_5 import CompanyDetailsPanelMixin5
from .chunk_6 import CompanyDetailsPanelMixin6
from .chunk_7 import CompanyDetailsPanelMixin7
from .chunk_8 import CompanyDetailsPanelMixin8
from .chunk_9 import CompanyDetailsPanelMixin9
from .chunk_10 import CompanyDetailsPanelMixin10
from .chunk_11 import CompanyDetailsPanelMixin11
from .chunk_12 import CompanyDetailsPanelMixin12
from .chunk_13 import CompanyDetailsPanelMixin13
from .chunk_14a import CompanyDetailsPanelMixin14A
from .chunk_14b import CompanyDetailsPanelMixin14B
from .chunk_15 import CompanyDetailsPanelMixin15
from .chunk_16 import CompanyDetailsPanelMixin16
from .chunk_17 import CompanyDetailsPanelMixin17
from .chunk_18 import CompanyDetailsPanelMixin18


class CompanyDetailsPanel(
    CompanyDetailsPanelMixin0,
    CompanyDetailsPanelMixin1,
    CompanyDetailsPanelMixin2,
    CompanyDetailsPanelMixin3,
    CompanyDetailsPanelMixin4,
    CompanyDetailsPanelMixin5,
    CompanyDetailsPanelMixin6,
    CompanyDetailsPanelMixin7,
    CompanyDetailsPanelMixin8,
    CompanyDetailsPanelMixin9,
    CompanyDetailsPanelMixin10,
    CompanyDetailsPanelMixin11,
    CompanyDetailsPanelMixin12,
    CompanyDetailsPanelMixin13,
    CompanyDetailsPanelMixin14A,
    CompanyDetailsPanelMixin14B,
    CompanyDetailsPanelMixin15,
    CompanyDetailsPanelMixin16,
    CompanyDetailsPanelMixin17,
    CompanyDetailsPanelMixin18,
    GeneralTabMixin,
    TaxIdsTabMixin,
    FilingTabMixin,
    VoCshTabMixin,
    FinancialDocsTabMixin,
    ctk.CTkFrame,
):
    pass
