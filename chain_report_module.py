import pandas as pd
import os
import re


def generate_chain_report():
    files = [f for f in os.listdir('.') if f.endswith('.csv') and 'Chain Report' in f]
    if not files:
        print("No Chain Report CSV file found.")
        return

    df = pd.read_csv(files[0], sep=';', skiprows=1)
    df.columns = [
        "Member", "Respect", "Best", "Avg", "Attacks", "Leave", "Mug",
        "Hosp", "War", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"
    ]

    for col in df.columns[1:]:
        df[col] = df[col].astype(str).str.replace(',', '').astype(float)

    df["Outside"] = df["Attacks"] - df["War"]

    percent_cols = ["Leave", "Mug", "Hosp", "War", "Outside", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"]

    def format_value_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        formatted_value = f'<div data-sort="{value_int}">{value_int}<div style="font-size: 10px; color: #aaa">{percent:.2f}%</div></div>'
        #print(f"Value INT: {value_int}, TYPE: {type(value_int)} -> {formatted_value}")
        return formatted_value

    for col in percent_cols:
        df[col] = [format_value_with_percent(v, total) for v, total in zip(df[col], df["Attacks"])]

    print(df.head())
    df = df.sort_values("Respect", ascending=False)

    def euro_float(x):
        if pd.isna(x):
            return ""
        return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def format_member(cell):
        match = re.search(r'\[(\d+)]', cell)
        if match:
            torn_id = match.group(1)
            name = re.sub(r'\[\d+]', '', cell).strip()
            name = name[:len(name)//2]
            return f'<a href="https://www.torn.com/profiles.php?XID={torn_id}" target="_blank" style="color:#67e8f9;text-decoration:none">{name}</a>'
        return cell

    df["Member"] = df["Member"].apply(format_member)

    # make Respect column into integers
    df.to_excel("chain_report.xlsx", index=False)
    df["Respect"] = df["Respect"].apply(lambda x: f"{int(round(x)):,}".replace(",", "."))
    df["Attacks"] = df["Attacks"].apply(lambda x: f"{int(round(x)):,}".replace(",", "."))
    df["Best"] = df["Best"].apply(euro_float)
    df["Avg"] = df["Avg"].apply(euro_float)


    new_cols = ['Member', 'Respect', 'Best', 'Avg', 'Attacks', 'War', 'Outside', 'Hosp', 'Mug', 'Retal', 'Overseas', 'Draw', 'Assist', 'Escape', 'Loss', 'Leave']
    df = df[new_cols]

    html_table = df.to_html(index=False, escape=False, classes='war_report', border=0)

    try:
        with open("chain_report_template.html", "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print("❌ chain_report_template.html not found. Using fallback styling.")
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <title>Chain Report</title>
</head>
<body>
    <h1>Chain Report</h1>
    {{TABLE_HTML}}
</body>
</html>
"""

    final_html = template.replace("{{CHAIN_TABLE}}", html_table)

    with open("chain_report.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    print("✅ Chain report saved to 'chain_report.html'")
