# FEATURE

채팅 컨텍스트 — chat_history 테이블 활용한 multi-turn 대화.
운영 데이터(재고/판매/레시피)를 조회해서 Claude가 사장 질문에 답변.

## 원하는 동작
- 사장이 "이번 주 뭐가 잘 팔렸어?" → Claude가 sales_logs 조회 후 답변
- "닭가슴살 언제 떨어져?" → ingredients + prediction 조회 후 답변
- 대화가 이어지면 이전 메시지 컨텍스트 유지 (multi-turn)
- session_id로 대화 세션 구분
- 답변은 입력 언어와 동일하게 (한국어 질문 → 한국어 답변)

## 사용자 시나리오
1. 사장이 채팅창에 질문 입력 (session_id 포함)
2. 백엔드가 chat_history에서 해당 session의 최근 대화 불러옴
3. 질문 내용 분석 → 관련 DB 데이터 조회 (재고/판매/레시피)
4. 조회한 데이터 + 대화 이력을 Claude에 전달
5. Claude 답변 생성
6. 질문 + 답변을 chat_history에 저장
7. 답변을 프론트에 반환

# EXAMPLES

examples/ 폴더 참고

# DOCUMENTATION

- Claude API: https://docs.anthropic.com/en/api/getting-started
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- FastAPI: https://fastapi.tiangolo.com/

# OTHER CONSIDERATIONS

- session_id: 프론트에서 UUID 생성해서 요청마다 전달
- 최근 20개 메시지만 컨텍스트에 포함 (토큰 절약)
- DB 조회는 질문 내용에 따라 선택적으로 (재고 질문 → inventory, 판매 질문 → sales_logs)
- 데이터 없을 때도 Claude가 자연스럽게 안내
- 기존 chat_with_claude() 함수 재사용 (backend/services/claude.py)
- 기존 ChatHistory 모델 재사용 (backend/models/database.py)
