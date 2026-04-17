# Generate PRP

INITIAL.md 파일을 읽고 완전한 PRP(Product Requirements Prompt)를 생성한다.

## 프로세스

**1. 조사**
- 코드베이스에서 유사 패턴 검색
- examples/ 폴더 참고
- 필요시 외부 문서 fetch
- 불명확한 부분은 사용자에게 질문

**2. PRP 생성**
아래 구조로 `PRPs/{feature-name}.md` 생성:

```markdown
# PRP: {기능명}

## 목적
한 줄 설명

## 컨텍스트
- 관련 파일 경로
- 의존성
- 참고 패턴

## 구현 순서
1. 
2. 
3. 

## API 엔드포인트 (해당시)
- METHOD /path → 설명

## DB 스키마 변경 (해당시)

## Claude API 활용 방식

## 검증 게이트
- [ ] 테스트 항목 1
- [ ] 테스트 항목 2

## 구현 가능성 점수: X/10
```

**3. 완성도 체크**
- 기존 코드 패턴과 일관성
- 엣지케이스 포함 여부
- 검증 가능한 체크리스트
