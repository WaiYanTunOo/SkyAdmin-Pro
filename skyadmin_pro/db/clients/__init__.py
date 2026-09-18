"""Aggressively Split Module."""

from __future__ import annotations

from .batch_a import BatchMixinA
from .batch_b import BatchMixinB
from .crud_a import CrudMixinA
from .crud_b import CrudMixinB
from .crud_c import CrudMixinC
from .crud_d import CrudMixinD
from .doc_list import DocListMixin
from .documents_a import DocumentsMixinA
from .documents_b import DocumentsMixinB
from .documents_c import DocumentsMixinC
from .groups import GroupsMixin
from .incentives import IncentivesMixin
from .names_a import NamesMixinA
from .names_b import NamesMixinB


class ClientsMixin(
    BatchMixinA,
    BatchMixinB,
    CrudMixinA,
    CrudMixinB,
    CrudMixinC,
    CrudMixinD,
    DocumentsMixinA,
    DocumentsMixinB,
    DocumentsMixinC,
    DocListMixin,
    GroupsMixin,
    IncentivesMixin,
    NamesMixinA,
    NamesMixinB,
):
    pass
