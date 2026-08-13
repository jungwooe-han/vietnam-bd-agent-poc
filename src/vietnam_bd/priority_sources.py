from __future__ import annotations


# Experimental Firecrawl A/B configuration. It is intentionally separate from
# the production OpenAI web-search path.
PRIORITY_SOURCES: tuple[str, ...] = (
    "vir.com.vn",
    "fia.mpi.gov.vn",
    "e.vnexpress.net",
    "baodautu.vn",
    "vietnam-briefing.com",
    "vietnamnews.vn",
    "hanoitimes.vn",
    "vsip.com",
)
