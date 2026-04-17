# PRP: 채팅 컨텍스트

## 목적
session_id 기반 multi-turn 대화 + 운영 DB 데이터를 Claude에 주입하여 사장 질문에 데이터 기반 답변 제공.

## 컨텍스트
- `backend/routers/chat.py` — 수정 대상 (session_id 추가, DB 주입 로직)
- `backend/services/claude.py` — `chat_with_claude()` 재사용
- `backend/services/prediction.py` — `forecast_all()` 재사용
- `backend/models/database.py` — `ChatHistory`, `SalesLog`, `Ingredient`, `Recipe`, `get_db()` 재사용
- 현재 `POST /api/chat/message`: messages 리스트만 받음, session 없음, DB 연결 없음

## 구현 순서

1. **`chat.py` — Request 모델 수정**
   - `ChatRequest`에 `session_id: str` 필드 추가
   - `get_db` dependency 주입 추가

2. **`chat.py` — 히스토리 로드 함수**
   - `_load_history(db, session_id, limit=20)` 작성
   - `ChatHistory` 테이블에서 `session_id` 기준 최근 `limit`개 조회
   - `[{"role": ..., "content": ...}]` 형태로 반환

3. **`chat.py` — DB 컨텍스트 빌더 함수**
   - `_build_context(db, user_message)` 작성
   - 키워드 감지로 필요한 데이터만 조회:
     - 재고/stock/inventory/ingredient 키워드 → `Ingredient` 전체 조회 + `forecast_all()`
     - 판매/sales/sell/sold/잘 팔 키워드 → 최근 7일 `SalesLog` + `Recipe` 조인 집계
     - 레시피/recipe/menu 키워드 → `Recipe` 전체 조회
   - 결과를 문자열 블록으로 직렬화해서 반환 (JSON 아닌 자연어 테이블 형태)
   - 해당 키워드 없으면 빈 문자열 반환

4. **`chat.py` — 시스템 프롬프트 조합**
   - `DEFAULT_SYSTEM_PROMPT` + DB 컨텍스트 블록 합성
   - 형태:
     ```
     {DEFAULT_SYSTEM_PROMPT}

     --- Current restaurant data ---
     {context_block}
     --- End of data ---

     Always respond in the same language the user writes in.
     ```

5. **`chat.py` — `send_message` 엔드포인트 수정**
   - 히스토리 로드 → 컨텍스트 빌드 → Claude 호출 순서로 실행
   - 메시지 순서: `loaded_history + [{"role":"user","content": 현재 질문}]`
   - Claude 답변 후 `ChatHistory`에 user + assistant 메시지 두 행 저장
   - `ChatResponse`에 `session_id` 함께 반환

6. **`chat.py` — GET /history 엔드포인트 추가 (선택)**
   - `GET /api/chat/history/{session_id}` → 해당 세션 전체 이력 반환
   - 프론트 새로고침 시 대화 복원용

## API 엔드포인트

- `POST /api/chat/message` → 수정 (session_id 추가, DB 컨텍스트 주입)
- `GET /api/chat/history/{session_id}` → 신규 (대화 이력 조회)

## DB 스키마 변경

없음. `chat_history` 테이블 이미 존재.

## Claude API 활용 방식

```python
# 시스템 프롬프트 = 기본 페르소나 + DB 데이터 스냅샷
system = DEFAULT_SYSTEM_PROMPT + "\n\n--- Current restaurant data ---\n" + context + "\n---"

# 메시지 = DB에서 불러온 이전 대화 + 현재 질문
messages = loaded_history + [{"role": "user", "content": user_message}]

reply = chat_with_claude(messages=messages, system_prompt=system)
```

- 모델: `claude-sonnet-4-6` (기존 `CLAUDE_MODEL` 상수 재사용)
- max_tokens: 1024 (기본값 유지)

## 검증 게이트

- [ ] `POST /api/chat/message` — session_id 없으면 422 반환
- [ ] 동일 session_id로 2회 요청 시 두 번째 응답에 이전 대화 컨텍스트 반영
- [ ] 재고 키워드 포함 질문 → system prompt에 ingredient 데이터 포함 여부 확인 (로그)
- [ ] 판매 키워드 포함 질문 → sales 데이터 포함 여부 확인
- [ ] DB 데이터 없을 때 → Claude가 "데이터 없음" 자연스럽게 안내
- [ ] `GET /api/chat/history/{session_id}` → 저장된 대화 순서대로 반환
- [ ] 한국어 질문 → 한국어 답변, 영어 질문 → 영어 답변

## 구현 가능성 점수: 9/10
기존 함수(`chat_with_claude`, `forecast_all`, `get_db`) 모두 재사용 가능. 키워드 기반 컨텍스트 선택이 단순하지만 MVP에 충분.
