"""Deterministic Local HR Policy RAG Engine simulating Vertex AI Search with Layout Parser."""
from typing import Any

POLICY_DOCUMENTS: list[dict[str, Any]] = [
    {
        "doc_id": "POL-LEAVE-001",
        "title": "Global Leave & Time-Off Policy v4.2",
        "section": "Section 4.2: Bereavement Leave",
        "url": "https://hr-policies.corp.internal/docs/Leave_Policy_v4.2.pdf#page=12",
        "keywords": ["bereavement", "funeral", "death", "family member", "compassionate leave", "忌引"],
        "content": (
            "Employees are eligible for up to 5 consecutive paid business days of Bereavement Leave "
            "in the event of the loss of an immediate family member (spouse, domestic partner, child, parent, sibling). "
            "For extended family members, up to 3 paid business days are provided. "
            "Requests must be submitted in WorkWeek under the 'Bereavement' or 'Vacation/PTO' category with manager notification."
        ),
    },
    {
        "doc_id": "POL-LEAVE-002",
        "title": "Global Leave & Time-Off Policy v4.2",
        "section": "Section 6.1: Short-Term Medical Leave (STD)",
        "url": "https://hr-policies.corp.internal/docs/Leave_Policy_v4.2.pdf#page=18",
        "keywords": ["medical leave", "short-term", "sick", "illness", "surgery", "hospital", "doctor", "傷病休暇"],
        "content": (
            "Short-Term Medical Leave provides 100% base salary continuation for up to 12 weeks for qualifying medical conditions. "
            "Procedure: (1) Submit a Leave of Absence request in WorkWeek specifying start and end dates under 'Sick/Medical' leave. "
            "(2) Open an IT ServiceImmediately ticket under category 'IT_Access_Delegation' to route urgent incoming employee emails "
            "and calendar delegations to your direct manager during your absence. "
            "(3) Provide medical certification within 15 calendar days if absence exceeds 5 consecutive business days."
        ),
    },
    {
        "doc_id": "POL-EXP-001",
        "title": "Global Employee Expense & Reimbursement Guidelines v3.0",
        "section": "Section 3.4: Home Office Peripherals & Headphones",
        "url": "https://hr-policies.corp.internal/docs/Expense_Guidelines_v3.0.pdf#page=8",
        "keywords": ["expense", "headphones", "noise-canceling", "noise cancelling", "reimbursement", "headset", "audio", "経費"],
        "content": (
            "Employees are allowed to expense noise-canceling headphones up to a maximum reimbursement limit of USD 250.00 "
            "once every 24 months, provided they are used for business communications and virtual meetings. "
            "Purchases exceeding USD 250 require prior VP approval. Receipts must be itemized and submitted via the expense portal."
        ),
    },
    {
        "doc_id": "POL-REM-001",
        "title": "Hybrid & Remote Work Equipment Policy v2.1",
        "section": "Section 2.2: Home Office Monitor & Hardware Eligibility",
        "url": "https://hr-policies.corp.internal/docs/Remote_Work_Policy_v2.1.pdf#page=5",
        "keywords": ["remote work", "monitor", "display", "screen", "home office", "equipment", "hardware", "eligible", "リモートワーク"],
        "content": (
            "Employees whose official WorkWeek profile status is designated as 'Approved Remote' or 'Hybrid (>=3 days remote)' "
            "are eligible to order one standard 27-inch 4K ergonomic monitor (Catalog Item: STD-MON-27INCH) at company expense. "
            "Fulfillment Process: Verify 'Approved Remote' status in WorkWeek, then create a hardware procurement ticket in "
            "ServiceImmediately (Category: 'Hardware_Procurement', Priority: '3 - Moderate') including confirmed shipping address."
        ),
    },
    {
        "doc_id": "POL-REL-001",
        "title": "Global Mobility & Office Transfer Policy v5.0",
        "section": "Section 5.1: International Relocation Allowance & UK London Transfer",
        "url": "https://hr-policies.corp.internal/docs/Relocation_Policy_v5.0.pdf#page=22",
        "keywords": ["relocation", "transfer", "london", "allowance", "moving", "uk office", "building access", "badge", "転勤"],
        "content": (
            "Employees transferring internationally to the London HQ Office (Building Code: LON-HQ-BLDG1) are entitled to a lump-sum "
            "Relocation Allowance of USD 10,000 (or GBP equivalent) to cover shipping, temporary housing, and settling-in costs. "
            "Mandatory Checklist: (1) Update your residential address and phone number in WorkWeek prior to transfer date. "
            "(2) Submit a Facilities Security ticket in ServiceImmediately (Category: 'Facilities_Badge_Access', Priority: '3 - Moderate') "
            "specifying Building 'LON-HQ-BLDG1' and transfer effective date to provision physical building access."
        ),
    },
    {
        "doc_id": "POL-COC-001",
        "title": "Corporate Code of Conduct & AI Usage Policy v1.4",
        "section": "Section 1.1: Data Privacy & Zero-Trust Confidentiality",
        "url": "https://hr-policies.corp.internal/docs/Code_of_Conduct_v1.4.pdf#page=3",
        "keywords": ["code of conduct", "privacy", "confidentiality", "security", "rbac", "行动規範"],
        "content": (
            "All employees must adhere to strict Role-Based Access Control (RBAC). Accessing, querying, or attempting to modify "
            "another employee's personal HR profile, salary, or leave records is strictly prohibited and logged as a security incident."
        ),
    },
]


def search_policy_documents(query: str, category_filter: str | None = None) -> dict[str, Any]:
    """Searches approved HR policy documents and returns grounded chunks with citation URLs and grounding score."""
    q_lower = query.lower()

    # Explicit unapproved policy topics (FR-5.4 Strict Refusal)
    unapproved_topics = ["pet insurance", "veterinary", "for dogs", "for cats", "crypto reimbursement"]
    if any(ut in q_lower for ut in unapproved_topics):
        return {
            "status": "NO_RELEVANT_POLICY_FOUND",
            "grounding_score": 0.12,
            "chunks": [],
            "guardrail_instruction": (
                "STRICT GROUNDING MANDATE (FR-5.4): Grounding score (0.12) is below threshold (0.75). "
                "You MUST refuse to answer or speculate. State clearly that the requested topic is not covered in approved HR policies."
            ),
        }

    stop_words = {"policy", "policies", "section", "benefit", "benefits", "corporate", "employee", "global", "guidelines", "work"}
    matched_chunks = []

    for doc in POLICY_DOCUMENTS:
        score = 0.0
        for kw in doc["keywords"]:
            if kw in q_lower:
                score += 0.35
        # Check specific domain word match excluding generic stop words
        if any(
            word in doc["title"].lower() or word in doc["section"].lower()
            for word in q_lower.split()
            if len(word) > 3 and word not in stop_words
        ):
            score += 0.25

        if score > 0:
            capped_score = min(0.98, round(0.55 + score, 2))
            matched_chunks.append({
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "section": doc["section"],
                "citation_url": doc["url"],
                "citation_markdown": f"[{doc['title']} - {doc['section']}]({doc['url']})",
                "content": doc["content"],
                "grounding_score": capped_score,
            })

    matched_chunks.sort(key=lambda x: x["grounding_score"], reverse=True)

    if not matched_chunks:
        return {
            "status": "NO_RELEVANT_POLICY_FOUND",
            "grounding_score": 0.12,
            "chunks": [],
            "guardrail_instruction": (
                "STRICT GROUNDING MANDATE (FR-5.4): Grounding score (0.12) is below threshold (0.75). "
                "You MUST refuse to answer or speculate. State clearly that the requested topic is not covered in approved HR policies."
            ),
        }

    top_score = matched_chunks[0]["grounding_score"]
    return {
        "status": "SUCCESS",
        "grounding_score": top_score,
        "chunks": matched_chunks[:3],
        "guardrail_instruction": (
            "MANDATORY CITATION RULE (FR-5.3): You MUST cite the exact `citation_markdown` link in your response."
        ),
    }
