def process_document(
    job_id: str,
    source_path: str,
    original_filename: str,
) -> dict:
    """
    Placeholder task.

    The real document analysis logic will be implemented
    when the Worker service is added.
    """
    return {
        "job_id": job_id,
        "source_path": source_path,
        "original_filename": original_filename,
        "status": "received",
    }