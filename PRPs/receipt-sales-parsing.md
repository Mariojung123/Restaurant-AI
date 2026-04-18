# PRP: Receipt Sales Parsing

## 목적
마감 영수증 사진 → Vision 파싱 → SalesLog 저장 + Ingredient.current_stock 차감 (2-step preview/confirm 패턴)

## 컨텍스트
- **패턴 참고**: `backend/routers/vision.py` (invoice preview/confirm), `backend/services/invoice.py` (fuzzy_match_ingredient)
- **DB 모델**: `backend/models/database.py` — SalesLog, Recipe, RecipeIngredient, Ingredient (변경 없음)
- **테스트 참고**: `backend/tests/test_vision_invoice.py` (unique suffix 패턴, SAVEPOINT 격리)
- **프론트 참고**: `frontend/src/pages/Invoice.jsx` (3단계 UI 구조)

## 구현 순서

1. `backend/services/receipt.py` 신규 생성
   - `fuzzy_match_recipe(db, name)` — SequenceMatcher, threshold 0.7, Recipe 대상
   - `process_receipt_items(items, sale_date, db)` — SalesLog + 재고 차감, (results, skipped_count) 반환

2. `backend/routers/vision.py` 엔드포인트 추가
   - `RECEIPT_EXTRACTION_PROMPT` 상수 추가
   - `_parse_receipt_json()` 파서 함수
   - `POST /receipt/preview` — Vision 파싱 + 퍼지 매칭, DB 쓰기 없음
   - `POST /receipt/confirm` — SalesLog 저장 + 재고 차감 + db.commit()

3. `backend/tests/test_vision_receipt.py` 신규 생성
   - preview 엔드포인트 테스트 (퍼지 매칭, DB 쓰기 없음, 중복 경고)
   - confirm 엔드포인트 테스트 (SalesLog 생성, 재고 차감, skip 처리)
   - 서비스 유닛 테스트 (fuzzy_match_recipe, process_receipt_items)

4. `frontend/src/pages/Receipt.jsx` 신규 생성
   - Invoice.jsx 동일 3단계 패턴
   - Step 2: match_score 기반 배지 + 드롭다운
   - "Record Sales" 버튼 → confirm

5. `frontend/src/App.jsx` — `/receipt` 라우트 추가

6. `frontend/src/components/Navbar.jsx` — "Receipt" 링크 추가

## API 엔드포인트

- `POST /api/vision/receipt/preview` — multipart/form-data, file 필드
- `POST /api/vision/receipt/confirm` — JSON body

## DB 스키마 변경
없음. 기존 SalesLog, Recipe, RecipeIngredient, Ingredient 재사용.

## Claude API 활용 방식
- `parse_image_with_claude()` 재사용 (`backend/services/claude.py`)
- `RECEIPT_EXTRACTION_PROMPT` + `max_tokens=2048`
- 반환: `{"sale_date": "...", "items": [{"name": ..., "quantity": int, "unit_price": ..., "total_price": ...}]}`

## 핵심 로직 엣지케이스
- `recipe_id` null + `include: true` → skipped_count 증가, 스킵 (에러 아님)
- `RecipeIngredient.quantity` null → 차감 스킵, ingredients_deducted 미포함
- `current_stock < 0` 허용 (예약 판매 등)
- `sale_date` null → `datetime.utcnow()` 사용
- 중복 체크: 동일 sale_date SalesLog 존재 시 `duplicate_warning: true`

## 검증 게이트
- [ ] `pytest backend/tests/test_vision_receipt.py -v` — 전체 PASS
- [ ] preview: DB 쓰기 없음 확인
- [ ] confirm: SalesLog 생성 + current_stock 차감 확인
- [ ] match_score >= 0.7 → suggested_match 반환
- [ ] match_score < 0.7 → suggested_match null
- [ ] include:false 항목 스킵 확인
- [ ] recipe_id null + include:true → items_skipped 카운트
- [ ] RecipeIngredient.quantity null → 차감 스킵
- [ ] 중복 날짜 → duplicate_warning: true
- [ ] 프론트: `/receipt` 라우트 접근
- [ ] 프론트: Step 1→2→3 플로우

## 구현 가능성 점수: 9/10
기존 invoice 패턴과 90% 동일. Recipe 매칭 + RecipeIngredient 조회 로직만 신규.
