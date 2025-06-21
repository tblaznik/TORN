import pandas as pd
import os
import re
import json


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

    # Convert numbers properly handling American formatting (comma as thousands separator)
    def convert_american_number(value_str):
        value_str = str(value_str).strip()
        if not value_str or value_str == 'nan':
            return 0.0
        
        # Remove commas (thousands separators) and convert to float
        return float(value_str.replace(',', ''))

    # Convert columns with proper American number handling
    for col in df.columns[1:]:
        df[col] = df[col].apply(convert_american_number)

    # Try to load war respect data if available
    war_respect_data = None
    if os.path.exists('war_respect_data.csv'):
        print("Loading war respect data for proper calculations...")
        war_df = pd.read_csv('war_respect_data.csv', sep=';', encoding='utf-8')
        war_respect_data = {}
        for _, row in war_df.iterrows():
            # Clean member names for matching
            clean_name = re.sub(r'\[\d+\]', '', row['Member']).strip()
            war_respect_data[clean_name] = row['war_respect']
        print(f"Loaded war respect data for {len(war_respect_data)} members")

    # If we have war respect data, use it to calculate outside respect properly
    if war_respect_data:
        print("Calculating war vs outside respect using API data...")
        for i, row in df.iterrows():
            member_name_original = row['Member']
            
            # Clean the name properly - remove the capitalized duplicate part
            def clean_member_name(name):
                # Remove ID brackets first
                clean = re.sub(r'\[\d+\]', '', name).strip()
                
                # Handle duplicated names like "JlambJLAMB" -> "Jlamb"
                # Split the name and check if second half is uppercase version of first half
                if len(clean) > 0:
                    # Find the middle point
                    mid = len(clean) // 2
                    first_half = clean[:mid]
                    second_half = clean[mid:]
                    
                    # Check if second half is uppercase version of first half
                    if first_half.upper() == second_half:
                        return first_half
                
                return clean
            
            clean_name = clean_member_name(member_name_original)
            
            if clean_name in war_respect_data:
                war_respect = war_respect_data[clean_name]
                total_respect = row['Respect']
                outside_respect = total_respect - war_respect
                
                # Update the dataframe
                df.at[i, 'War_Respect'] = war_respect
                df.at[i, 'Outside_Respect'] = outside_respect
                
                print(f"{clean_name}: Total={total_respect}, War={war_respect}, Outside={outside_respect}")
            else:
                # Try case-insensitive matching
                found_match = False
                for war_name in war_respect_data.keys():
                    if clean_name.lower() == war_name.lower():
                        war_respect = war_respect_data[war_name]
                        total_respect = row['Respect']
                        outside_respect = total_respect - war_respect
                        
                        df.at[i, 'War_Respect'] = war_respect
                        df.at[i, 'Outside_Respect'] = outside_respect
                        
                        print(f"{clean_name} (case-insensitive match with {war_name}): Total={total_respect}, War={war_respect}, Outside={outside_respect}")
                        found_match = True
                        break
                
                if not found_match:
                    # Fallback: assume all respect is from war if not found
                    df.at[i, 'War_Respect'] = row['Respect']
                    df.at[i, 'Outside_Respect'] = 0
                    print(f"{clean_name}: Not found in war data, using total respect as war respect")
    else:
        print("No war respect data available, using chain report data as-is")
        df['War_Respect'] = df['Respect']
        df['Outside_Respect'] = 0

    df["Outside"] = df["Attacks"] - df["War"]

    percent_cols = ["Leave", "Mug", "Hosp", "War", "Outside", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"]

    # Calculate totals BEFORE applying percentage formatting - use War_Respect for calculations
    total_respect = df["War_Respect"].sum()  # Use war respect for totals
    total_attacks = df["Attacks"].sum()
    total_best = df["Best"].max()  # Best chain bonus is the maximum
    avg_respect = df["War_Respect"].mean()  # Average war respect per member
    
    # Store raw totals for percentage columns
    raw_totals = {}
    for col in percent_cols:
        raw_totals[col] = df[col].sum()

    # Store raw values for each row BEFORE formatting
    raw_war_attacks = df["War"].copy()
    raw_total_attacks = df["Attacks"].copy()

    # Prepare pie chart data
    # Chart 1: War vs Outside
    war_vs_outside_data = {
        'labels': ['War', 'Outside'],
        'data': [int(raw_totals['War']), int(raw_totals['Outside'])],
        'colors': ['#f093fb', '#667eea']
    }
    
    # Chart 2: Attack types breakdown
    attack_types_labels = ['Leave', 'Hosp', 'Retal', 'Mug', 'Overseas', 'Assist', 'Draw', 'Escape', 'Loss']
    attack_types_colors = ['#2ECC71', '#27AE60', '#16A085', '#F39C12', '#E67E22', '#D35400', '#E74C3C', '#C0392B', '#8E44AD']
    
    # Filter out zero values
    filtered_attack_data = []
    filtered_attack_labels = []
    filtered_attack_colors = []
    
    for i, label in enumerate(attack_types_labels):
        value = int(raw_totals[label])
        if value > 0:
            filtered_attack_data.append(value)
            filtered_attack_labels.append(label)
            filtered_attack_colors.append(attack_types_colors[i])
    
    attack_types_data = {
        'labels': filtered_attack_labels,
        'data': filtered_attack_data,
        'colors': filtered_attack_colors
    }

    # Prepare JSON data for JavaScript
    war_data_json = json.dumps(war_vs_outside_data['data'])
    war_colors_json = json.dumps(war_vs_outside_data['colors'])
    war_labels_json = json.dumps(war_vs_outside_data['labels'])
    attack_data_json = json.dumps(attack_types_data['data'])
    attack_colors_json = json.dumps(attack_types_data['colors'])
    attack_labels_json = json.dumps(attack_types_data['labels'])

    def format_value_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        formatted_value = f'<div data-sort="{value_int}">{value_int:,}<div style="font-size: 10px; color: #aaa">{percent:.2f}%</div></div>'
        return formatted_value

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

    print(df.head())
    df = df.sort_values("War_Respect", ascending=False)  # Sort by war respect

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
    df["Respect"] = df["War_Respect"].apply(lambda x: f"{int(round(x)):,}")  # Use war respect for display
    df["Attacks"] = df["Attacks"].apply(lambda x: f"{int(round(x)):,}")
    df["Best"] = df["Best"].apply(format_number)
    df["Avg"] = df["Avg"].apply(format_number)

    new_cols = ['Member', 'Respect', 'Best', 'Avg', 'Attacks', 'War', 'Outside', 'Leave', 'Hosp', 'Mug', 'Retal', 'Overseas', 'Draw', 'Assist', 'Escape', 'Loss']
    df = df[new_cols]

    # Create totals row with proper formatting
    def format_total_with_percent(value, total):
        value_int = int(round(value))
        percent = (value / total * 100) if total > 0 else 0.0
        return f'<div data-sort="{value_int}"><strong>{value_int:,}</strong><div style="font-size: 10px; color: #aaa"><strong>{percent:.2f}%</strong></div></div>'

    # Calculate war attacks (excluding outside attacks)
    total_war_attacks = raw_totals['War']

    totals_row = {
        'Member': '<strong>TOTALS</strong>',
        'Respect': f'<strong>{int(round(total_respect)):,}</strong>',
        'Best': f'<strong>{format_number(total_best)}</strong>',
        'Avg': f'<strong>{format_number(avg_respect)}</strong>',
        'Attacks': f'<strong>{int(round(total_attacks)):,}</strong>',
        'War': format_total_with_percent(raw_totals['War'], total_attacks),  # War vs total attacks
        'Outside': format_total_with_percent(raw_totals['Outside'], total_attacks),  # Outside vs total attacks
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

    # Create pie charts section
    pie_charts_html = f"""
    <div class="charts-section">
        <h2 style="text-align: center; color: white; margin-bottom: 30px;">📊 Attack Distribution</h2>
        <div class="charts-container">
            <div class="chart-box">
                <h3>War vs Outside Attacks</h3>
                <canvas id="warVsOutsideChart" width="400" height="400"></canvas>
            </div>
            
            <div class="chart-box">
                <h3>Attack Types Breakdown</h3>
                <canvas id="attackTypesChart" width="400" height="400"></canvas>
            </div>
        </div>
    </div>
    """

    # Create the chart scripts with proper data injection
    chart_styles_and_scripts = f"""
    <style>
        .charts-section {{
            background-color: #2a2a2a;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid #444;
        }}
        .charts-container {{
            display: flex;
            gap: 40px;
            justify-content: center;
            align-items: flex-start;
            flex-wrap: wrap;
        }}
        .chart-box {{
            background-color: #1a1a1a;
            padding: 25px;
            border-radius: 8px;
            border: 1px solid #555;
            text-align: center;
            flex: 1;
            min-width: 350px;
            max-width: 450px;
        }}
        .chart-box h3 {{
            color: white;
            margin-bottom: 20px;
            font-size: 18px;
        }}
        @media (max-width: 768px) {{
            .charts-container {{
                flex-direction: column;
            }}
            .chart-box {{
                min-width: auto;
                max-width: none;
            }}
        }}
    </style>
    
    <script>
        function drawPieChart(canvasId, data, colors, labels) {{
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const radius = Math.min(centerX, centerY) - 20;
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Calculate total
            const total = data.reduce((sum, value) => sum + value, 0);
            if (total === 0) return;
            
            // Draw pie slices
            let currentAngle = -Math.PI / 2; // Start from top
            
            for (let i = 0; i < data.length; i++) {{
                if (data[i] === 0) continue;
                
                const sliceAngle = (data[i] / total) * 2 * Math.PI;
                
                // Draw slice
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
                ctx.closePath();
                ctx.fillStyle = colors[i];
                ctx.fill();
                
                // Draw border
                ctx.strokeStyle = '#444';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                currentAngle += sliceAngle;
            }}
        }}
        
        function initCharts() {{
            // War vs Outside Chart
            drawPieChart('warVsOutsideChart', {war_data_json}, {war_colors_json}, {war_labels_json});
            
            // Attack Types Chart
            drawPieChart('attackTypesChart', {attack_data_json}, {attack_colors_json}, {attack_labels_json});
        }}
        
        // Initialize charts when DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initCharts);
        }} else {{
            initCharts();
        }}
    </script>
    """

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
    {{PIE_CHARTS}}
    {{CHAIN_TABLE}}
</body>
</html>
"""

    # Replace placeholders with actual content
    final_html = template.replace("{{PIE_CHARTS}}", pie_charts_html)
    final_html = final_html.replace("{{CHAIN_TABLE}}", html_table)
    
    # Insert scripts before </body>
    final_html = final_html.replace("</body>", chart_styles_and_scripts + "\n</body>")

    with open("chain_report.html", "w", encoding="utf-8") as f:
        f.write(final_html)

    print("✅ Chain report with pie charts saved to 'chain_report.html'")