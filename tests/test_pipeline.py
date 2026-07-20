import pytest
from pydantic import ValidationError

from src.pipeline import (
    CountryRecord,
    IpLocationRecord,
    WeatherRecord,
    extract_weather_records,
    validate_records,
)


def test_weather_record_validates_normal_data() -> None:
    """정상 날씨 데이터는 Pydantic 모델 검증을 통과해야 합니다."""

    record = WeatherRecord.model_validate(
        {
            "source": "open_meteo",
            "time": "2026-07-20T00:00",
            "temperature_2m": 25.5,
            "precipitation_probability": 30,
        }
    )

    assert record.temperature_2m == 25.5
    assert record.precipitation_probability == 30


def test_weather_record_rejects_invalid_range() -> None:
    """강수확률은 0~100 범위를 벗어나면 실패해야 합니다."""

    with pytest.raises(ValidationError):
        WeatherRecord.model_validate(
            {
                "source": "open_meteo",
                "time": "2026-07-20T00:00",
                "temperature_2m": 25.5,
                "precipitation_probability": 130,
            }
        )


def test_country_record_rejects_empty_text() -> None:
    """국가명처럼 필요한 문자열 필드는 빈 값이면 실패해야 합니다."""

    with pytest.raises(ValidationError):
        CountryRecord.model_validate(
            {
                "source": "countries_dev",
                "name": "",
                "cca2": "KR",
                "cca3": "KOR",
                "capital": "Seoul",
                "region": "Asia",
                "population": 51_000_000,
            }
        )


def test_ip_record_rejects_invalid_latitude() -> None:
    """위도는 -90~90 범위를 벗어나면 실패해야 합니다."""

    with pytest.raises(ValidationError):
        IpLocationRecord.model_validate(
            {
                "source": "ip_api",
                "query": "8.8.8.8",
                "country": "United States",
                "city": "Ashburn",
                "lat": 120.0,
                "lon": -77.5,
                "timezone": "America/New_York",
            }
        )


def test_extract_weather_records_returns_hourly_rows() -> None:
    """Open-Meteo 응답에서 시간대별 행이 만들어져야 합니다."""

    rows = extract_weather_records(
        {
            "hourly": {
                "time": ["2026-07-20T00:00", "2026-07-20T01:00"],
                "temperature_2m": [25.1, 24.7],
                "precipitation_probability": [10, 20],
            }
        }
    )

    assert len(rows) == 2
    assert rows[0]["source"] == "open_meteo"


def test_validate_records_separates_valid_and_error_rows() -> None:
    """수집 데이터 검증 결과는 성공 목록과 실패 목록으로 분리되어야 합니다."""

    raw_data = {
        "open_meteo": {
            "hourly": {
                "time": ["2026-07-20T00:00"],
                "temperature_2m": [25.1],
                "precipitation_probability": [10],
            }
        },
        "countries_dev": {
            "name": {"common": "South Korea"},
            "cca2": "KR",
            "cca3": "KOR",
            "capital": ["Seoul"],
            "region": "Asia",
            "population": 51_000_000,
        },
        "ip_api": {
            "status": "success",
            "query": "8.8.8.8",
            "country": "United States",
            "city": "Ashburn",
            "lat": 39.03,
            "lon": -77.5,
            "timezone": "America/New_York",
        },
    }

    valid_records, error_records = validate_records(raw_data)

    assert len(valid_records) == 3
    assert error_records == []
