"""
[Day 1] 종합 실습 실행 파일.

작성자: 조현강 (광주 4반)
"""

import asyncio
from pathlib import Path
from typing import Any

from src.pipeline import run_pipeline


def print_result(result: dict[str, Any]) -> None:
    """파이프라인 실행 결과를 화면에 출력합니다."""

    performance = result["performance"]

    print("\n=== Pydantic 검증 결과 ===")
    print(f"검증 성공: {result['valid_count']}건")
    print(f"검증 실패: {result['error_count']}건")

    if result["errors"]:
        print("\n=== 검증 실패 상세 ===")
        for error in result["errors"]:
            print(error)

    print("\n=== CSV / Parquet 저장 및 성능 비교 ===")
    print(f"CSV 쓰기(저장) 시간: {performance['csv_write']:.6f}초")
    print(f"CSV 읽기 시간: {performance['csv_read']:.6f}초")
    print(f"CSV 파일 크기: {performance['csv_size_kb']:.2f}KB")
    print(f"Parquet 쓰기(저장) 시간: {performance['parquet_write']:.6f}초")
    print(f"Parquet 읽기 시간: {performance['parquet_read']:.6f}초")
    print(f"Parquet 파일 크기: {performance['parquet_size_kb']:.2f}KB")
    print(f"쓰기(저장)가 더 빠른 형식: {performance['write_faster']}")
    print(f"읽기가 더 빠른 형식: {performance['read_faster']}")
    print(f"저장된 행 수: {int(performance['row_count'])}건")


def main() -> None:
    """전체 파이프라인을 실행합니다."""

    result = asyncio.run(run_pipeline(Path("output")))
    print_result(result)


if __name__ == "__main__":
    main()

