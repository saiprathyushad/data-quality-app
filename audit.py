from datetime import datetime

def create_audit_log(issues, decisions):
    log = []
    for i, issue in enumerate(issues):
        decision = decisions.get(i, "pending")
        log.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "issue_type": issue["issue_type"],
            "column": issue["column"],
            "affected_rows": str(issue["affected_rows"]),
            "original_values": str(issue["original_values"]),
            "suggested_fix": str(issue["suggested_fix"]),
            "confidence": f"{int(issue['confidence'] * 100)}%",
            "decision": decision
        })
    return log