import pandas as pd
import re


def format_number_american(num):
    """Format numbers with American standards: comma as thousands separator, period as decimal"""
    if isinstance(num, (int, float)):
        return f"{num:,.2f}"
    return str(num)


def format_member_link(cell):
    """Format member names with Torn profile links"""
    match = re.search(r'\[(\d+)]', cell)
    if match:
        torn_id = match.group(1)
        name = re.sub(r'\[\d+]', '', cell).strip()
        # Handle duplicated names like "JlambJLAMB" -> "Jlamb"
        name = name[:len(name)//2] if len(name) > 15 else name
        return f'<a href="https://www.torn.com/profiles.php?XID={torn_id}" target="_blank" style="color:#67e8f9;text-decoration:none">{name}</a>'
    return cell


def format_value_with_percent(value, total):
    """Format value with percentage for sortable columns"""
    value_int = int(round(value))
    percent = (value / total * 100) if total > 0 else 0.0
    formatted_value = f'<div data-sort="{value_int}">{value_int:,}<div style="font-size: 10px; color: #aaa">{percent:.2f}%</div></div>'
    return formatted_value


def prepare_chain_display_data(complete_chain_data):
    """Prepare chain data for display with proper formatting"""
    
    # Work with a copy to avoid modifying original data
    df = complete_chain_data.copy()
    
    # Calculate totals BEFORE applying percentage formatting - use War_Respect for calculations
    total_respect = df["War_Respect"].sum()  # Use war respect for totals
    total_attacks = df["Attacks"].sum()
    total_best = df["Best"].max()  # Best chain bonus is the maximum
    avg_respect = df["War_Respect"].mean()  # Average war respect per member
    
    # Store raw totals for percentage columns
    percent_cols = ["Leave", "Mug", "Hosp", "War", "Outside", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"]
    raw_totals = {}
    for col in percent_cols:
        raw_totals[col] = df[col].sum()

    # Store raw values for each row BEFORE formatting
    raw_war_attacks = df["War"].copy()
    raw_total_attacks = df["Attacks"].copy()

    # Apply formatting to percentage columns using raw values for calculations
    for i in range(len(df)):
        for col in percent_cols:
            value = df.iloc[i][col]  # Get the raw numeric value
            
            if col == 'Outside':
                # Outside uses total attacks as denominator
                total = raw_total_attacks.iloc[i]
            elif col == 'War':
                # War uses total attacks as denominator  
                total = raw_total_attacks.iloc[i]
            else:
                # All other columns use war attacks as denominator
                total = raw_war_attacks.iloc[i]
            
            # Apply the formatting
            df.at[i, col] = format_value_with_percent(value, total)

    # Sort by war respect
    df = df.sort_values("War_Respect", ascending=False)

    # Format member names with links
    df["Member"] = df["Member"].apply(format_member_link)

    # Format numbers for display using American formatting
    df["Respect"] = df["War_Respect"].apply(lambda x: f"{int(round(x)):,}")  # Use war respect for display
    df["Attacks"] = df["Attacks"].apply(lambda x: f"{int(round(x)):,}")
    df["Best"] = df["Best"].apply(format_number_american)
    df["Avg"] = df["Avg"].apply(format_number_american)
    df["Saves"] = df["Saves"].apply(lambda x: f"{int(round(x)):,}")  # Format saves as integer
    df["Save_Score"] = df["Save_Score"].apply(format_number_american)  # Format save score with decimals

    # Select columns for display - include saves data that was merged in main.py
    new_cols = ['Member', 'Respect', 'Best', 'Avg', 'Attacks', 'War', 'Outside', 'Saves', 'Save_Score', 'Leave', 'Hosp', 'Mug', 'Retal', 'Overseas', 'Draw', 'Assist', 'Escape', 'Loss']
    df = df[new_cols]

    return df, total_respect, total_attacks, total_best, avg_respect, raw_totals


def create_totals_row(total_respect, total_attacks, total_best, avg_respect, raw_totals, complete_chain_data):
    """Create the totals row for the table"""
    
    def format_total_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        return f'<div data-sort="{value_int}"><strong>{value_int:,}</strong><div style="font-size: 10px; color: #aaa"><strong>{percent:.2f}%</strong></div></div>'

    # Calculate war attacks (excluding outside attacks)
    total_war_attacks = raw_totals['War']
    
    # Calculate saves totals
    total_saves = complete_chain_data['Saves'].sum()
    total_save_score = complete_chain_data['Save_Score'].sum()

    totals_row = {
        'Member': '<strong>TOTALS</strong>',
        'Respect': f'<strong>{int(round(total_respect)):,}</strong>',
        'Best': f'<strong>{format_number_american(total_best)}</strong>',
        'Avg': f'<strong>{format_number_american(avg_respect)}</strong>',
        'Attacks': f'<strong>{int(round(total_attacks)):,}</strong>',
        'War': format_total_with_percent(raw_totals['War'], total_attacks),  # War vs total attacks
        'Outside': format_total_with_percent(raw_totals['Outside'], total_attacks),  # Outside vs total attacks
        'Saves': f'<strong>{int(round(total_saves)):,}</strong>',
        'Save_Score': f'<strong>{format_number_american(total_save_score)}</strong>',
        'Leave': format_total_with_percent(raw_totals['Leave'], total_war_attacks),  # Leave vs war attacks
        'Hosp': format_total_with_percent(raw_totals['Hosp'], total_war_attacks),  # Hosp vs war attacks
        'Mug': format_total_with_percent(raw_totals['Mug'], total_war_attacks),  # Mug vs war attacks
        'Retal': format_total_with_percent(raw_totals['Retal'], total_war_attacks),  # Retal vs war attacks
        'Overseas': format_total_with_percent(raw_totals['Overseas'], total_war_attacks),  # Overseas vs war attacks
        'Draw': format_total_with_percent(raw_totals['Draw'], total_war_attacks),  # Draw vs war attacks
        'Assist': format_total_with_percent(raw_totals['Assist'], total_war_attacks),  # Assist vs war attacks
        'Escape': format_total_with_percent(raw_totals['Escape'], total_war_attacks),  # Escape vs war attacks
        'Loss': format_total_with_percent(raw_totals['Loss'], total_war_attacks)  # Loss vs war attacks
    }
    
    return totals_row


def create_chain_html_table(df, totals_row):
    """Create HTML table with totals row"""
    
    # Get column order - include saves columns
    new_cols = ['Member', 'Respect', 'Best', 'Avg', 'Attacks', 'War', 'Outside', 'Saves', 'Save_Score', 'Leave', 'Hosp', 'Mug', 'Retal', 'Overseas', 'Draw', 'Assist', 'Escape', 'Loss']
    
    # Generate HTML table
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

    return html_table


def generate_chain_report_content(complete_chain_data):
    """Main function to generate chain report content"""
    print("Generating chain report content...")
    
    # Prepare display data
    df, total_respect, total_attacks, total_best, avg_respect, raw_totals = prepare_chain_display_data(complete_chain_data)
    
    # Create totals row
    totals_row = create_totals_row(total_respect, total_attacks, total_best, avg_respect, raw_totals, complete_chain_data)
    
    # Create HTML table
    html_table = create_chain_html_table(df, totals_row)
    
    print("Chain report content generated successfully")
    
    return {
        'table_html': html_table
    }