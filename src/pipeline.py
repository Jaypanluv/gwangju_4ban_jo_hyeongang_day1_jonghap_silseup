"""
Day 1 종합 실습 파이프라인.

작성자: 조현강 (광주 4반)

기능:
1. 3개 공개 API를 asyncio.gather()로 동시에 수집
2. 수집한 JSON에서 필요한 필드를 추출
3. Pydantic v2 모델로 타입과 범위 검증
4. 검증 통과 데이터를 CSV와 Parquet로 저장
5. 두 파일 형식의 읽기/쓰기 시간을 측정하고 비교
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Literal

import httpx
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=37.5665&longitude=126.9780"
    "&hourly=temperature_2m,precipitation_probability"
    "&forecast_days=3&timezone=Asia/Seoul"
)
COUNTRY_URL = "https://countries.dev/alpha/KOR"
IP_API_URL = "http://ip-api.com/json/8.8.8.8"


class WeatherRecord(BaseModel):
    """Open-Meteo 날씨 데이터 한 행을 검증하는 모델."""

    model_config = ConfigDict(strict=True)

    source: Literal["open_meteo"]
    time: str
    temperature_2m: float = Field(ge=-80, le=80)
    precipitation_probability: int = Field(ge=0, le=100)

    @field_validator("time")
    @classmethod
    def check_time(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("time 값은 비어 있을 수 없습니다.")
        return value


class CountryRecord(BaseModel):
    """Countries.dev 한국 국가 정보 한 행을 검증하는 모델."""

    model_config = ConfigDict(strict=True)

    source: Literal["countries_dev"]
    name: str
    cca2: str
    cca3: str
    capital: str
    region: str
    population: int = Field(ge=0)

    @field_validator("name", "cca2", "cca3", "capital", "region")
    @classmethod
    def check_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("문자열 값은 비어 있을 수 없습니다.")
        return value


class IpLocationRecord(BaseModel):
    """ip-api 위치 정보 한 행을 검증하는 모델."""

    model_config = ConfigDict(strict=True)

    source: Literal["ip_api"]
    query: str
    country: str
    city: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str

    @field_validator("query", "country", "city", "timezone")
    @classmethod
    def check_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("문자열 값은 비어 있을 수 없습니다.")
        return value


async def fetch_json(client: httpx.AsyncClient, api_name: str, url: str) -> dict[str, Any]:
    """API에서 JSON 응답을 가져옵니다."""

    response = await client.get(url)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, dict):
        raise TypeError(f"{api_name} 응답은 dict 형식이어야 합니다.")

    print(f"[수집 성공] {api_name}")
    return data


async def collect_api_data() -> dict[str, dict[str, Any]]:
    """3개 API를 동시에 호출합니다."""

    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        weather_task = fetch_json(client, "open_meteo", OPEN_METEO_URL)
        country_task = fetch_json(client, "countries_dev", COUNTRY_URL)
        ip_task = fetch_json(client, "ip_api", IP_API_URL)

        weather, country, ip_info = await asyncio.gather(
            weather_task,
            country_task,
            ip_task,
        )

    return {
        "open_meteo": weather,
        "countries_dev": country,
        "ip_api": ip_info,
    }


def extract_weather_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Open-Meteo 응답에서 시간, 기온, 강수확률만 추출합니다."""

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise ValueError("Open-Meteo 응답에 hourly 데이터가 없습니다.")

    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    precipitation = hourly.get("precipitation_probability", [])

    return [
        {
            "source": "open_meteo",
            "time": time_value,
            "temperature_2m": float(temperature),
            "precipitation_probability": int(probability),
        }
        for time_value, temperature, probability in zip(
            times,
            temperatures,
            precipitation,
            strict=True,
        )
    ]


def get_first_text(value: Any, default: str) -> str:
    """문자열 또는 리스트 값을 문자열 하나로 정리합니다."""

    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and value:
        return str(value[0])
    return default


def extract_country_record(payload: dict[str, Any]) -> dict[str, Any]:
    """Countries.dev 응답에서 한국 국가 정보만 추출합니다."""

    name_value = payload.get("name")
    if isinstance(name_value, dict):
        name = name_value.get("common") or name_value.get("official") or "South Korea"
    else:
        name = get_first_text(name_value, "South Korea")

    return {
        "source": "countries_dev",
        "name": name,
        "cca2": get_first_text(payload.get("cca2") or payload.get("alpha2Code"), "KR"),
        "cca3": get_first_text(payload.get("cca3") or payload.get("alpha3Code"), "KOR"),
        "capital": get_first_text(payload.get("capital"), "Seoul"),
        "region": get_first_text(payload.get("region"), "Asia"),
        "population": int(payload.get("population", 0)),
    }


def extract_ip_record(payload: dict[str, Any]) -> dict[str, Any]:
    """ip-api 응답에서 IP 위치 정보만 추출합니다."""

    if payload.get("status") != "success":
        raise ValueError(f"ip-api 응답 상태가 success가 아닙니다: {payload.get('status')}")

    return {
        "source": "ip_api",
        "query": payload.get("query", ""),
        "country": payload.get("country", ""),
        "city": payload.get("city", ""),
        "lat": float(payload.get("lat")),
        "lon": float(payload.get("lon")),
        "timezone": payload.get("timezone", ""),
    }


def validate_records(
    raw_data: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """추출한 데이터를 Pydantic v2 모델로 검증합니다."""

    valid_records: list[dict[str, Any]] = []
    error_records: list[dict[str, Any]] = []
    targets: list[tuple[str, type[BaseModel], dict[str, Any]]] = []

    for item in extract_weather_records(raw_data["open_meteo"]):
        targets.append(("open_meteo", WeatherRecord, item))

    targets.append(("countries_dev", CountryRecord, extract_country_record(raw_data["countries_dev"])))
    targets.append(("ip_api", IpLocationRecord, extract_ip_record(raw_data["ip_api"])))

    for index, (source, model, item) in enumerate(targets, start=1):
        try:
            record = model.model_validate(item)
            valid_records.append(record.model_dump())
        except ValidationError as error:
            error_records.append(
                {
                    "row": index,
                    "source": source,
                    "input": item,
                    "error": error.errors(),
                }
            )

    return valid_records, error_records


def measure_storage_performance(
    records: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, float | str]:
    """CSV와 Parquet 저장/읽기 시간을 측정하고 비교합니다."""

    output_dir.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(records)
    csv_path = output_dir / "valid_records.csv"
    parquet_path = output_dir / "valid_records.parquet"

    csv_write_start = time.perf_counter()
    dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")
    csv_write_time = time.perf_counter() - csv_write_start

    parquet_write_start = time.perf_counter()
    dataframe.to_parquet(parquet_path, index=False)
    parquet_write_time = time.perf_counter() - parquet_write_start

    csv_read_start = time.perf_counter()
    csv_data = pd.read_csv(csv_path)
    csv_read_time = time.perf_counter() - csv_read_start

    parquet_read_start = time.perf_counter()
    parquet_data = pd.read_parquet(parquet_path)
    parquet_read_time = time.perf_counter() - parquet_read_start

    if len(csv_data) != len(records) or len(parquet_data) != len(records):
        raise ValueError("저장 후 다시 읽은 데이터 건수가 원본과 다릅니다.")

    return {
        "csv_write": csv_write_time,
        "csv_read": csv_read_time,
        "csv_size_kb": csv_path.stat().st_size / 1024,
        "parquet_write": parquet_write_time,
        "parquet_read": parquet_read_time,
        "parquet_size_kb": parquet_path.stat().st_size / 1024,
        "write_faster": "CSV" if csv_write_time < parquet_write_time else "Parquet",
        "read_faster": "CSV" if csv_read_time < parquet_read_time else "Parquet",
        "row_count": float(len(records)),
    }


async def run_pipeline(output_dir: Path) -> dict[str, Any]:
    """수집, 검증, 저장, 성능 비교를 순서대로 실행합니다."""

    raw_data = await collect_api_data()
    valid_records, error_records = validate_records(raw_data)
    performance = measure_storage_performance(valid_records, output_dir)

    return {
        "valid_count": len(valid_records),
        "error_count": len(error_records),
        "errors": error_records,
        "performance": performance,
    }

