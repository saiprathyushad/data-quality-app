import anthropic
import json
import os
import pandas as pd
from dotenv import load_dotenv
from dateutil import parser as date_parser

load_dotenv()

def auto_fix_value(issue_type, column, original_value, suggested_fix):
    if original_value is None:
        return None, False

    str_value = str(original_value).strip()

    # Auto-fix currency symbols — '300$' or '$300' → 300
    if issue_type == "Inconsistent Formatting":
        cleaned = str_value.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned), True
        except ValueError:
            pass

    # Auto-fix capitalization — 'sports' → 'Sports'
    if issue_type == "Inconsistent Formatting":
        if str_value.isalpha() and not str_value.istitle():
            return str_value.title(), True

    # Auto-fix dates
    if issue_type == "Inconsistent Formatting" and "date" in column.lower():
        try:
            parsed = date_parser.parse(str_value)
            return parsed.strftime("%m/%d/%Y"), True
        except Exception:
            pass

    # Auto-fix semantic duplicates
    if issue_type == "Semantic Duplicate" and suggested_fix:
        return suggested_fix, True

    # Auto-fix written numbers — 'four hundred' → 400
    word_to_num = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
        'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
        'ten': 10, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
        'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
        'hundred': 100, 'thousand': 1000
    }
    words = str_value.lower().split()
    if all(w in word_to_num for w in words):
        total = 0
        current = 0
        for word in words:
            num = word_to_num[word]
            if num == 100:
                current *= 100
            elif num == 1000:
                total += current * 1000
                current = 0
            else:
                current += num
        return float(total + current), True

    return None, False


def pandas_detect(df):
    issues = []

    # Missing values — Pandas scans every row
    for col in df.columns:
        missing_rows = df[df[col].isnull()].index.tolist()
        if missing_rows:
            issues.append({
                "issue_type": "Missing Value",
                "column": col,
                "affected_rows": missing_rows,
                "original_values": [None] * len(missing_rows),
                "suggested_fix": None,
                "confidence": 1.0,
                "detected_by": "Pandas"
            })

    # Type mismatches — Pandas checks columns that look numeric
    for col in df.columns:
        if df[col].dtype == object:
            numeric_converted = pd.to_numeric(df[col], errors='coerce')
            numeric_ratio = numeric_converted.notnull().sum() / df[col].notnull().sum()
            if numeric_ratio > 0.5:
                bad_rows = df[df[col].notnull() & numeric_converted.isnull()].index.tolist()
                if bad_rows:
                    issues.append({
                        "issue_type": "Type Mismatch",
                        "column": col,
                        "affected_rows": bad_rows[:10],
                        "original_values": df[col].iloc[bad_rows[:10]].tolist(),
                        "suggested_fix": None,
                        "confidence": 0.9,
                        "detected_by": "Pandas"
                    })

    # Outliers — Pandas uses IQR method
    for col in df.columns:
        if df[col].dtype == object:
            converted = pd.to_numeric(df[col], errors='coerce')
            numeric_ratio = converted.notnull().sum() / df[col].notnull().sum()
            if numeric_ratio > 0.5:
                Q1 = converted.quantile(0.25)
                Q3 = converted.quantile(0.75)
                IQR = Q3 - Q1
                outlier_mask = (converted < Q1 - 1.5 * IQR) | (converted > Q3 + 1.5 * IQR)
                outlier_rows = df[outlier_mask].index.tolist()
                if outlier_rows:
                    issues.append({
                        "issue_type": "Outlier",
                        "column": col,
                        "affected_rows": outlier_rows[:10],
                        "original_values": converted[outlier_mask].tolist()[:10],
                        "suggested_fix": None,
                        "confidence": 0.85,
                        "detected_by": "Pandas"
                    })
        elif df[col].dtype in ['int64', 'float64']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outlier_mask = (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)
            outlier_rows = df[outlier_mask].index.tolist()
            if outlier_rows:
                issues.append({
                    "issue_type": "Outlier",
                    "column": col,
                    "affected_rows": outlier_rows[:10],
                    "original_values": df[col][outlier_mask].tolist()[:10],
                    "suggested_fix": None,
                    "confidence": 0.85,
                    "detected_by": "Pandas"
                })

    return issues


def claude_detect(df):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    if len(df) > 500:
        sample = df.sample(100).to_string()
    else:
        sample = df.to_string()

    columns = df.dtypes.to_string()

    prompt = f"""You are a data quality expert. Analyse this CSV dataset and detect data quality issues that are hard to detect programmatically.

Focus ONLY on:
- Semantic duplicates (e.g. "NY" and "New York" meaning the same thing)
- Inconsistent formatting (e.g. dates in different formats, phone number formats, currency symbols inside numeric columns like "300$" or "$300")
- Values that are contextually wrong (e.g. negative quantities, impossible dates)

Do NOT flag missing values or outliers — those are already handled separately.

Column types:
{columns}

Sample data:
{sample}

Return a JSON array of issues found. Each issue must follow this exact schema:
{{
    "issue_type": "one of: Semantic Duplicate, Inconsistent Formatting, Contextually Wrong",
    "column": "column name",
    "affected_rows": [list of row numbers],
    "original_values": [list of the actual bad values],
    "suggested_fix": "the exact corrected value as a string, or null if no fix possible",
    "confidence": 0.0 to 1.0
}}

Rules:
- Return ONLY a valid JSON array, no explanation, no markdown, no extra text
- If no issues found, return an empty array []
- Maximum 10 issues
- Only flag real issues you are confident about
- For suggested_fix, provide the exact corrected value, not an instruction
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = message.content[0].text
    print("Claude raw response:", response_text)

    try:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        issues = json.loads(cleaned.strip())

        # Add detected_by field to every Claude issue
        for issue in issues:
            issue["detected_by"] = "Claude AI"

        return issues
    except json.JSONDecodeError:
        print("JSON parsing failed")
        return []


def detect_issues(df):
    pandas_issues = pandas_detect(df)
    claude_issues = claude_detect(df)
    return pandas_issues + claude_issues