import os

DEPARTMENTS = {
    "epfo": {
        "label": "EPFO (Employees' Provident Fund Organisation)",
        "keywords": ["pf", "provident fund", "epfo", "uan", "pf withdrawal", "pf claim", "pension fund", "eps"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from EPFO officer", 15),
            ("Escalate to Regional PF Commissioner if unresolved", 30),
            ("Escalate to CPGRAMS nodal officer", 45),
        ],
        "documents": ["UAN number", "PF account number / member ID", "Account linked to UAN", "Bank passbook copy", "Reason for rejection (if reapplying)"],
    },
    "income_tax": {
        "label": "Income Tax Department",
        "keywords": ["income tax", "itr", "tax refund", "pan", "assessing officer", "tds", "form 26as", "notice under section"],
        "sla": [
            ("Acknowledgement generated", 2),
            ("First response from CPC/AO", 21),
            ("Escalate to Grievance Cell (CPGRAMS)", 30),
            ("Escalate to Ombudsman", 60),
        ],
        "documents": ["PAN number", "Assessment year", "ITR acknowledgement number", "Notice/order reference number (if any)", "Form 26AS copy"],
    },
    "railways": {
        "label": "Railways / IRCTC",
        "keywords": ["irctc", "pnr", "train", "railway", "ticket refund", "tatkal", "railways"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from IRCTC/Zonal Railway", 7),
            ("Escalate to Railway Board", 15),
        ],
        "documents": ["PNR number", "Transaction ID / UTR", "Journey date", "Screenshot of refund status (if available)"],
    },
    "passport": {
        "label": "Passport Seva (Ministry of External Affairs)",
        "keywords": ["passport", "passport seva", "psk", "arn number"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from Passport Seva Kendra", 10),
            ("Escalate to Regional Passport Officer", 21),
        ],
        "documents": ["Application Reference Number (ARN/File number)", "Appointment date", "Police verification status (if applicable)"],
    },
    "aadhaar": {
        "label": "UIDAI (Aadhaar)",
        "keywords": ["aadhaar", "uidai", "aadhar", "enrolment id", "eid"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from UIDAI Regional Office", 10),
            ("Escalate to UIDAI HQ Grievance Cell", 20),
        ],
        "documents": ["Enrolment ID (EID) / Reference number", "Update Request Number (URN, if any)", "Proof of identity/address used"],
    },
    "pension": {
        "label": "Pension (CPAO / State Pension Directorate)",
        "keywords": ["pension", "pensioner", "ppo", "cpao", "family pension"],
        "sla": [
            ("Acknowledgement generated", 2),
            ("First response from CPAO/PDA", 21),
            ("Escalate to Department of Pension & Pensioners' Welfare", 45),
        ],
        "documents": ["PPO number", "Bank account & branch details", "Retirement order copy", "Life certificate status"],
    },
    "municipal": {
        "label": "Municipal / Local Body (property tax, water, sanitation)",
        "keywords": ["municipal", "property tax", "water supply", "garbage", "sanitation", "corporation", "nagar nigam", "gram panchayat"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from ward officer", 7),
            ("Escalate to Municipal Commissioner", 15),
        ],
        "documents": ["Property/ward number", "Complaint area photos (if applicable)", "Previous complaint number (if any)"],
    },
    "electricity": {
        "label": "Electricity / Power Utility",
        "keywords": ["electricity", "power cut", "discom", "electricity bill", "transformer", "meter reading"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from local sub-division office", 3),
            ("Escalate to Consumer Grievance Redressal Forum", 10),
        ],
        "documents": ["Consumer account number", "Meter number", "Last bill copy"],
    },
    "banking": {
        "label": "Banking (RBI Ombudsman route)",
        "keywords": ["bank account", "atm", "neft", "upi", "loan", "bank", "cheque bounce", "credit card"],
        "sla": [
            ("Bank's internal grievance response", 30),
            ("Escalate to Banking Ombudsman (RBI) if unresolved", 30),
        ],
        "documents": ["Account/loan/card number", "Transaction reference number", "Bank's complaint reference (if already raised)"],
    },
    "police": {
        "label": "Police / Law & Order",
        "keywords": ["police", "fir", "theft", "complaint against police", "law and order"],
        "sla": [
            ("Acknowledgement generated", 1),
            ("First response from Station House Officer", 7),
            ("Escalate to Superintendent of Police / DCP", 15),
        ],
        "documents": ["FIR number (if filed)", "Police station name", "Incident date and location"],
    },
    "other": {
        "label": "General Public Grievance (CPGRAMS)",
        "keywords": [],
        "sla": [
            ("Acknowledgement generated", 3),
            ("First response from nodal department", 21),
            ("Escalate to DARPG (CPGRAMS)", 30),
        ],
        "documents": ["Any reference/application number related to your issue", "Relevant dates", "Any prior correspondence"],
    },
}