import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template, g

try:
    from openai import OpenAI  # pyright: ignore[reportMissingImports]
    _openai_available = True
except ImportError:  # pragma: no cover - package may not be installed locally
    OpenAI = None
    _openai_available = False

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "grievances.db")

# ---------------------------------------------------------------------------
# 1. DEPARTMENT KNOWLEDGE BASE
#    Keyword -> department mapping, plus SLA milestones and document
#    checklists for each. This is the "domain knowledge" that replaces the
#    confusing dropdowns on real portals like CPGRAMS.
# ---------------------------------------------------------------------------

DEPARTMENTS = {
    "epfo": {
        "label": "EPFO (Employees' Provident Fund Organisation)",
        "keywords": ["pf", "provident fund", "epfo", "uan", "pf withdrawal",
                     "pf claim", "pension fund", "eps"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from EPFO officer", 15),
            ("Escalate to Regional PF Commissioner if unresolved", 30),
            ("Escalate to CPGRAMS nodal officer", 45),
        ],
        "documents": ["UAN number", "PF account number / member ID",
                      "Aadhaar linked to UAN", "Bank passbook copy",
                      "Reason for rejection (if reapplying)"],
    },
    "income_tax": {
        "label": "Income Tax Department",
        "keywords": ["income tax", "itr", "tax refund", "pan", "assessing officer",
                     "tds", "form 26as", "notice under section"],
        "sla": [
            ("Acknowledgement generated", 2),
            ("First response from CPC/AO", 21),
            ("Escalate to Grievance Cell (CPGRAMS)", 30),
            ("Escalate to Ombudsman", 60),
        ],
        "documents": ["PAN number", "Assessment year", "ITR acknowledgement number",
                      "Notice/order reference number (if any)", "Form 26AS copy"],
    },
    "railways": {
        "label": "Railways / IRCTC",
        "keywords": ["irctc", "pnr", "train", "railway", "ticket refund",
                     "tatkal", "railways"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from IRCTC/Zonal Railway", 7),
            ("Escalate to Railway Board", 15),
        ],
        "documents": ["PNR number", "Transaction ID / UTR", "Journey date",
                      "Screenshot of refund status (if available)"],
    },
    "passport": {
        "label": "Passport Seva (Ministry of External Affairs)",
        "keywords": ["passport", "passport seva", "psk", "arn number"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from Passport Seva Kendra", 10),
            ("Escalate to Regional Passport Officer", 21),
        ],
        "documents": ["Application Reference Number (ARN/File number)",
                      "Appointment date", "Police verification status (if applicable)"],
    },
    "aadhaar": {
        "label": "UIDAI (Aadhaar)",
        "keywords": ["aadhaar", "uidai", "aadhar", "enrolment id", "eid"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from UIDAI Regional Office", 10),
            ("Escalate to UIDAI HQ Grievance Cell", 20),
        ],
        "documents": ["Aadhaar number / Enrolment ID (EID)", "Update Request Number (URN, if any)",
                      "Proof of identity/address used"],
    },
    "pension": {
        "label": "Pension (CPAO / State Pension Directorate)",
        "keywords": ["pension", "pensioner", "ppo", "cpao", "family pension"],
        "sla": [
            ("Acknowledgement generated", 2),
            ("First response from CPAO/PDA", 21),
            ("Escalate to Department of Pension & Pensioners' Welfare", 45),
        ],
        "documents": ["PPO number", "Bank account & branch details",
                      "Retirement order copy", "Life certificate status"],
    },
    "municipal": {
        "label": "Municipal / Local Body (property tax, water, sanitation)",
        "keywords": ["municipal", "property tax", "water supply", "garbage",
                     "sanitation", "corporation", "nagar nigam", "gram panchayat"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from ward officer", 7),
            ("Escalate to Municipal Commissioner", 15),
        ],
        "documents": ["Property/ward number", "Complaint area photos (if applicable)",
                      "Previous complaint number (if any)"],
    },
    "electricity": {
        "label": "Electricity / Power Utility",
        "keywords": ["electricity", "power cut", "discom", "electricity bill",
                     "transformer", "meter reading"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from local sub-division office", 3),
            ("Escalate to Consumer Grievance Redressal Forum", 10),
        ],
        "documents": ["Consumer account number", "Meter number", "Last bill copy"],
    },
    "banking": {
        "label": "Banking (RBI Ombudsman route)",
        "keywords": ["bank account", "atm", "neft", "upi", "loan", "bank",
                     "cheque bounce", "credit card"],
        "sla": [
            ("Bank's internal grievance response", 30),
            ("Escalate to Banking Ombudsman (RBI) if unresolved", 30),
        ],
        "documents": ["Account/loan/card number", "Transaction reference number",
                      "Bank's complaint reference (if already raised)"],
    },
    "police": {
        "label": "Police / Law & Order",
        "keywords": ["police", "fir", "theft", "complaint against police",
                     "law and order"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from Station House Officer", 7),
            ("Escalate to Superintendent of Police / DCP", 15),
        ],
        "documents": ["FIR number (if filed)", "Police station name",
                      "Incident date and location"],
    },
    "other": {
        "label": "General Public Grievance (CPGRAMS)",
        "keywords": [],
        "sla": [
            ("Acknowledgement generated", 3),
            ("First response from nodal department", 21),
            ("Escalate to DARPG (CPGRAMS)", 30),
        ],
        "documents": ["Any reference/application number related to your issue",
                      "Relevant dates", "Any prior correspondence"],
    },
}


def classify(text: str):
    """Very lightweight keyword scorer. Good enough for a hackathon demo;
    swap for an embeddings/LLM classifier for production."""
    text_l = text.lower()
    best_key, best_score = "other", 0
    for key, info in DEPARTMENTS.items():
        score = sum(1 for kw in info["keywords"] if kw in text_l)
        if score > best_score:
            best_key, best_score = key, score
    return best_key


def build_sla_dates(department_key: str, start: datetime):
    info = DEPARTMENTS[department_key]
    out = []
    for label, days in info["sla"]:
        out.append({
            "label": label,
            "days": days,
            "date": (start + timedelta(days=days)).strftime("%d %b %Y"),
        })
    return out


# ---------------------------------------------------------------------------
# 2. DRAFTING
#    Uses OpenAI if OPENAI_API_KEY is set, otherwise a clean template.
#    Either path returns a properly structured, CPGRAMS-style grievance.
# ---------------------------------------------------------------------------

def draft_with_llm(name, contact, department_label, description):
    client = OpenAI()
    system = (
        "You draft formal, concise Indian public-grievance submissions in the "
        "style expected by portals like CPGRAMS. Structure: Subject line, "
        "Details of Grievance (factual, no exaggeration), Relief Sought. "
        "Keep it under 220 words, plain formal English, no invented facts - "
        "only use what the citizen provided."
    )
    user = (
        f"Citizen name: {name or 'Not provided'}\n"
        f"Contact: {contact or 'Not provided'}\n"
        f"Department: {department_label}\n"
        f"Citizen's own description of the problem:\n{description}\n\n"
        "Draft the grievance now."
    )
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()


def draft_with_template(name, contact, department_label, description):
    """Fallback drafter - no API key needed. Produces a genuinely usable,
    properly formatted grievance so the app works end-to-end offline."""
    clean_desc = re.sub(r"\s+", " ", description).strip()
    subject = clean_desc[:80].rstrip(".,;") + ("..." if len(clean_desc) > 80 else "")
    return (
        f"Subject: Grievance regarding {subject}\n\n"
        f"To,\nThe Grievance Redressal Officer,\n{department_label}\n\n"
        f"Respected Sir/Madam,\n\n"
        f"I, {name or '[Your Name]'}, wish to bring the following issue to your "
        f"kind notice for necessary action.\n\n"
        f"Details of Grievance:\n{clean_desc}\n\n"
        f"Relief Sought:\nI request that the above issue be looked into on "
        f"priority and resolved at the earliest, and that I be informed of the "
        f"action taken.\n\n"
        f"I can be reached at: {contact or '[Your phone/email]'}.\n\n"
        f"Thanking you,\n{name or '[Your Name]'}"
    )


def draft_grievance(name, contact, department_label, description):
    if _openai_available and os.environ.get("OPENAI_API_KEY"):
        try:
            return draft_with_llm(name, contact, department_label, description), "llm"
        except Exception:
            pass  # fall through to template on any API error
    return draft_with_template(name, contact, department_label, description), "template"


# ---------------------------------------------------------------------------
# 2b. CHAT SUPPORT ("what's happening with my grievance")
#     Deliberately narrow scope: the assistant only knows what's in THIS
#     citizen's saved record (description, department, SLA milestones,
#     documents) - never general legal/policy advice. This keeps it from
#     inventing promises it can't back ("your claim will be cleared by
#     Friday"). If no API key is set, a rule-based responder answers the
#     most common questions from the same data, so chat still works offline.
# ---------------------------------------------------------------------------

def chat_with_llm(grievance_row, history, message):
    client = OpenAI()
    created = datetime.fromisoformat(grievance_row["created_at"])
    sla = build_sla_dates(grievance_row["department_key"], created)
    sla_text = "\n".join(f"- {s['label']}: expected by {s['date']}" for s in sla)
    system = (
        "You help a citizen understand ONLY their own grievance below. "
        "Use exclusively the facts given here - never invent a resolution "
        "date, a policy, or a promise that isn't in this data. If asked "
        "something outside this record (general law, other departments, "
        "unrelated topics), say clearly that you don't have that "
        "information and suggest contacting the department directly. "
        "Keep answers under 100 words, plain and reassuring, not robotic.\n\n"
        f"Reference ID: {grievance_row['id']}\n"
        f"Department: {grievance_row['department_label']}\n"
        f"Citizen's description: {grievance_row['description']}\n"
        f"Filed on: {created.strftime('%d %b %Y')}\n"
        f"Expected timeline:\n{sla_text}"
    )
    messages = [{"role": "system", "content": system}]
    for turn in history[-6:]:  # keep last few turns only, stay small/fast
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=messages,
        temperature=0.3,
        max_tokens=220,
    )
    return resp.choices[0].message.content.strip()


def chat_with_rules(grievance_row, message):
    """Offline fallback: keyword-matches the question against the same
    SLA/document data used everywhere else, so chat degrades gracefully
    instead of breaking when there's no API key."""
    created = datetime.fromisoformat(grievance_row["created_at"])
    sla = build_sla_dates(grievance_row["department_key"], created)
    m = message.lower()

    if any(w in m for w in ["document", "attach", "need", "require"]):
        docs = DEPARTMENTS[grievance_row["department_key"]]["documents"]
        return "Documents usually needed for this: " + "; ".join(docs) + "."
    if any(w in m for w in ["when", "how long", "time", "status", "update", "deadline"]):
        lines = [f"{s['label']} - expected by {s['date']}" for s in sla]
        return "Based on the usual timeline for this department: " + " | ".join(lines)
    if any(w in m for w in ["escalate", "no response", "not resolved", "ignored"]):
        last = sla[-1]
        return (f"If there's been no response, the next step is: {last['label']} "
                f"(expected by {last['date']}). Keep your reference ID "
                f"{grievance_row['id']} handy when you follow up.")
    return (f"I can share your filing date, expected timeline, and document "
            f"checklist for reference {grievance_row['id']} - ask me about "
            f"'documents needed' or 'when will this be resolved'. For anything "
            f"beyond this record, please contact {grievance_row['department_label']} directly.")


def answer_chat(grievance_row, history, message):
    if _openai_available and os.environ.get("OPENAI_API_KEY"):
        try:
            return chat_with_llm(grievance_row, history, message), "llm"
        except Exception:
            pass
    return chat_with_rules(grievance_row, message), "rules"


# ---------------------------------------------------------------------------
# 3. STORAGE (SQLite) - lets the user save a grievance and revisit its
#    reference ID + escalation timeline later, simulating the "tracker"
#    that CPGRAMS-style portals rarely make clear.
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grievances (
            id TEXT PRIMARY KEY,
            name TEXT,
            contact TEXT,
            department_key TEXT,
            department_label TEXT,
            description TEXT,
            draft_text TEXT,
            drafted_by TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 4. ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/classify", methods=["POST"])
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


@app.route("/api/draft", methods=["POST"])
def api_draft():
    data = request.get_json(force=True)
    name = data.get("name", "")
    contact = data.get("contact", "")
    department_key = data.get("department_key", "other")
    department_label = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])["label"]
    description = data.get("description", "")
    text, source = draft_grievance(name, contact, department_label, description)
    return jsonify({"draft": text, "source": source})


@app.route("/api/grievances", methods=["POST"])
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


@app.route("/api/grievances", methods=["GET"])
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


@app.route("/api/grievances/<ref_id>/chat", methods=["POST"])
def chat_about_grievance(ref_id):
    db = get_db()
    r = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not r:
        return jsonify({"error": "not found"}), 404
    data = request.get_json(force=True)
    message = data.get("message", "").strip()
    history = data.get("history", [])  # [{role: 'user'|'assistant', content: ''}]
    if not message:
        return jsonify({"error": "empty message"}), 400
    reply, source = answer_chat(r, history, message)
    return jsonify({"reply": reply, "source": source})


@app.route("/api/grievances/<ref_id>", methods=["GET"])
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

init_db()
if __name__ == "__main__":
     app.run(debug=False, port=5000)