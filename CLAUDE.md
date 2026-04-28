# Data Quality App

## What this is
Streamlit app to detect, score, and clean CSV data quality issues with human-in-the-loop validation.

## Stack
- Python, Pandas, Streamlit
- Claude API (connected at the end — mock data used during build)

## File structure
- app.py — main Streamlit app
- detector.py — issue detection logic (mock now, Claude API later)
- scorer.py — quality score calculation
- audit.py — audit trail logging

## Key rules
- Never apply fixes without user approval
- Every issue must have a confidence score (0.0 to 1.0)
- Store all state in st.session_state
- Mock detection returns same JSON schema as Claude will later