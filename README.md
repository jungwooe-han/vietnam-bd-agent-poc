# Vietnam Manufacturing BD Agent POC

RFP/PRD v1.0을 기반으로 만든 모바일 대응 Streamlit POC입니다.

## 현재 구현

- 자유 텍스트 / 뉴스 URL / PDF·TXT 입력
- 입력 맥락에 따른 추가 질문
- URL/PDF 본문 추출
- OpenAI Responses API 기반 분석
- 선택적 웹 검색 도구
- Opportunity Qualification
- Samsung DX Perspective
- Meeting Intelligence: 대상, 이유, 핵심 질문 3–5개, 판단 포인트
- Internal Intelligence 빈 상태 및 더미 케이스 연동 구조
- Next Step Navigator
- 모바일 카드/탭 UI
- API 키가 없어도 확인 가능한 데모 모드

## 1분 실행 (Windows)

1. 압축을 완전히 해제합니다. ZIP 안에서 직접 실행하지 않습니다.
2. `run_windows.bat`를 더블클릭합니다.
3. 설치가 끝나면 브라우저에서 `http://localhost:8501`을 엽니다.
4. 첫 실행은 사이드바의 데모 모드를 켠 상태로 테스트합니다.

Python 3.11~3.13을 우선 사용하며, 실행 파일이 설치 오류에서 자동으로 멈추도록 구성했습니다.

직접 실행:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

`.env`에 OpenAI API 키를 넣으면 실제 분석을 실행합니다.

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
ENABLE_WEB_SEARCH=true
```

## 모바일에서 열기

### 같은 Wi-Fi에서 로컬 테스트

```powershell
streamlit run app.py --server.address 0.0.0.0
```

PC의 IPv4 주소를 확인한 뒤 휴대폰에서 `http://PC주소:8501`로 접속합니다. Windows 방화벽 허용이 필요할 수 있습니다.

### 인터넷 배포

GitHub에 올린 뒤 Streamlit Community Cloud에서 `app.py`를 배포하고, Secrets에 API 키를 등록합니다. 실제 회사 데이터는 승인된 사내 환경으로 이전하기 전까지 사용하지 마세요.

## 내부 더미데이터 추가

`data/dummy_opportunities.json`에 RFP Appendix D 형태의 케이스를 배열로 추가합니다. 현재 파일은 빈 배열이며 없어도 앱이 정상 작동합니다.

## 보안

- 실제 회사 기밀정보 금지
- `.env`와 `.streamlit/secrets.toml`은 Git에 올리지 않음
- Community Cloud에는 더미·가명 데이터만 사용


## Connection error / status 500 해결

- 기존에 열린 검은 창과 브라우저 탭을 모두 닫습니다.
- ZIP을 폴더에 완전히 압축 해제했는지 확인합니다.
- 프로젝트 폴더의 `.venv`를 삭제한 뒤 `run_windows.bat`를 다시 실행합니다.
- 계속 실패하면 `diagnose_windows.bat`를 실행하고 표시되는 오류를 확인합니다.
- 같은 Wi-Fi의 휴대폰에서 열려면 PC에서 먼저 정상 실행한 후 `run_windows_network.bat`를 사용합니다.
