
# 🇮🇳 Saral Shikayat

### Don't know where to complain? Just describe your problem.

*Saral Shikayat* is a citizen-focused grievance assistant that helps people understand *which department is responsible for their problem, what information/documents they may need, how the complaint process works, and how to track their grievance afterward.*

Instead of forcing citizens to understand government departments and formal grievance terminology, Saral Shikayat lets them explain their problem in their own words.

---

## 🎯 Problem

Citizens often know *what is wrong*, but don't know:

* Which department is responsible
* Where they should submit the complaint
* What information or documents they need
* What happens after submitting it
* When they should follow up or escalate
* How to understand the grievance process

Existing grievance systems can require citizens to already understand the administrative structure before they can effectively use them.

---

## 💡 Solution

Saral Shikayat simplifies the journey:

text
Describe your problem
        ↓
Find the relevant department
        ↓
Understand why it was selected
        ↓
See required documents/information
        ↓
Generate a formal grievance
        ↓
Save a reference ID
        ↓
Track the complaint
        ↓
Ask the assistant about the grievance


The citizen does not need to know the correct government terminology beforehand.

---

## ✨ Key Features

### 🔎 Smart Department Identification

Describe your problem in natural language and Saral Shikayat recommends the most relevant department using a lightweight classification system.

### 📝 Grievance Drafting

The application converts a citizen's description into a structured formal grievance that can be edited and copied into the appropriate official portal.

### 📋 Document Checklist

Users can see the information and documents that are commonly useful for their type of complaint.

### ⏱️ Expected Process Timeline

The application provides an indicative timeline showing expected response and escalation milestones.

### 🆔 Complaint Reference ID

Saved grievances receive a unique reference ID so citizens can identify and follow up on them.

### 📊 Grievance Tracking

Citizens can revisit saved grievances and view their complaint information and expected escalation timeline.

### 💬 Grievance Assistant

Users can ask questions about their saved grievance, such as:

* When should I expect a response?
* What documents do I need?
* What happens if there is no response?
* How can I follow up?

The assistant is intentionally restricted to information available for that grievance instead of making unsupported promises.

### 📴 Graceful AI Fallback

AI-powered drafting and assistance can be enabled with an API key. The application also provides deterministic template/rule-based fallbacks so the core experience can continue working without an AI API.

---

## 🛠️ Technology

* *Backend:* Python + Flask
* *Database:* SQLite
* *Frontend:* HTML, CSS, JavaScript
* *UI:* Tailwind CSS
* *AI:* OpenAI API (optional)
* *Classification:* Rule-based department knowledge base with keyword scoring
* *Architecture:* REST-style Flask API + browser-based frontend

---

## 🏗️ Architecture

text
                 Citizen
                    │
                    ▼
          Natural-language problem
                    │
                    ▼
          Department Classifier
                    │
                    ▼
          Department Recommendation
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
      Documents   Timeline   Next Steps
          │         │          │
          └─────────┼──────────┘
                    ▼
            Grievance Draft
                    │
                    ▼
             Save Complaint
                    │
                    ▼
              Reference ID
                    │
                    ▼
              Track Grievance
                    │
                    ▼
             Citizen Assistant


---

## 🚀 Running Locally

### 1. Clone the repository

bash
git clone https://github.com/devanshrai1300-wq/Saral-Shikayat.git
cd Saral-Shikayat


### 2. Install dependencies

bash
pip install -r requirements.txt


### 3. Optional: Configure OpenAI

The application works without an OpenAI API key using its built-in fallback system.

If you want AI-assisted drafting and grievance chat:

bash
export OPENAI_API_KEY="your_api_key"


On Windows:

powershell
$env:OPENAI_API_KEY="your_api_key"


You may also configure the model:

bash
export OPENAI_MODEL="gpt-4o-mini"


### 4. Start the application

bash
python app.py


Open:

text
http://localhost:5000


---

## 📁 Project Structure

text
Saral-Shikayat/
│
├── app.py
├── grievances.db
├── requirements.txt
├── README.md
├── LICENSE
│
└── templates/
    └── index.html


---

## 🔐 Privacy & Security

This project is a prototype and should *not be treated as a production government grievance system*.

The current prototype uses local SQLite storage and does not implement production-grade citizen authentication, authorization, encryption, or government-system integration.

Do not use real sensitive personal information when testing the public demo.

---

## ⚠️ Important Disclaimer

*Saral Shikayat is an independent prototype and is not an official government website or government service.*

The department information, timelines, workflows and other data used by the prototype may be simulated or indicative and should be verified against the relevant official authority before submitting a real grievance.

Saral Shikayat does not claim government endorsement, approval or partnership.

---

## 🔮 Future Improvements

Potential future versions could include:

* Location-based department routing
* State/city-specific grievance authorities
* Official portal and helpline directories
* Secure citizen authentication
* SMS/email notifications
* Photo and document attachments
* Real-time complaint status updates through authorized integrations
* Multilingual support
* Voice-based complaint submission
* Accessibility improvements
* Human escalation and support workflows
* Analytics for departments and administrators

---

## 🤝 Why Saral Shikayat?

The goal is simple:

> *Citizens shouldn't need to understand the government system before they can ask the government for help.*

Saral Shikayat turns a confusing administrative journey into a simple citizen journey:

*Explain → Find → Prepare → Submit → Track*

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.