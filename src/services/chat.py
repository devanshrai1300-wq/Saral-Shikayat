import os
from datetime import datetime
from src.config import DEPARTMENTS
from src.services.classifier import build_sla_dates

try:
    from openai import OpenAI  # type: ignore
    _openai_available = True
except ImportError:
    _openai_available = False
    OpenAI = None  # type: ignore

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
    for turn in history[-6:]:
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