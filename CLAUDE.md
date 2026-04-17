# 식당 운영 AI 파트너 — 프로젝트 컨텍스트

## 프로젝트 방향
캐나다 소규모 식당 사장을 위한 **자연어 기반 AI 운영 파트너** PWA 웹 서비스.
포트폴리오용. Claude API 활용.

## 핵심 컨셉
> "납품서랑 마감 영수증 사진만 찍으면 AI가 재고 소진 시점 예측해주는 앱"

사장이 채팅으로: "이번 주 뭐가 잘 팔렸어?", "닭가슴살 언제 떨어져?" → Claude가 데이터 해석 + 친근하게 답변 + 조언

## 확정 기능 (MVP)
1. **자연어 채팅 Q&A** — 운영 데이터 기반 Claude 답변
2. **레시피 등록** — 대화로 입력 + Claude가 재료/수량 추측 후 확인만
   - 자연어 단위 허용: "피망 반개", "마늘 한 스푼" 등
3. **납품서 사진 → Vision 파싱** — 재고 자동 업데이트
4. **마감 영수증 사진 → Vision 파싱** — 판매량 자동 반영
5. **재고 소진 예측 알림** — 대시보드에 표시
   - "닭가슴살 내일 저녁 다 써요" 형태

## 기술 스택
- **Frontend**: React + Vite + Tailwind CSS (PWA)
- **Backend**: FastAPI (Python)
- **DB**: PostgreSQL
- **AI**: Claude API
  - claude-sonnet-4-6 (채팅, 예측, 레시피 추측)
  - Vision (납품서/영수증 사진 파싱)
- **배포**: Vercel (Frontend) + Railway/Render (Backend)

## 프로젝트 구조
```
Project_04_16/
├── frontend/          → React PWA
│   └── src/
│       ├── pages/     → Chat, Dashboard, Recipe, Settings
│       └── components/
├── backend/           → FastAPI
│   ├── main.py        → 진입점 + 라우터 등록
│   ├── routers/       → chat.py, inventory.py, vision.py, recipe.py
│   ├── services/      → claude.py, prediction.py
│   ├── models/        → DB 모델
│   └── .env           → ANTHROPIC_API_KEY, DATABASE_URL
├── PRPs/              → 기능별 구현 계획
├── examples/          → 코드 패턴 참고
└── .claude/commands/  → generate-prp.md, execute-prp.md
```

## 코드 규칙
- Python: snake_case, 함수 단일 책임 원칙
- React: 함수형 컴포넌트 + hooks only
- JavaScript only (NO TypeScript)
- 변수명/주석/커밋 메시지: 영어
- 파일 500줄 이하
- load_dotenv() → main.py 최상단 호출

## AI 규칙
- 불명확하면 질문 먼저
- 파일 경로 확인 후 참조
- 명시적 지시 없이 기존 코드 삭제 금지
- Serena MCP로 심볼 단위 읽기 (파일 전체 읽기 최소화)

## 타겟
- 캐나다 소규모 독립 식당 (직원 50명 미만)
- 기술 친숙도 낮은 오너
- 이민자 운영 식당

## 경쟁사 공백
- MarketMan/WISK: 수동 카운트 필요, 자연어 없음
- Restoke: Vision 있지만 자연어 채팅 없음, 소규모 타겟 아님
- Square AI: 판매 Q&A만, 재고/발주 연동 없음
