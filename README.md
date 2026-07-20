# Day 1 종합 실습 - 실무형 수집·검증·품질 파이프라인

작성자: 조현강 (광주 4반)

## 실습 목표

3개 공개 API를 동시에 수집하고, 필요한 필드를 Pydantic v2로 검증한 뒤,
검증 통과 데이터를 CSV와 Parquet로 저장하고 읽기/쓰기 시간을 비교합니다.

## 사용 API

- Open-Meteo: 서울 3일 시간대별 기온, 강수확률
- Countries.dev: 한국 국가 정보
- ip-api: 8.8.8.8 IP 기반 지역 정보

## 실행 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 검사 방법

```bash
pytest
ruff check .
```

## 주요 구조

```text
.
├── main.py
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   └── pipeline.py
├── tests/
│   └── test_pipeline.py
└── output/
    ├── valid_records.csv
    └── valid_records.parquet
```

