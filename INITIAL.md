# FEATURE

납품서 사진 → Vision 파싱 → 재고 자동 업데이트.
Claude Vision이 납품서 이미지에서 재료/수량 추출 후 inventory_logs에 자동 저장.

## 원하는 동작
- 사장이 납품서 사진 업로드 → Claude Vision이 라인 아이템 JSON 추출
- 추출된 재료명으로 기존 Ingredient 조회 (대소문자 무시 매칭)
  - 매칭 성공 → InventoryLog 생성 + current_stock 증가
  - 매칭 실패 → Ingredient 신규 생성 + InventoryLog 생성
- 처리 결과 반환: 공급업체, 날짜, 아이템별 action(matched/created)

## 사용자 시나리오
1. 사장이 납품서 사진 업로드 (jpeg/png/webp/gif)
2. 백엔드가 Claude Vision에 이미지 + 추출 프롬프트 전달
3. Claude가 JSON 반환: { supplier_name, invoice_date, items: [{name, quantity, unit, unit_price}] }
4. 각 아이템마다 Ingredient 테이블 조회 → 매칭 or 신규 생성
5. InventoryLog 생성 + ingredient.current_stock 업데이트
6. DB commit 후 처리 결과 반환

# EXAMPLES

examples/ 폴더 참고

# DOCUMENTATION

- Claude API: https://docs.anthropic.com/en/api/getting-started
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- FastAPI: https://fastapi.tiangolo.com/

# OTHER CONSIDERATIONS

- 기존 parse_image_with_claude() 재사용 (backend/services/claude.py)
- 기존 Ingredient, InventoryLog 모델 재사용 (backend/models/database.py)
- Claude가 마크다운 코드펜스 포함 응답할 수 있음 → fence strip 필요
- max_tokens=2048 (납품서 JSON이 길 수 있음)
- change_type="delivery" 고정
- 같은 납품서에 동일 재료 두 줄 → 두 개 InventoryLog 생성 (정상)
- 아이템 0개 반환도 HTTP 200 (오류 아님)
- Claude JSON 파싱 실패 → HTTP 422 (500 아님)
