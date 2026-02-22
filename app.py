from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from analysis_service import AnalysisError, build_analysis_payload, parse_uploaded_feedback, search_feedback
from api_schemas import ApiErrorResponse, ApiSuccessResponse
from pdf_export import build_executive_summary_pdf


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _to_int(value: str | None, default: int, minimum: int = 1) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def create_app() -> Flask:
    app = Flask(__name__)

    max_upload_mb = _to_int(os.getenv("MAX_UPLOAD_MB"), default=5, minimum=1)
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
    app.config["JSON_SORT_KEYS"] = False

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    logger = logging.getLogger(__name__)

    rate_limit = _to_int(os.getenv("RATE_LIMIT_PER_MIN"), default=60, minimum=1)
    trust_proxy_headers = _to_bool(os.getenv("TRUST_PROXY_HEADERS"), default=False)
    if trust_proxy_headers:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    history: dict[str, deque[float]] = defaultdict(deque)
    limiter_lock = Lock()
    request_counter = 0

    def _client_ip() -> str:
        if trust_proxy_headers:
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[0].strip() or (request.remote_addr or "unknown")
        return request.remote_addr or "unknown"

    @app.before_request
    def simple_rate_limit():
        nonlocal request_counter
        if not request.path.startswith("/api/"):
            return None
        ip = _client_ip()
        now = time.time()
        with limiter_lock:
            request_counter += 1
            if request_counter % 100 == 0:
                stale_ips = []
                for stored_ip, q in history.items():
                    while q and now - q[0] > 60:
                        q.popleft()
                    if not q:
                        stale_ips.append(stored_ip)
                for stored_ip in stale_ips:
                    history.pop(stored_ip, None)

            q = history[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= rate_limit:
                payload = ApiErrorResponse(error={"code": "rate_limited", "message": "Too many requests. Try again in a minute."})
                return jsonify(payload.model_dump()), 429
            q.append(now)
        return None

    @app.errorhandler(AnalysisError)
    def handle_analysis_error(exc: AnalysisError):
        payload = ApiErrorResponse(error={"code": exc.code, "message": exc.message})
        return jsonify(payload.model_dump()), exc.status_code

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_file(_exc: RequestEntityTooLarge):
        payload = ApiErrorResponse(
            error={
                "code": "file_too_large",
                "message": f"File too large. Max allowed is {max_upload_mb} MB.",
            }
        )
        return jsonify(payload.model_dump()), 413

    @app.errorhandler(ValidationError)
    def handle_schema_error(exc: ValidationError):
        payload = ApiErrorResponse(
            error={"code": "schema_error", "message": f"Response schema validation failed: {exc.errors()[0]['msg']}"}
        )
        return jsonify(payload.model_dump()), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        if not request.path.startswith("/api/"):
            return exc
        payload = ApiErrorResponse(error={"code": "http_error", "message": exc.description})
        return jsonify(payload.model_dump()), exc.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        if isinstance(exc, HTTPException):
            return exc
        logger.exception("Unhandled API error: %s", exc)
        payload = ApiErrorResponse(error={"code": "internal_error", "message": "Unexpected server error"})
        return jsonify(payload.model_dump()), 500

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.post("/api/analyze")
    def analyze_upload():
        uploaded_file = request.files.get("feedback_file")
        parsed = parse_uploaded_feedback(uploaded_file)
        data = build_analysis_payload(parsed)
        payload = ApiSuccessResponse(data=data)
        return jsonify(payload.model_dump())

    @app.post("/api/search")
    def search_upload():
        keyword = (request.form.get("keyword") or "").strip()
        case_sensitive = _to_bool(request.form.get("case_sensitive"), default=False)
        match_mode = (request.form.get("match_mode") or "partial").strip().lower()
        sentiment_filter = (request.form.get("sentiment_filter") or "all").strip().lower()
        min_rating_raw = (request.form.get("min_rating") or "").strip()
        if min_rating_raw:
            try:
                min_rating = int(min_rating_raw)
            except ValueError as exc:
                raise AnalysisError("min_rating must be a number between 1 and 5") from exc
        else:
            min_rating = None

        uploaded_file = request.files.get("feedback_file")
        parsed = parse_uploaded_feedback(uploaded_file)
        matches = search_feedback(
            parsed.feedback_list,
            keyword,
            case_sensitive=case_sensitive,
            match_mode=match_mode,
            sentiment_filter=sentiment_filter,
            min_rating=min_rating,
            csv_rows=parsed.csv_rows,
        )
        data: dict[str, Any] = {
            "keyword": keyword,
            "count": len(matches),
            "matches": matches[:200],
            "options": {
                "case_sensitive": case_sensitive,
                "match_mode": match_mode,
                "sentiment_filter": sentiment_filter,
                "min_rating": min_rating,
            },
        }
        payload = ApiSuccessResponse(data=data)
        return jsonify(payload.model_dump())

    @app.post("/api/compare")
    def compare_uploads():
        first = request.files.get("feedback_file")
        second = request.files.get("feedback_file_compare")
        if not second:
            raise AnalysisError("Please upload a second file to compare")

        parsed_a = parse_uploaded_feedback(first)
        parsed_b = parse_uploaded_feedback(second)

        analysis_a = build_analysis_payload(parsed_a)
        analysis_b = build_analysis_payload(parsed_b)

        deltas = {
            "total_feedback_delta": analysis_b["stats"]["total"] - analysis_a["stats"]["total"],
            "positive_pct_delta": round(
                analysis_b["sentiment_percent"]["Positive"] - analysis_a["sentiment_percent"]["Positive"], 1
            ),
            "negative_pct_delta": round(
                analysis_b["sentiment_percent"]["Negative"] - analysis_a["sentiment_percent"]["Negative"], 1
            ),
            "avg_rating_delta": (
                round((analysis_b["average_rating"] or 0) - (analysis_a["average_rating"] or 0), 2)
                if analysis_a["average_rating"] is not None and analysis_b["average_rating"] is not None
                else None
            ),
        }

        payload = ApiSuccessResponse(
            data={
                "baseline": analysis_a,
                "candidate": analysis_b,
                "delta": deltas,
            }
        )
        return jsonify(payload.model_dump())

    @app.get("/api/health")
    def health():
        payload = ApiSuccessResponse(data={"status": "ok"})
        return jsonify(payload.model_dump())

    @app.post("/api/export-summary-pdf")
    def export_summary_pdf():
        body = request.get_json(silent=True) or {}
        analysis = body.get("analysis")
        if not isinstance(analysis, dict):
            raise AnalysisError("analysis payload is required for PDF export")

        pdf_bytes = build_executive_summary_pdf(analysis)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="executive_summary.pdf"'},
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=_to_bool(os.getenv("FLASK_DEBUG"), default=True))
