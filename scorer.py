def calculate_score(df, issues):
    # Completeness — based on missing values in the dataframe
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = df.isnull().sum().sum()
    completeness = ((total_cells - missing_cells) / total_cells) * 100

    # Consistency — penalise for formatting and semantic issues
    consistency_issues = [i for i in issues if i["issue_type"] in ["Inconsistent Formatting", "Semantic Duplicate"]]
    consistency = max(0, 100 - (len(consistency_issues) * 10))

    # Accuracy — penalise for outliers and type mismatches
    accuracy_issues = [i for i in issues if i["issue_type"] in ["Outlier", "Type Mismatch"]]
    accuracy = max(0, 100 - (len(accuracy_issues) * 10))

    # Uniqueness — penalise for duplicates
    uniqueness_issues = [i for i in issues if i["issue_type"] == "Semantic Duplicate"]
    uniqueness = max(0, 100 - (len(uniqueness_issues) * 10))

    # Overall score
    overall = round((completeness + consistency + accuracy + uniqueness) / 4)

    return {
        "overall": overall,
        "completeness": round(completeness),
        "consistency": round(consistency),
        "accuracy": round(accuracy),
        "uniqueness": round(uniqueness)
    }