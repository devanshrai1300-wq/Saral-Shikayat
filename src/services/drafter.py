import os
import re

try:
    from openai import OpenAI  # type: ignore[import-not-found]
    _openai_available = True
except ImportError:
    OpenAI = None  # type: ignore[assignment]
    _openai_available = False

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
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        max_tokens=400,
    )
    return resp.choices[0].message.content.strip()

def draft_with_template(name, contact, department_label, description):
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
            pass
    return draft_with_template(name, contact, department_label, description), "template"