from mr_impact.index.adapters.generic import GenericAdapter
from mr_impact.index.adapters.jil import JilAdapter
from mr_impact.index.adapters.readers_bridge import ReadersBridgeAdapter
from mr_impact.index.adapters.sql import SqlAdapter

DEFAULT_ADAPTERS = [
    JilAdapter(),
    SqlAdapter(),
    ReadersBridgeAdapter(),
    GenericAdapter(),
]

__all__ = ["DEFAULT_ADAPTERS", "GenericAdapter", "JilAdapter", "ReadersBridgeAdapter", "SqlAdapter"]
