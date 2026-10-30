import hashlib
import html
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

from rq import get_current_job


RESULT_DIR = Path(os.getenv("RESULT_DIR", "/data/results"))
WORDS_PER_MINUTE = 200


def update_progress(progress: int, message: str) -> None:
    job = get_current_job()

    if job is None:
        return

    job.meta["progress"] = progress
    job.meta["progress_message"] = message
    job.save_meta()


def atomic_write_text(
    destination: Path,
    content: str,
    encoding: str = "utf-8",
) -> None:
    temporary_path = destination.with_suffix(
        destination.suffix + ".tmp"
    )

    temporary_path.write_text(content, encoding=encoding)
    temporary_path.replace(destination)


def extract_words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text.lower(), flags=re.UNICODE)


def build_html_report(report: dict) -> str:
    frequent_terms = report["frequent_terms"]

    if frequent_terms:
        term_rows = "\n".join(
            (
                "<tr>"
                f"<td>{html.escape(item['term'])}</td>"
                f"<td>{item['count']}</td>"
                "</tr>"
            )
            for item in frequent_terms
        )
    else:
        term_rows = '<tr><td colspan="2">No words found</td></tr>'

    safe_filename = html.escape(report["original_filename"])

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DocFlow Report</title>

    <style>
        body {{
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            font-family: Arial, sans-serif;
            color: #1f2937;
            background: #f8fafc;
        }}

        .card {{
            padding: 24px;
            border: 1px solid #dbe2ea;
            border-radius: 12px;
            background: white;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin: 24px 0;
        }}

        .metric {{
            padding: 16px;
            border-radius: 8px;
            background: #eff6ff;
        }}

        .metric strong {{
            display: block;
            margin-top: 6px;
            font-size: 24px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th,
        td {{
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
        }}

        code {{
            overflow-wrap: anywhere;
        }}
    </style>
</head>

<body>
    <main class="card">
        <h1>DocFlow document report</h1>
        <p><strong>File:</strong> {safe_filename}</p>
        <p><strong>Job:</strong> <code>{report["job_id"]}</code></p>

        <section class="metrics">
            <div class="metric">
                Words
                <strong>{report["word_count"]}</strong>
            </div>

            <div class="metric">
                Lines
                <strong>{report["line_count"]}</strong>
            </div>

            <div class="metric">
                Characters
                <strong>{report["character_count"]}</strong>
            </div>

            <div class="metric">
                Reading time
                <strong>{report["estimated_reading_minutes"]} min</strong>
            </div>
        </section>

        <h2>Frequent terms</h2>

        <table>
            <thead>
                <tr>
                    <th>Term</th>
                    <th>Occurrences</th>
                </tr>
            </thead>
            <tbody>
                {term_rows}
            </tbody>
        </table>

        <h2>Integrity</h2>
        <p><strong>Size:</strong> {report["file_size_bytes"]} bytes</p>
        <p><strong>SHA-256:</strong></p>
        <code>{report["sha256"]}</code>
    </main>
</body>
</html>
"""


def process_document(
    job_id: str,
    source_path: str,
    original_filename: str,
) -> dict:
    source = Path(source_path)

    if not source.is_file():
        raise FileNotFoundError(
            f"Source document does not exist: {source}"
        )

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    update_progress(10, "Reading document")

    raw_content = source.read_bytes()
    text = raw_content.decode("utf-8-sig")

    update_progress(40, "Analyzing document")

    words = extract_words(text)
    frequencies = Counter(words)

    line_count = len(text.splitlines())
    word_count = len(words)
    character_count = len(text)

    estimated_reading_minutes = (
        math.ceil(word_count / WORDS_PER_MINUTE)
        if word_count > 0
        else 0
    )

    frequent_terms = [
        {
            "term": term,
            "count": count,
        }
        for term, count in frequencies.most_common(10)
    ]

    report = {
        "job_id": job_id,
        "source_path": source_path,
        "original_filename": original_filename,
        "stored_filename": source.name,
        "file_size_bytes": len(raw_content),
        "line_count": line_count,
        "word_count": word_count,
        "unique_word_count": len(frequencies),
        "character_count": character_count,
        "estimated_reading_minutes": estimated_reading_minutes,
        "frequent_terms": frequent_terms,
        "sha256": hashlib.sha256(raw_content).hexdigest(),
    }

    update_progress(75, "Generating reports")

    json_path = RESULT_DIR / f"{job_id}.json"
    html_path = RESULT_DIR / f"{job_id}.html"

    json_content = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    )

    html_content = build_html_report(report)

    atomic_write_text(json_path, json_content)
    atomic_write_text(html_path, html_content)

    update_progress(100, "Processing completed")

    return {
        **report,
        "result_url": f"/api/jobs/{job_id}/result",
        "download_url": f"/api/jobs/{job_id}/download",
    }