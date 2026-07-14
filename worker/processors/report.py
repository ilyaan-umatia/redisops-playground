def generate_report(
    payload: dict[str, str | int | float | bool],
) -> dict[str, str | int | float | bool]:
    if payload.get("force_failure") is True:
        raise RuntimeError("Demo report generation failed")
    return {
        "message": "Demo report generated",
        "records_processed": int(payload.get("record_count", 100)),
    }
