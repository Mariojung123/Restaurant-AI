# Invoice Confirmation Flow — Feature Spec

## Overview

납품서 스캔 기능에 **preview → 유저 편집 → confirm** 플로우 추가.

**기존 문제:** `POST /vision/invoice`는 파싱 즉시 DB commit → 아래 5가지 문제 발생:
1. **중복 방지 없음** — 같은 납품서 2번 스캔 시 재고 2배
2. **OCR 오류 수정 불가** — "1.5 kg" → "15 kg" 저장되어도 수정 불가
3. **재료명 오인식** — "Mozz Cheese" → "mozzarella cheese"와 별도 재료로 생성
4. **단위 불일치** — "L" vs "liter" → 다른 재료로 분리
5. **항목 삭제 불가** — 전체 저장 강제

**해결:** 2개 엔드포인트로 분리. `/preview`는 파싱만(DB 쓰기 없음), `/confirm`은 유저 확인 후 저장.

---

## Backend

### `POST /vision/invoice/preview`

**목적:** Claude Vision으로 납품서 파싱. 퍼지 매칭 제안 포함. DB 쓰기 없음.

**Input:** `multipart/form-data` — `file` (image/jpeg, image/png, image/webp, image/gif)

**처리 순서:**
1. 파일 타입/비어있음 검증
2. `parse_image_with_claude()` 호출 (`INVOICE_EXTRACTION_PROMPT`, max_tokens=2048)
3. `_parse_invoice_json()`으로 파싱
4. 각 아이템 → `difflib.SequenceMatcher`로 기존 Ingredient 퍼지 매칭
   - score ≥ 0.7 → `suggested_match` + `match_score` 포함
   - score < 0.7 → `suggested_match: null`
5. 중복 체크: 같은 supplier + invoice_date의 InventoryLog 존재 시 `duplicate_warning: true`

**Output:**
```json
{
  "supplier": "Farm Fresh Co.",
  "invoice_date": "2024-05-10",
  "duplicate_warning": false,
  "items": [
    {
      "name": "chicken breast",
      "quantity": 10.0,
      "unit": "kg",
      "unit_price": 5.99,
      "suggested_match": { "id": 3, "name": "chicken breast", "unit": "kg" },
      "match_score": 1.0
    },
    {
      "name": "mozz cheese",
      "quantity": 3.0,
      "unit": "kg",
      "unit_price": null,
      "suggested_match": { "id": 7, "name": "mozzarella cheese", "unit": "kg" },
      "match_score": 0.74
    },
    {
      "name": "new herb mix",
      "quantity": 1.0,
      "unit": "bag",
      "unit_price": 4.50,
      "suggested_match": null,
      "match_score": 0.0
    }
  ]
}
```

**에러:**
- 400: 지원하지 않는 이미지 타입 or 빈 파일
- 422: Claude 비정상 JSON 반환
- 500: Claude API 오류

---

### `POST /vision/invoice/confirm`

**목적:** 유저가 검토/수정한 아이템 받아 DB 저장.

**Input:** JSON body
```json
{
  "supplier": "Farm Fresh Co.",
  "invoice_date": "2024-05-10",
  "items": [
    {
      "name": "chicken breast",
      "quantity": 10.0,
      "unit": "kg",
      "unit_price": 5.99,
      "ingredient_id": 3,
      "include": true
    },
    {
      "name": "mozz cheese",
      "quantity": 3.0,
      "unit": "kg",
      "unit_price": null,
      "ingredient_id": 7,
      "include": true
    },
    {
      "name": "new herb mix",
      "quantity": 1.0,
      "unit": "bag",
      "unit_price": 4.50,
      "ingredient_id": null,
      "include": true
    },
    {
      "name": "unwanted item",
      "quantity": 2.0,
      "unit": "ea",
      "unit_price": 1.00,
      "ingredient_id": null,
      "include": false
    }
  ]
}
```

**처리 규칙:**
- `include: false` 항목 스킵
- `ingredient_id` 있음 → ID로 기존 Ingredient 조회 (이름 검색 없음)
- `ingredient_id` null → 신규 Ingredient 생성
- 각 포함 항목 InventoryLog 생성, `current_stock` 증가
- 전체 처리 후 `db.commit()`

**Output:** 기존 `/vision/invoice`와 동일한 `InvoiceResponse` 스키마
```json
{
  "supplier": "Farm Fresh Co.",
  "invoice_date": "2024-05-10",
  "items_processed": 3,
  "items": [
    {
      "name": "chicken breast",
      "quantity": 10.0,
      "unit": "kg",
      "unit_price": 5.99,
      "action": "matched",
      "ingredient_id": 3,
      "inventory_log_id": 42
    }
  ]
}
```

---

## Service Layer (`backend/services/invoice.py`)

### 신규 함수: `fuzzy_match_ingredient(db, name)`
```python
def fuzzy_match_ingredient(db, name: str) -> tuple[Ingredient | None, float]:
    """difflib.SequenceMatcher로 최고 매칭 Ingredient 반환. threshold 0.7."""
```
- 전체 Ingredient 조회 후 각각 SequenceMatcher ratio 계산
- 최고 score ≥ 0.7이면 해당 Ingredient + score 반환
- 없으면 (None, 0.0) 반환

### 기존 함수 확장: `process_invoice_items`
- 각 아이템에 `ingredient_id: int | None` 필드 추가
- `ingredient_id` 있으면 → ID로 fetch, 없으면 기존 이름 검색 or 신규 생성

---

## Frontend

### 신규 페이지: `frontend/src/pages/Invoice.jsx`

로컬 state로 현재 step(1/2/3) 관리하는 단일 컴포넌트.

#### Step 1 — 업로드
- 드래그앤드롭 + 클릭 파일 선택
- 선택 후 이미지 썸네일 미리보기
- "분석하기" 버튼 (파일 없으면 disabled)
- `POST /vision/invoice/preview` 호출 중 로딩 스피너

#### Step 2 — 검토/수정
- 상단: supplier 텍스트 인풋 + invoice_date 텍스트 인풋 (편집 가능)
- 중복 경고 배너 (조건부, 노란색):
  > "⚠ 동일한 납품서가 이미 저장되어 있습니다. 중복 저장 시 재고가 중복 반영됩니다."
- 아이템 테이블:

  | ☑ | 재료명 | 수량 | 단위 | 단가 | 매칭 상태 |
  |---|--------|------|------|------|-----------|
  | ✓ | chicken breast | 10 | kg | 5.99 | ✓ 기존 매칭 |
  | ✓ | mozz cheese | 3 | kg | — | ⚠ [mozzarella cheese ▾] |
  | ✓ | new herb mix | 1 | bag | 4.50 | ✨ 신규 생성 |
  | ☐ | unwanted item | 2 | ea | 1.00 | (회색 처리) |

  - name/quantity/unit/unit_price 셀: 인라인 `<input>` 편집 가능
  - 체크박스 해제 → 행 전체 회색 처리
  - 매칭 상태:
    - `match_score === 1.0` → "✓ 기존 매칭" (초록)
    - `0.7 ≤ match_score < 1.0` → 드롭다운: [제안 재료명] or "신규 생성" (노란)
    - `match_score < 0.7` → "✨ 신규 생성" (파랑)
  - 드롭다운에서 기존 재료 선택 → `ingredient_id` 해당 ID로 설정
  - "신규 생성" 선택 → `ingredient_id` null
- "재고 반영" 버튼 → confirm payload 생성 → `POST /vision/invoice/confirm`

#### Step 3 — 완료
- "✅ X개 항목 재고 반영 완료, Y개 항목 건너뜀"
- 저장된 아이템 목록 + action 배지: "기존 재료" (matched) / "신규 등록" (created)
- "대시보드로 이동" 버튼 → `/` 이동
- "다른 납품서 스캔" 버튼 → Step 1 리셋

---

## 라우팅

### `frontend/src/App.jsx`
`<Route path="/invoice" element={<Invoice />} />` 추가

### `frontend/src/components/Navbar.jsx`
"납품서 스캔" → `/invoice` 링크 추가

---

## 재사용

| 자산 | 위치 | 용도 |
|------|------|------|
| `parse_image_with_claude()` | `backend/services/claude.py` | preview 엔드포인트에서 그대로 재사용 |
| `INVOICE_EXTRACTION_PROMPT` | `backend/routers/vision.py` | preview 엔드포인트에서 재사용 |
| `_strip_fences()`, `_parse_invoice_json()` | `backend/routers/vision.py` | preview에서 재사용 |
| `_find_ingredient_by_name()` | `backend/services/invoice.py` | 폴백용 유지 |
| `_create_ingredient()` | `backend/services/invoice.py` | 그대로 재사용 |
| `_create_log()` | `backend/services/invoice.py` | 그대로 재사용 |
| `Ingredient`, `InventoryLog` | `backend/models/database.py` | 그대로 재사용 |

---

## 수정/생성 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/routers/vision.py` | `/preview`, `/confirm` 엔드포인트 추가 |
| `backend/services/invoice.py` | `fuzzy_match_ingredient()` 추가, `process_invoice_items` 확장 |
| `frontend/src/pages/Invoice.jsx` | 신규 — 3단계 납품서 검토 UI |
| `frontend/src/App.jsx` | `/invoice` 라우트 추가 |
| `frontend/src/components/Navbar.jsx` | "납품서 스캔" 링크 추가 |

---

## 검증

1. 백엔드 실행: `backend/` 에서 `uvicorn main:app --reload`
2. 프론트엔드 실행: `frontend/` 에서 `npm run dev`
3. `/invoice` 페이지에서 납품서 이미지 업로드
4. Step 2: 파싱된 아이템 + 매칭 상태 확인
5. 아이템명 수정, 체크박스 해제, 드롭다운으로 기존 재료 선택
6. "재고 반영" 클릭
7. Step 3: 성공 화면 + 저장 건수 확인
8. DB에서 `current_stock` 업데이트 확인 (제외 항목 반영 안됨)
9. 같은 이미지 재업로드 → 중복 경고 배너 표시 확인
10. 백엔드 테스트: `pytest backend/tests/test_vision_invoice.py -v`

## 기타 고려사항

- 기존 `/vision/invoice` 엔드포인트 유지 (하위 호환)
- `difflib`은 Python 표준 라이브러리, 별도 설치 불필요
- confirm 시 이미지 재전송 없음 — 파싱 데이터만 JSON으로 전송
- `ingredient_id`로 fetch 실패 시 → 404가 아닌 신규 생성으로 폴백
- 아이템 0개 전체 제외 후 confirm → HTTP 200, `items_processed: 0`
