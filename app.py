import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import Flask, g, jsonify, render_template, request

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "grievances.db")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


# ---------------------------------------------------------------------------
# Department knowledge base
# ---------------------------------------------------------------------------
DEPARTMENTS = {
    "epfo": {
        "label": "EPFO (Provident Fund)",
        "icon": "💼",
        "keywords": [
            "pf", "provident fund", "epfo", "uan", "pf withdrawal",
            "pf claim", "pension fund", "eps", "epf", "provident"
        ],
        "hindi_keywords": ["पीएफ", "भविष्य निधि", "ईपीएफ", "यूएएन"],
        "documents": [
            "UAN / PF member ID",
            "Claim or transaction reference, if available",
            "Bank details used for the PF claim"
        ],
        "next_steps": [
            "Check your UAN/claim details",
            "Prepare the relevant reference number",
            "Use the official EPFO grievance channel"
        ],
        "sla": [
            ("Acknowledgement / complaint record", 1),
            ("Indicative first response window", 15),
            ("Indicative escalation point", 30)
        ]
    },
    "income_tax": {
        "label": "Income Tax Department",
        "icon": "💰",
        "keywords": [
            "income tax", "itr", "tax refund", "pan", "tds",
            "form 26as", "tax notice", "income tax refund"
        ],
        "hindi_keywords": ["आयकर", "टैक्स", "रिफंड", "पैन", "टीडीएस"],
        "documents": [
            "PAN number",
            "Assessment year",
            "ITR acknowledgement / transaction reference"
        ],
        "next_steps": [
            "Collect PAN and assessment-year details",
            "Keep the ITR / refund reference ready",
            "Verify the official Income Tax grievance route"
        ],
        "sla": [
            ("Complaint record created", 2),
            ("Indicative response window", 21),
            ("Indicative escalation point", 30)
        ]
    },
    "railways": {
        "label": "Railways / IRCTC",
        "icon": "🚆",
        "keywords": [
            "irctc", "pnr", "train", "railway", "ticket refund",
            "tatkal", "railways", "train ticket", "rail ticket"
        ],
        "hindi_keywords": ["रेलवे", "ट्रेन", "टिकट", "पीएनआर"],
        "documents": [
            "PNR number",
            "Ticket / transaction reference",
            "Journey date"
        ],
        "next_steps": [
            "Keep the PNR or booking reference ready",
            "Describe the issue and journey date",
            "Use the official railway grievance channel"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative response window", 7),
            ("Indicative escalation point", 15)
        ]
    },
    "passport": {
        "label": "Passport Seva",
        "icon": "🛂",
        "keywords": [
            "passport", "passport seva", "psk", "arn number",
            "passport application", "passport appointment"
        ],
        "hindi_keywords": ["पासपोर्ट", "पासपोर्ट सेवा"],
        "documents": [
            "Application / file / ARN number",
            "Appointment details, if applicable",
            "Relevant police-verification details, if applicable"
        ],
        "next_steps": [
            "Find your application/file reference",
            "Check appointment or verification status",
            "Use the official Passport Seva grievance route"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative response window", 10),
            ("Indicative escalation point", 21)
        ]
    },
    "aadhaar": {
        "label": "UIDAI (Aadhaar)",
        "icon": "🪪",
        "keywords": [
            "aadhaar", "aadhar", "uidai", "enrolment id", "eid",
            "aadhaar update", "aadhaar card"
        ],
        "hindi_keywords": ["आधार", "यूआईडीएआई", "नामांकन"],
        "documents": [
            "Aadhaar number / Enrolment ID",
            "Update Request Number, if available",
            "Relevant proof used for the request"
        ],
        "next_steps": [
            "Keep your Aadhaar/EID reference ready",
            "Note the date of the update request",
            "Use the official UIDAI grievance channel"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative response window", 10),
            ("Indicative escalation point", 20)
        ]
    },
    "pension": {
        "label": "Pension / Pension Directorate",
        "icon": "👴",
        "keywords": [
            "pension", "pensioner", "ppo", "cpao", "family pension",
            "pension payment", "pension stopped"
        ],
        "hindi_keywords": ["पेंशन", "पेंशनभोगी"],
        "documents": [
            "PPO number",
            "Relevant bank/payment details",
            "Previous pension correspondence, if any"
        ],
        "next_steps": [
            "Keep PPO and payment records ready",
            "Describe the missing or incorrect payment",
            "Use the relevant official pension grievance channel"
        ],
        "sla": [
            ("Complaint record created", 2),
            ("Indicative response window", 21),
            ("Indicative escalation point", 45)
        ]
    },
    "municipal": {
        "label": "Municipal / Local Body",
        "icon": "🏙️",
        "keywords": [
            "municipal", "property tax", "water supply", "garbage",
            "sanitation", "corporation", "nagar nigam", "gram panchayat",
            "street light", "streetlight", "drain", "sewage", "road damage",
            "pothole", "water leakage", "waste collection", "dirty water"
        ],
        "hindi_keywords": [
            "कचरा", "नाली", "सफाई", "सड़क", "गड्ढा", "पानी", "स्ट्रीट लाइट",
            "नगर निगम", "नगर पालिका", "ग्राम पंचायत"
        ],
        "documents": [
            "Area / ward / locality details",
            "Photo of the issue, if useful",
            "Previous complaint number, if any"
        ],
        "next_steps": [
            "Add the exact area or locality",
            "Attach a photo where useful",
            "Use the relevant local body's grievance channel"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative local response window", 7),
            ("Indicative escalation point", 15)
        ]
    },
    "electricity": {
        "label": "Electricity / Power Utility",
        "icon": "⚡",
        "keywords": [
            "electricity", "power cut", "discom", "electricity bill",
            "transformer", "meter reading", "meter", "power supply",
            "voltage", "electric pole", "electric wire"
        ],
        "hindi_keywords": ["बिजली", "विद्युत", "ट्रांसफार्मर", "मीटर"],
        "documents": [
            "Consumer account / connection number",
            "Meter number",
            "Latest electricity bill, if available"
        ],
        "next_steps": [
            "Keep your consumer number ready",
            "Mention outage/billing dates and location",
            "Use the relevant electricity utility grievance channel"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative response window", 3),
            ("Indicative escalation point", 10)
        ]
    },
    "banking": {
        "label": "Banking / Financial Grievance",
        "icon": "🏦",
        "keywords": [
            "bank account", "atm", "neft", "upi", "loan", "bank",
            "cheque bounce", "credit card", "debit card", "transaction",
            "failed transaction", "refund not received", "bank transfer"
        ],
        "hindi_keywords": ["बैंक", "बैंक खाता", "यूपीआई", "लेनदेन", "एटीएम"],
        "documents": [
            "Transaction/reference number",
            "Relevant account/card details",
            "Bank complaint reference, if already raised"
        ],
        "next_steps": [
            "Collect the transaction reference",
            "Check whether the bank complaint was already registered",
            "Use the appropriate official banking grievance route"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative internal response window", 30),
            ("Indicative escalation point", 30)
        ]
    },
    "police": {
        "label": "Police / Law & Order",
        "icon": "👮",
        "keywords": [
            "police", "fir", "theft", "crime", "complaint against police",
            "law and order", "fraud", "stolen", "missing person"
        ],
        "hindi_keywords": ["पुलिस", "एफआईआर", "चोरी", "अपराध", "धोखाधड़ी"],
        "documents": [
            "Incident date and location",
            "Police station details, if known",
            "FIR / complaint number, if already filed"
        ],
        "next_steps": [
            "Record the date, time and location",
            "Keep any existing complaint/FIR reference",
            "Use the appropriate police/emergency channel based on the situation"
        ],
        "sla": [
            ("Complaint record created", 1),
            ("Indicative response window", 7),
            ("Indicative escalation point", 15)
        ]
    },
    "other": {
        "label": "General Public Grievance",
        "icon": "❓",
        "keywords": [],
        "hindi_keywords": [],
        "documents": [
            "Relevant application/reference number",
            "Important dates",
            "Previous correspondence, if any"
        ],
        "next_steps": [
            "Choose the closest department from the list",
            "Keep any application/reference number ready",
            "Verify the correct official grievance channel before filing"
        ],
        "sla": [
            ("Complaint record created", 3),
            ("Indicative response window", 21),
            ("Indicative escalation point", 30)
        ]
    }
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = {
    "status": "TEXT DEFAULT 'submitted'",
    "location": "TEXT DEFAULT ''",
    "updated_at": "TEXT DEFAULT ''",
    "status_note": "TEXT DEFAULT ''"
}


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
    conn.row_factory = sqlite3.Row
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

    existing = {row[1] for row in conn.execute("PRAGMA table_info(grievances)").fetchall()}
    for column, definition in REQUIRED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE grievances ADD COLUMN {column} {definition}")

    conn.execute("UPDATE grievances SET updated_at = created_at WHERE updated_at IS NULL OR updated_at = ''")
    conn.execute("UPDATE grievances SET status = 'submitted' WHERE status IS NULL OR status = ''")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------
WORD_RE = re.compile(r"\w+", re.UNICODE)


def normalise(text):
    text = (text or "").lower().strip()
    return re.sub(r"\s+", " ", text)


def classify_with_score(text):
    text_l = normalise(text)
    best_key = "other"
    best_score = 0
    matched_keywords = []

    for key, info in DEPARTMENTS.items():
        if key == "other":
            continue

        score = 0
        matches = []
        for kw in info["keywords"]:
            if kw in text_l:
                # Exact keyword matches get the strongest signal.
                bonus = 2 if " " in kw else 1
                score += bonus
                matches.append(kw)

        for kw in info.get("hindi_keywords", []):
            if kw in text_l:
                score += 2
                matches.append(kw)

        # Context boosters for frequent two-word combinations.
        if key == "municipal" and any(x in text_l for x in ["street light", "streetlight", "garbage", "pothole"]):
            score += 2
        if key == "electricity" and any(x in text_l for x in ["power cut", "meter", "transformer"]):
            score += 2
        if key == "banking" and any(x in text_l for x in ["upi", "transaction", "atm"]):
            score += 2

        if score > best_score:
            best_key = key
            best_score = score
            matched_keywords = matches

    if best_score == 0:
        return "other", 0, []

    if best_score >= 6:
        confidence = 0.92
    elif best_score >= 4:
        confidence = 0.82
    elif best_score >= 2:
        confidence = 0.68
    else:
        confidence = 0.55

    return best_key, confidence, matched_keywords[:6]


def build_sla_dates(department_key, start):
    info = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])
    return [
        {
            "label": label,
            "days": days,
            "date": (start + timedelta(days=days)).strftime("%d %b %Y")
        }
        for label, days in info["sla"]
    ]


def build_status(status):
    labels = {
        "submitted": "Submitted",
        "under_review": "Under review",
        "in_progress": "In progress",
        "resolved": "Resolved"
    }
    return labels.get(status, "Submitted")


def build_response(key, confidence, matched_keywords):
    info = DEPARTMENTS[key]
    if confidence >= 0.9:
        confidence_label = "High match"
    elif confidence >= 0.75:
        confidence_label = "Good match"
    elif confidence > 0:
        confidence_label = "Possible match"
    else:
        confidence_label = "Needs review"

    if matched_keywords:
        why = [f"Matched terms: {', '.join(matched_keywords)}."]
    else:
        why = ["No strong keyword match was found, so please review the department manually."]

    return {
        "department_key": key,
        "department_label": info["label"],
        "icon": info["icon"],
        "confidence": round(confidence * 100),
        "confidence_label": confidence_label,
        "why": why,
        "documents": info["documents"],
        "next_steps": info["next_steps"],
        "sla": build_sla_dates(key, datetime.now())
    }


# ---------------------------------------------------------------------------
# Drafting
# ---------------------------------------------------------------------------
def draft_with_template(name, contact, department_label, description, location=""):
    clean_desc = re.sub(r"\s+", " ", (description or "")).strip()
    subject = clean_desc[:90].rstrip(".,;")
    if len(clean_desc) > 90:
        subject += "..."

    location_line = location.strip() if location.strip() else "[Location not provided]"

    return (
        f"Subject: Grievance regarding {subject}\n\n"
        f"To,\n"
        f"The Grievance Redressal Officer,\n"
        f"{department_label}\n\n"
        f"Respected Sir/Madam,\n\n"
        f"I, {name or '[Your Name]'}, wish to bring the following issue to your kind notice for necessary action.\n\n"
        f"Details of Grievance:\n{clean_desc}\n\n"
        f"Location:\n{location_line}\n\n"
        f"Relief Sought:\n"
        f"I request that the above issue be examined and necessary action be taken at the earliest. I also request that I be informed of the action taken on this grievance.\n\n"
        f"Contact: {contact or '[Your phone/email]'}\n\n"
        f"Thanking you,\n"
        f"{name or '[Your Name]'}"
    )


def draft_with_llm(name, contact, department_label, description, location):
    client = OpenAI()
    system = (
        "You draft concise public-grievance submissions in plain formal English. "
        "Use only the citizen-provided facts. Structure: Subject, Details of Grievance, "
        "Location, Relief Sought. Keep it under 220 words. Never invent facts, departments, "
        "legal claims, deadlines or government promises."
    )
    user = (
        f"Citizen name: {name or 'Not provided'}\n"
        f"Contact: {contact or 'Not provided'}\n"
        f"Department: {department_label}\n"
        f"Location: {location or 'Not provided'}\n"
        f"Citizen description:\n{description}\n"
    )
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2,
        max_tokens=420
    )
    return response.choices[0].message.content.strip()


def draft_grievance(name, contact, department_label, description, location):
    if OpenAI is not None and os.environ.get("OPENAI_API_KEY"):
        try:
            return draft_with_llm(name, contact, department_label, description, location), "llm"
        except Exception:
            pass
    return draft_with_template(name, contact, department_label, description, location), "template"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/classify")
def api_classify():
    data = request.get_json(silent=True) or {}
    description = str(data.get("description", "")).strip()

    if len(description) < 3:
        return jsonify({"error": "Please describe the problem."}), 400

    key, confidence, matched = classify_with_score(description)
    return jsonify(build_response(key, confidence, matched))


@app.post("/api/draft")
def api_draft():
    data = request.get_json(silent=True) or {}
    description = str(data.get("description", "")).strip()
    if not description:
        return jsonify({"error": "Description is required."}), 400

    department_key = data.get("department_key", "other")
    info = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])

    draft, source = draft_grievance(
        str(data.get("name", "")).strip(),
        str(data.get("contact", "")).strip(),
        info["label"],
        description,
        str(data.get("location", "")).strip()
    )
    return jsonify({"draft": draft, "source": source})


@app.post("/api/grievances")
def save_grievance():
    data = request.get_json(silent=True) or {}
    description = str(data.get("description", "")).strip()
    if not description:
        return jsonify({"error": "Description is required."}), 400

    department_key = data.get("department_key", "other")
    if department_key not in DEPARTMENTS:
        department_key = "other"

    department_label = DEPARTMENTS[department_key]["label"]
    now = datetime.now().isoformat(timespec="seconds")
    gid = uuid.uuid4().hex[:8].upper()

    db = get_db()
    db.execute(
        """
        INSERT INTO grievances (
            id, name, contact, department_key, department_label,
            description, draft_text, drafted_by, created_at,
            status, location, updated_at, status_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            gid,
            str(data.get("name", "")).strip(),
            str(data.get("contact", "")).strip(),
            department_key,
            department_label,
            description,
            str(data.get("draft_text", "")).strip(),
            str(data.get("drafted_by", "template")),
            now,
            "submitted",
            str(data.get("location", "")).strip(),
            now,
            "Prototype record created. No live government system is connected."
        )
    )
    db.commit()

    return jsonify({
        "ref_id": gid,
        "status": "submitted",
        "status_label": "Submitted"
    })


@app.get("/api/grievances")
def list_grievances():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM grievances ORDER BY created_at DESC"
    ).fetchall()

    result = []
    for row in rows:
        created = datetime.fromisoformat(row["created_at"])
        department_key = row["department_key"]
        info = DEPARTMENTS.get(department_key, DEPARTMENTS["other"])
        status = row["status"] or "submitted"

        result.append({
            "ref_id": row["id"],
            "name": row["name"],
            "contact": row["contact"],
            "department_key": department_key,
            "department_label": row["department_label"],
            "icon": info["icon"],
            "description": row["description"],
            "draft_text": row["draft_text"],
            "created_at": created.strftime("%d %b %Y, %I:%M %p"),
            "location": row["location"] or "",
            "status": status,
            "status_label": build_status(status),
            "status_note": row["status_note"] or "",
            "updated_at": row["updated_at"] or row["created_at"],
            "sla": build_sla_dates(department_key, created)
        })

    return jsonify(result)


@app.post("/api/grievances/<ref_id>/advance")
def advance_status(ref_id):
    """Advance the prototype-only status so the demo can show an end-to-end workflow."""
    db = get_db()
    row = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not row:
        return jsonify({"error": "Grievance not found."}), 404

    order = ["submitted", "under_review", "in_progress", "resolved"]
    current = row["status"] or "submitted"
    try:
        index = order.index(current)
    except ValueError:
        index = 0

    if index >= len(order) - 1:
        return jsonify({
            "status": current,
            "status_label": build_status(current),
            "message": "This prototype grievance is already marked resolved."
        })

    next_status = order[index + 1]
    notes = {
        "under_review": "Prototype simulation: department review started.",
        "in_progress": "Prototype simulation: action is in progress.",
        "resolved": "Prototype simulation: issue marked resolved."
    }
    now = datetime.now().isoformat(timespec="seconds")

    db.execute(
        "UPDATE grievances SET status=?, updated_at=?, status_note=? WHERE id=?",
        (next_status, now, notes[next_status], ref_id)
    )
    db.commit()

    return jsonify({
        "status": next_status,
        "status_label": build_status(next_status),
        "message": notes[next_status]
    })


@app.post("/api/grievances/<ref_id>/chat")
def chat_about_grievance(ref_id):
    db = get_db()
    row = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not row:
        return jsonify({"error": "Grievance not found."}), 404

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "Please ask a question."}), 400

    info = DEPARTMENTS.get(row["department_key"], DEPARTMENTS["other"])
    sla = build_sla_dates(row["department_key"], datetime.fromisoformat(row["created_at"]))
    lower = message.lower()

    if any(word in lower for word in ["document", "documents", "proof", "paper"]):
        reply = "Documents commonly useful for this grievance: " + "; ".join(info["documents"]) + "."
    elif any(word in lower for word in ["when", "time", "deadline", "how long", "status", "update"]):
        lines = [f"{item['label']} — {item['date']}" for item in sla]
        reply = "Indicative prototype timeline: " + " | ".join(lines)
    elif any(word in lower for word in ["no response", "escalate", "ignored", "not solved", "not resolved"]):
        last = sla[-1]
        reply = (
            f"For this prototype, the next indicated escalation point is {last['label']} on {last['date']}. "
            f"Keep reference ID {row['id']} and verify the actual escalation process with the relevant authority."
        )
    elif any(word in lower for word in ["department", "where", "who"]):
        reply = (
            f"Your saved grievance is currently mapped to {row['department_label']}. "
            f"This is a prototype recommendation, not an official routing decision."
        )
    else:
        reply = (
            f"For reference #{row['id']}, your grievance is saved under {row['department_label']}. "
            "You can ask me about documents, timeline, escalation or the mapped department."
        )

    return jsonify({"reply": reply, "source": "rules"})


@app.get("/api/grievances/<ref_id>")
def get_grievance(ref_id):
    db = get_db()
    row = db.execute("SELECT * FROM grievances WHERE id=?", (ref_id,)).fetchone()
    if not row:
        return jsonify({"error": "Grievance not found."}), 404

    created = datetime.fromisoformat(row["created_at"])
    return jsonify({
        "ref_id": row["id"],
        "name": row["name"],
        "contact": row["contact"],
        "department_key": row["department_key"],
        "department_label": row["department_label"],
        "description": row["description"],
        "draft_text": row["draft_text"],
        "location": row["location"] or "",
        "created_at": created.strftime("%d %b %Y, %I:%M %p"),
        "status": row["status"] or "submitted",
        "status_label": build_status(row["status"] or "submitted"),
        "status_note": row["status_note"] or "",
        "updated_at": row["updated_at"] or row["created_at"],
        "sla": build_sla_dates(row["department_key"], created)
    })


# Initialize DB both for local execution and production WSGI servers.
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
