ReadMe Summary: A robust PDF-to-ANSI 835 conversion engine aligned with the CMS 835 TR3 5010A1 specification. It prioritizes all Required (R) segments while dynamically mapping Situational (S) segments—such as MIA (Inpatient) or MOA (Outpatient)—whenever data is present.

Validation Process:
Includes a built-in reconciliation engine to verify Check Amount = Σ(Claim Payments) + Adjustments before 835 generation.

All Amount Fields are right-justified, zero-filled for the first 10 positions, and space-filled for the remaining positions per CMS guidelines

ReadMe Note: This module includes a Fault-Tolerant Parsing Layer. In real-world RCM, EOBs are often poorly scanned or contain non-standard formatting. This engine uses proactive error handling to isolate malformed records, ensuring the entire batch doesn't fail due to a single unreadable claim
