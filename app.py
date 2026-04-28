import streamlit as st
import pandas as pd
from detector import detect_issues, auto_fix_value
from scorer import calculate_score
from audit import create_audit_log

st.set_page_config(page_title="Data Quality Governance System", layout="wide")
st.title("Data Quality Governance System")

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    st.subheader("Raw Data Preview")
    st.dataframe(df)
    st.write(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")

    st.divider()

    issues = detect_issues(df)
    scores = calculate_score(df, issues)

    st.subheader("Data Quality Score")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Overall", f"{scores['overall']}/100")
    col2.metric("Completeness", f"{scores['completeness']}%")
    col3.metric("Consistency", f"{scores['consistency']}%")
    col4.metric("Accuracy", f"{scores['accuracy']}%")
    col5.metric("Uniqueness", f"{scores['uniqueness']}%")

    st.divider()

    st.subheader("Detected Issues")
    st.write(f"{len(issues)} issues found")

    if "decisions" not in st.session_state:
        st.session_state.decisions = {}

    for i, issue in enumerate(issues):
        with st.expander(f"{issue['issue_type']} — {issue['column']}"):

            # Show who detected it
            detected_by = issue.get("detected_by", "Unknown")
            if detected_by == "Pandas":
                st.info(f"🐼 Detected by: Pandas — scanned every row")
            else:
                st.success(f"🤖 Detected by: Claude AI — semantic understanding")

            st.write(f"**Affected rows:** {issue['affected_rows']}")

            # Show per-row fix status
            fix_details = []
            for j, orig in enumerate(issue['original_values']):
                fixed_value, can_fix = auto_fix_value(
                    issue['issue_type'],
                    issue['column'],
                    orig,
                    issue['suggested_fix']
                )
                if can_fix:
                    fix_details.append(f"`{orig}` → `{fixed_value}` ✅ auto fix")
                else:
                    fix_details.append(f"`{orig}` → ⚠️ manual review needed")

            st.write("**Fix details:**")
            for detail in fix_details:
                st.write(detail)

            st.write(f"**Confidence:** {int(issue['confidence'] * 100)}%")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve", key=f"approve_{i}"):
                    st.session_state.decisions[i] = "approved"
            with col2:
                if st.button("❌ Reject", key=f"reject_{i}"):
                    st.session_state.decisions[i] = "rejected"

            if i in st.session_state.decisions:
                st.success(f"Marked as: {st.session_state.decisions[i]}")

    st.divider()

    # Apply approved fixes row by row
    cleaned_df = df.copy()
    manual_review_rows = set()

    for i, issue in enumerate(issues):
        col = issue['column']
        rows = issue['affected_rows']
        decision = st.session_state.decisions.get(i)

        if decision == "approved":
            for j, row in enumerate(rows):
                if row < len(cleaned_df):
                    original_value = issue['original_values'][j] if j < len(issue['original_values']) else None
                    fixed_value, can_fix = auto_fix_value(
                        issue['issue_type'],
                        col,
                        original_value,
                        issue['suggested_fix']
                    )
                    if can_fix:
                        cleaned_df.at[row, col] = fixed_value
                    else:
                        manual_review_rows.add(row)

    # Add manual review flag column
    cleaned_df['needs_manual_review'] = ['YES' if i in manual_review_rows else '' for i in cleaned_df.index]

    st.subheader("Audit Trail")
    audit_log = create_audit_log(issues, st.session_state.decisions)
    audit_df = pd.DataFrame(audit_log)
    st.dataframe(audit_df)

    audit_csv = audit_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Audit Report",
        data=audit_csv,
        file_name="audit_report.csv",
        mime="text/csv"
    )

    cleaned_csv = cleaned_df.to_csv(index=False)
    st.download_button(
        label="⬇️ Download Cleaned CSV",
        data=cleaned_csv,
        file_name="cleaned_data.csv",
        mime="text/csv"
    )