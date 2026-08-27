import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from src.config import DEPARTMENTS
from src.db import get_db
from src.services.classifier import classify, build_sla_dates
from src.services.drafter import draft_grievance
from src.services.chat import answer_chat

api_bp = Blueprint("api", __name__)

@api_bp.route("/")
def index():
    return render_template("index.html")

@api_bp.route("/api/classify", methods=["POST"])
def api_classify():
    data = request.get_json(force=True)
    description = data.get("description", "")
    key = classify(description)
    info = DEPARTMENTS[key]
    return jsonify({
        "department_key": key,
        "department_label": info["label"],
        "documents": info["documents"],
        "sla": build_sla_dates(key, datetime.now()),
    })

@api_bp.route("/api/draft", methods=["POST"])
def api_draft():
    data = request.get_json(force=True)
    name = data.get("name", "")
    contact = data.get("contact", "")
    department_key = data.get("department_key", "other")
    department_label = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])["label"]
    description = data.get("description", "")
    text, source = draft_grievance(name, contact, department_label, description)
    return jsonify({"draft": text, "source": source})

@api_bp.route("/api/grievances", methods=["POST"])
def save_grievance():
    data = request.get_json(force=True)
    gid = str(uuid.uuid4())[:8].upper()
    db = get_db()
    db.execute(
        "INSERT INTO grievances VALUES (?,?,?,?,?,?,?,?,?)",
        (
            gid,
            data.get("name", ""),
            data.get("contact", ""),
            data.get("department_key", "other"),
            data.get("department_label", ""),
            data.get("description", ""),
            data.get("draft_text", ""),
            data.get("drafted_by", "template"),
            datetime.now().isoformat(),
        ),
    )
    db.commit()
    return jsonify({"ref_id": gid})

@api_bp.route("/api/grievances", methods=["GET"])
def list_grievances():
    db = get_db()
    rows = db.execute("SELECT * FROM grievances ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        created = datetime.fromisoformat(r["created_at"])
        out.append({
            "ref_id": r["id"],
            "name": r["name"],
            "department_label": r["department_label"],
            "description": r["description"],
            "created_at": created.strftime("%d %b %Y, %I:%M %p"),
            "sla": build_sla_dates(r["department_key"], created),
        })
    return jsonify(out)

@api_bp.route("/api/grievances/<ref_id>/chat", methods=["POST"])
def chat_about_grievance(ref_id):
    db = get_db()
    r = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not r:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(force=True)
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "empty message"}), 400
    reply, source = answer_chat(r, history, message)
    return jsonify({"reply": reply, "source": source})

@api_bp.route("/api/grievances/<ref_id>", methods=["GET"])
def get_grievance(ref_id):
    db = get_db()
    r = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not r:
        return jsonify({"error": "not found"}), 404
    created = datetime.fromisoformat(r["created_at"])
    return jsonify({
        "ref_id": r["id"],
        "name": r["name"],
        "contact": r["contact"],
        "department_label": r["department_label"],
        "description": r["description"],
        "draft_text": r["draft_text"],
        "created_at": created.strftime("%d %b %Y, %I:%M %p"),
        "sla": build_sla_dates(r["department_key"], created),
    })