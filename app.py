from __future__ import annotations

import logging
import os
import time
import uuid
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from flask import Flask, Response, jsonify, render_template, request, send_file
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from analysis_service import (
    AnalysisError,
    build_analysis_payload,
    generate_detailed_csv,
    parse_uploaded_feedback,
    search_feedback,
)
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


# Global in-memory storage for handling files across hard page loads
SERVER_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_LOCK = Lock()

def create_app() -> Flask:
    app = Flask(__name__)

    max_upload_mb = _to_int(os.getenv("MAX_UPLOAD_MB"), default=5, minimum=1)
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
    app.config["JSON_SORT_KEYS"] = False

    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    logger = logging.getLogger(__name__)

    rate_limit = _to_int(os.getenv("RATE_LIMIT_PER_MIN"), default=60, minimum=1)
    session_ttl = _to_int(os.getenv("SESSION_TTL_MINUTES"), default=30, minimum=1) * 60  # seconds
    trust_proxy_headers = _to_bool(os.getenv("TRUST_PROXY_HEADERS"), default=False)
    if trust_proxy_headers:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    history: dict[str, deque[float]] = defaultdict(deque)
    limiter_lock = Lock()
    request_counter = 0
    last_session_cleanup = time.time()
    SESSION_CLEANUP_INTERVAL = 300  # 5 minutes
    MAX_SESSIONS = _to_int(os.getenv("MAX_SESSIONS"), default=1000, minimum=10)

    def _cleanup_expired_sessions():
        """Remove sessions older than session_ttl. Called periodically."""
        now = time.time()
        with SESSION_LOCK:
            expired = [sid for sid, data in SERVER_SESSIONS.items()
                       if now - data.get("last_accessed", 0) > session_ttl]
            for sid in expired:
                del SERVER_SESSIONS[sid]
        if expired:
            logger.info("Evicted %d expired session(s)", len(expired))

    def _get_session(sid: str | None):
        """Retrieve a valid, non-expired session or raise AnalysisError."""
        if not sid:
            raise AnalysisError("Session expired.", code="MISSING_SESSION")
        with SESSION_LOCK:
            session = SERVER_SESSIONS.get(sid)
            if not session:
                raise AnalysisError("Session expired.", code="MISSING_SESSION")
            if time.time() - session.get("last_accessed", 0) > session_ttl:
                SERVER_SESSIONS.pop(sid, None)
                raise AnalysisError("Session expired.", code="MISSING_SESSION")
            session["last_accessed"] = time.time()
        return session

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
            # Periodic session cleanup (time-based, every 5 minutes)
            nonlocal last_session_cleanup
            now_for_cleanup = time.time()
            if now_for_cleanup - last_session_cleanup >= SESSION_CLEANUP_INTERVAL:
                last_session_cleanup = now_for_cleanup
                _cleanup_expired_sessions()

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

    @app.after_request
    def add_security_headers(response: Response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://lh3.googleusercontent.com https://lh3.googleusercontent.com/aida-public/; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-DNS-Prefetch-Control"] = "off"
        # Prevent caching of API responses containing session IDs
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/")
    def page_home():
        return render_template("home.html")

    @app.get("/dashboard")
    def page_dashboard():
        return render_template("dashboard.html")

    @app.get("/analytics")
    def page_analytics():
        return render_template("analytics.html")

    @app.get("/raw_data")
    def page_raw_data():
        return render_template("raw_data.html")

    @app.get("/compare")
    def page_compare():
        return render_template("compare.html")

    @app.get("/reports")
    def page_reports():
        return render_template("reports.html")

    @app.get("/api/data")
    def get_data():
        sid = request.args.get("sid")
        session = _get_session(sid)
        data = dict(session["analysis"])
        if "comparison" in session:
            data["comparison"] = session["comparison"]
        return jsonify(ApiSuccessResponse(data=data).model_dump())

    @app.post("/api/analyze")
    def analyze_upload():
        uploaded_file = request.files.get("feedback_file")
        parsed = parse_uploaded_feedback(uploaded_file)
        data = build_analysis_payload(parsed)
        
        sid = str(uuid.uuid4())
        now = time.time()
        with SESSION_LOCK:
            # Prevent memory exhaustion from unbounded session creation
            if len(SERVER_SESSIONS) >= MAX_SESSIONS:
                raise AnalysisError(
                    "Server is at capacity. Please try again later.",
                    code="capacity_exceeded",
                    status_code=503,
                )
            SERVER_SESSIONS[sid] = {
                "parsed": parsed,
                "analysis": data,
                "created_at": now,
                "last_accessed": now,
            }
        payload = ApiSuccessResponse(data={"session_id": sid})
        return jsonify(payload.model_dump())

    @app.post("/api/search")
    def search_upload():
        sid = request.form.get("sid")
        session = _get_session(sid)
            
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

        parsed = session["parsed"]
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

        sid = str(uuid.uuid4())
        now = time.time()
        with SESSION_LOCK:
            if len(SERVER_SESSIONS) >= MAX_SESSIONS:
                raise AnalysisError(
                    "Server is at capacity. Please try again later.",
                    code="capacity_exceeded",
                    status_code=503,
                )
            SERVER_SESSIONS[sid] = {
                "parsed": parsed_a,
                "analysis": analysis_a,
                "comparison": {
                    "candidate": analysis_b,
                    "delta": deltas,
                },
                "created_at": now,
                "last_accessed": now,
            }

        payload = ApiSuccessResponse(
            data={
                "session_id": sid,
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

    @app.get("/api/export-summary-pdf")
    def export_summary_pdf():
        sid = request.args.get("sid")
        session = _get_session(sid)
            
        analysis = session["analysis"]
        if not isinstance(analysis, dict):
            raise AnalysisError("analysis payload is required for PDF export")

        pdf_bytes = build_executive_summary_pdf(analysis)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="executive_summary_{sid[:8]}.pdf"'},
        )

    @app.get("/api/export-detailed-csv")
    def export_detailed_csv():
        sid = request.args.get("sid")
        session = _get_session(sid)
            
        analysis = session["analysis"]
        parsed = session["parsed"]

        csv_content = generate_detailed_csv(analysis, parsed.csv_rows)
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="detailed_analysis_{sid[:8]}.csv"'},
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=_to_bool(os.getenv("FLASK_DEBUG"), default=False))
