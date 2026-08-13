from __future__ import annotations

import re
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .telemetry import record_external_api_call

URL_RE = re.compile(r"https?://[^\s]+")


def find_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def extract_url_text(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BD-Agent-POC/1.0)"}
    record_external_api_call()
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "nav", "footer", "header", "aside"]):
        node.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return text[:20000]


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for page in reader.pages[:30]:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)[:40000]


def build_extracted_context(seed: str, uploaded_file) -> tuple[str, list[str]]:
    chunks: list[str] = []
    notes: list[str] = []

    urls = find_urls(seed)
    for url in urls[:3]:
        try:
            chunks.append(f"[URL: {url}]\n{extract_url_text(url)}")
            notes.append(f"URL 본문 추출 완료: {url}")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"URL 본문 추출 실패(검색 분석은 계속 진행): {url} / {exc}")

    if uploaded_file is not None:
        name = uploaded_file.name.lower()
        try:
            if name.endswith(".pdf"):
                chunks.append(f"[PDF: {uploaded_file.name}]\n{extract_pdf_text(uploaded_file.getvalue())}")
                notes.append(f"PDF 추출 완료: {uploaded_file.name}")
            elif name.endswith((".txt", ".md")):
                chunks.append(uploaded_file.getvalue().decode("utf-8", errors="replace")[:40000])
                notes.append(f"텍스트 파일 추출 완료: {uploaded_file.name}")
            else:
                notes.append("현재 POC는 PDF/TXT/MD 파일을 지원합니다.")
        except Exception as exc:  # noqa: BLE001
            notes.append(f"파일 추출 실패: {exc}")

    return "\n\n".join(chunks), notes
