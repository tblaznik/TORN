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

    # Convert numbers properly handling European formatting
    # For most columns, comma is decimal separator, but for integer columns like Respect/Attacks, comma might be thousands separator
    def convert_european_number(value_str):
        value_str = str(value_str).strip()
        if not value_str or value_str == 'nan':
            return 0.0
        
        # If it has a comma and no decimal point, it's likely a thousands separator
        if ',' in value_str and '.' not in value_str:
            # This is European thousands separator (e.g., "2,368" = 2368)
            return float(value_str.replace(',', ''))
        elif ',' in value_str and '.' in value_str:
            # This has both comma and period - European style with thousands and decimals (e.g., "1.234,56")
            return float(value_str.replace('.', '').replace(',', '.'))
        elif ',' in value_str:
            # Only comma, treat as decimal separator (e.g., "26,17" = 26.17)
            return float(value_str.replace(',', '.'))
        else:
            # No comma, standard format
            return float(value_str)

    # Convert columns with proper European number handling
    for col in df.columns[1:]:
        df[col] = df[col].apply(convert_european_number)

    df["Outside"] = df["Attacks"] - df["War"]

    percent_cols = ["Leave", "Mug", "Hosp", "War", "Outside", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"]

    # Calculate totals BEFORE applying percentage formatting
    total_respect = df["Respect"].sum()
    total_attacks = df["Attacks"].sum()
    total_best = df["Best"].max()  # Best chain bonus is the maximum
    avg_respect = df["Respect"].mean()  # Average respect per member
    
    # Store raw totals for percentage columns
    raw_totals = {}
    for col in percent_cols:
        raw_totals[col] = df[col].sum()

    def format_value_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        formatted_value = f'<div data-sort="{value_int}">{value_int}<div style="font-size: 10px; color: #aaa">{percent:.2f}%</div></div>'
        return formatted_value

    # Apply formatting to percentage columns
    for col in percent_cols:
        df[col] = [format_value_with_percent(v, total) for v, total in zip(df[col], df["Attacks"])]

    print(df.head())
    df = df.sort_values("Respect", ascending=False)

    def format_number(x):
        """Format numbers with American standard: comma as thousands separator, period as decimal"""
        if pd.isna(x):
            return ""
        return f"{x:,.2f}"

    def format_member(cell):
        match = re.search(r'\[(\d+)]', cell)
        if match:
            torn_id = match.group(1)
            name = re.sub(r'\[\d+]', '', cell).strip()
            name = name[:len(name)//2]
            return f'<a href="https://www.torn.com/profiles.php?XID={torn_id}" target="_blank" style="color:#67e8f9;text-decoration:none">{name}</a>'
        return cell

    df["Member"] = df["Member"].apply(format_member)

    # Save to Excel first, then format for display
    df.to_excel("chain_report.xlsx", index=False)
    
    # Format numbers for display using American formatting
    df["Respect"] = df["Respect"].apply(lambda x: f"{int(round(x)):,}")
    df["Attacks"] = df["Attacks"].apply(lambda x: f"{int(round(x)):,}")
    df["Best"] = df["Best"].apply(format_number)
    df["Avg"] = df["Avg"].apply(format_number)

    new_cols = ['Member', 'Respect', 'Best', 'Avg', 'Attacks', 'War', 'Outside', 'Leave', 'Hosp', 'Mug', 'Retal', 'Overseas', 'Draw', 'Assist', 'Escape', 'Loss']
    df = df[new_cols]

    # Create totals row with proper formatting
    def format_total_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        return f'<div data-sort="{value_int}"><strong>{value_int}</strong><div style="font-size: 10px; color: #aaa"><strong>{percent:.2f}%</strong></div></div>'

    totals_row = {
        'Member': '<strong>TOTALS</strong>',
        'Respect': f'<strong>{int(round(total_respect)):,}</strong>',
        'Best': f'<strong>{format_number(total_best)}</strong>',
        'Avg': f'<strong>{format_number(avg_respect)}</strong>',
        'Attacks': f'<strong>{int(round(total_attacks)):,}</strong>',
        'War': format_total_with_percent(raw_totals['War'], total_attacks),
        'Outside': format_total_with_percent(raw_totals['Outside'], total_attacks),
        'Leave': format_total_with_percent(raw_totals['Leave'], total_attacks),
        'Hosp': format_total_with_percent(raw_totals['Hosp'], total_attacks),
        'Mug': format_total_with_percent(raw_totals['Mug'], total_attacks),
        'Retal': format_total_with_percent(raw_totals['Retal'], total_attacks),
        'Overseas': format_total_with_percent(raw_totals['Overseas'], total_attacks),
        'Draw': format_total_with_percent(raw_totals['Draw'], total_attacks),
        'Assist': format_total_with_percent(raw_totals['Assist'], total_attacks),
        'Escape': format_total_with_percent(raw_totals['Escape'], total_attacks),
        'Loss': format_total_with_percent(raw_totals['Loss'], total_attacks)
    }

    html_table = df.to_html(index=False, escape=False, classes='war_report', border=0)
    
    # Insert totals row as a second header after the main header
    header_end = html_table.find('</thead>')
    if header_end != -1:
        # Create the totals header row with the same structure as data rows but styled as header
        totals_header = '<tr class="totals-row">'
        for col in new_cols:
            totals_header += f'<th class="totals-cell">{totals_row[col]}</th>'
        totals_header += '</tr>'
        
        # Insert before </thead>
        html_table = html_table[:header_end] + totals_header + html_table[header_end:]

    try:
        with open("chain_report_template.html", "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print("❌ chain_report_template.html not found. Using fallback styling.")
        template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chain Report</title>
</head>
<body>
    <h1>Chain Report</h1>
    {{CHAIN_TABLE}}
</body>
</html>
"""

    final_html = template.replace("{{CHAIN_TABLE}}", html_table)

    with open("chain_report.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    print("✅ Chain report saved to 'chain_report.html'")
