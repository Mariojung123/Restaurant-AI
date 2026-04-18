# Recipe Natural Language Registration — Feature Spec

## Overview

레시피 자연어 등록 플로우. 사장이 재료를 자연어로 입력하면 Claude가 수량/단위 추측 → 기존 재고 재료와 퍼지 매칭 → 확인 후 저장.

Invoice/Receipt와 동일한 2-step 패턴:
- `POST /api/recipe/preview` — Claude NL 파싱 + 기존 Ingredient 퍼지 매칭, DB 쓰기 없음
- `POST /api/recipe/confirm` — Recipe + RecipeIngredient 저장

---

## DB 구조 (기존, 변경 없음)

```
Recipe: id, name, description, price
RecipeIngredient: recipe_id, ingredient_id, quantity, unit, quantity_display
Ingredient: id, name, unit, current_stock
```

---

## Backend

### `POST /api/recipe/preview`

**목적:** 레시피명 + 자연어 재료 텍스트 파싱. Recipe 퍼지 매칭 아닌 Ingredient 퍼지 매칭. DB 쓰기 없음.

**Input:** JSON body
```json
{
  "name": "Salmon with Cream Sauce",
  "description": "Pan-seared salmon in garlic cream sauce",
  "price": 24.0,
  "ingredient_text": "salmon fillet 200g, butter 1 tablespoon, heavy cream 100ml, garlic 2 cloves, roma tomato 1 piece"
}
```

**처리 순서:**
1. `parse_recipe_ingredients(ingredient_text)` 호출 (기존 `services/claude.py`)
2. 각 파싱 결과 → `fuzzy_match_ingredient(db, name)` (기존 `services/invoice.py` 재사용)
   - score ≥ 0.7 → `suggested_match` + `match_score` 포함
   - score < 0.7 → `suggested_match: null`
3. DB 쓰기 없음

**Output:**
```json
{
  "name": "Salmon with Cream Sauce",
  "description": "Pan-seared salmon in garlic cream sauce",
  "price": 24.0,
  "items": [
    {
      "name": "salmon fillet",
      "quantity": 200.0,
      "unit": "g",
      "quantity_display": "200g",
      "reasoning": "200g is a standard restaurant portion for salmon.",
      "suggested_match": { "id": 2, "name": "salmon fillet", "unit": "kg" },
      "match_score": 1.0
    },
    {
      "name": "garlic",
      "quantity": 6.0,
      "unit": "g",
      "quantity_display": "2 cloves",
      "reasoning": "2 garlic cloves is roughly 6g.",
      "suggested_match": { "id": 7, "name": "garlic", "unit": "unit" },
      "match_score": 1.0
    },
    {
      "name": "black pepper",
      "quantity": 1.0,
      "unit": "g",
      "quantity_display": "a pinch",
      "reasoning": "A pinch of black pepper is about 1g.",
      "suggested_match": null,
      "match_score": 0.0
    }
  ]
}
```

**에러:**
- 400: ingredient_text 비어있음
- 502: Claude API 파싱 실패
- 500: Claude API 오류

---

### `POST /api/recipe/confirm`

**목적:** 유저 검토 후 Recipe + RecipeIngredient 저장.

**Input:** JSON body
```json
{
  "name": "Salmon with Cream Sauce",
  "description": "Pan-seared salmon in garlic cream sauce",
  "price": 24.0,
  "items": [
    {
      "name": "salmon fillet",
      "quantity": 200.0,
      "unit": "g",
      "quantity_display": "200g",
      "ingredient_id": 2,
      "include": true
    },
    {
      "name": "black pepper",
      "quantity": 1.0,
      "unit": "g",
      "quantity_display": "a pinch",
      "ingredient_id": null,
      "include": false
    }
  ]
}
```

**처리 규칙:**
- `include: false` → 스킵
- `ingredient_id` 있음 → 기존 Ingredient 사용
- `ingredient_id` null + `include: true` → 새 Ingredient 생성 (current_stock=0, unit=item.unit)
- Recipe 생성 → RecipeIngredient 연결 → `db.commit()`

**Output:**
```json
{
  "id": 3,
  "name": "Salmon with Cream Sauce",
  "description": "Pan-seared salmon in garlic cream sauce",
  "price": 24.0,
  "ingredients_linked": 2,
  "ingredients_created": 0
}
```

**에러:**
- 409: 동일한 이름의 Recipe 이미 존재

---

## Frontend

### 수정 페이지: `frontend/src/pages/Recipe.jsx`

기존 목록 조회에 3단계 등록 플로우 추가.

#### 기존 목록 화면
- 레시피 카드 목록 (기존 유지)
- "+ Add Recipe" 버튼 → Step 1 진입

#### Step 1 — 레시피 정보 + 재료 입력
- Recipe Name 텍스트 인풋
- Price 숫자 인풋
- Description 텍스트 인풋 (선택)
- Ingredients 텍스트에리어 (자연어 자유 입력)
  - placeholder: `"salmon fillet 200g, butter 1 tablespoon, heavy cream 100ml, garlic 2 cloves"`
- "Analyze" 버튼 → `POST /api/recipe/preview` 호출
- 로딩 중 스피너

#### Step 2 — 검토/수정
- 상단: Recipe 이름/가격 표시 (편집 불가, 확인용)
- 아이템 테이블:

  | ☑ | Ingredient | Qty | Unit | Display | Claude's note | Match |
  |---|-----------|-----|------|---------|--------------|-------|

  - quantity/unit 셀: 인라인 `<input>` 편집 가능
  - 체크박스 해제 → 행 회색 (해당 재료 레시피에서 제외)
  - Claude's note: reasoning 텍스트 (회색, 읽기 전용)
  - 매칭 상태:
    - `match_score === 1.0` → "✓ Matched" (초록)
    - `0.7 ≤ match_score < 1.0` → 드롭다운: [제안 재료명] or "Create new" (노란)
    - `match_score < 0.7` → "✨ New ingredient" (파란) — 저장 시 신규 Ingredient 생성
- "Save Recipe" 버튼 → `POST /api/recipe/confirm`

#### Step 3 — 완료
- "✅ Recipe saved — X ingredients linked, Y new ingredients created"
- 저장된 레시피 이름 + 가격 표시
- "Add Another Recipe" 버튼 → Step 1 리셋
- "Back to List" 버튼 → 목록으로

---

## 재사용

| 자산 | 위치 | 용도 |
|------|------|------|
| `parse_recipe_ingredients()` | `backend/services/claude.py` | preview에서 재사용 |
| `fuzzy_match_ingredient()` | `backend/services/invoice.py` | 재료 퍼지 매칭 재사용 |
| `_create_ingredient()` | `backend/services/invoice.py` | 신규 재료 생성 재사용 |
| Invoice.jsx 구조 | `frontend/src/pages/Invoice.jsx` | Step 2 테이블 패턴 |

---

## 수정/생성 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/routers/recipe.py` | `/preview`, `/confirm` 엔드포인트 추가 |
| `frontend/src/pages/Recipe.jsx` | 3단계 등록 UI 추가 (목록 유지) |

---

## 검증

1. 백엔드: `uvicorn main:app --reload`
2. 프론트: `npm run dev`
3. `/recipe` → "+ Add Recipe" 클릭
4. 재료 자연어 입력 후 "Analyze"
5. Step 2: Claude 파싱 결과 + 재고 재료 매칭 확인
6. 수량 수정, 체크박스 해제 테스트
7. "Save Recipe" → Step 3 확인
8. DB에서 Recipe + RecipeIngredient 저장 확인
9. 동일 이름 재등록 시 409 에러 확인
10. 백엔드 테스트: `pytest backend/tests/test_recipe_register.py -v`

## 기타 고려사항

- `parse_recipe_ingredients()` 는 Claude에게 자연어 재료 → JSON 변환 요청. 이미 구현됨.
- 단위 불일치 허용: Ingredient.unit="kg", RecipeIngredient.unit="g" — 그대로 저장, 환산 없음.
- `quantity_display` 원문 보존: "2 cloves", "a pinch" 등 자연어 표현 그대로 저장.
- 기존 `POST /api/recipe/` 엔드포인트 유지 (Swagger 직접 호출용).
- 테스트명 unique suffix 패턴 유지 (`rec-`, `-99`).
