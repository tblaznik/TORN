import pandas as pd
import os
import re


class ChainEarningsCalculator:
    def __init__(self, total_caches, tax_rate=0.05, respect_weight=60, hit_weight=30):
        """
        Initialize the earnings calculator
        
        Args:
            total_caches: Total cache value (US format: 4,209,000,000.00)
            tax_rate: Tax percentage (default 5%)
            respect_weight: Weight for respect-based distribution (default 60)
            hit_weight: Weight for hit-based distribution (default 30)
        """
        print("\n" + "="*60)
        print("🧮 INITIALIZING EARNINGS CALCULATOR")
        print("="*60)
        
        self.total_caches = self.parse_us_number(total_caches)
        self.tax_rate = tax_rate
        self.respect_weight = respect_weight
        self.hit_weight = hit_weight
        self.total_weight = 90 
        
        print(f"📊 Input Parameters:")
        print(f"   Total Caches: ${self.total_caches:,.2f}")
        print(f"   Tax Rate: {self.tax_rate*100}%")
        print(f"   Respect Weight: {self.respect_weight}")
        print(f"   Hit Weight: {self.hit_weight}")
        print(f"   Total Weight: {self.total_weight}")
        
        # Calculate pools
        self.tax_amount = self.total_caches * self.tax_rate
        self.total_payout = self.total_caches - self.tax_amount
        
        print(f"\n💰 Basic Calculations:")
        print(f"   Tax Amount: ${self.tax_amount:,.2f} ({self.total_caches:,.2f} × {self.tax_rate})")
        print(f"   Total Payout: ${self.total_payout:,.2f} ({self.total_caches:,.2f} - {self.tax_amount:,.2f})")
        
        # Calculate pool distributions
        self.respect_pool = self.total_payout * (self.respect_weight / self.total_weight)
        self.hit_pool = self.total_payout * (self.hit_weight / self.total_weight)
        
        print(f"\n🎯 Initial Pool Distributions (will be recalculated later):")
        print(f"   Respect Pool: ${self.respect_pool:,.2f} ({self.total_payout:,.2f} × {self.respect_weight}/{self.total_weight})")
        print(f"   Hit Pool: ${self.hit_pool:,.2f} ({self.total_payout:,.2f} × {self.hit_weight}/{self.total_weight})")
        print(f"   Respect %: {(self.respect_weight/self.total_weight)*100:.2f}%")
        print(f"   Hit %: {(self.hit_weight/self.total_weight)*100:.2f}%")
        
    def parse_us_number(self, value_str):
        """Parse US number format (comma as thousands separator, period as decimal)"""
        if isinstance(value_str, (int, float)):
            return float(value_str)
        
        # Remove currency symbols and spaces
        clean_str = str(value_str).replace('$', '').replace(' ', '').strip()
        
        # Handle US format: 4,209,000,000.00
        return float(clean_str.replace(',', ''))
    
    def format_us_currency(self, amount):
        """Format number in US style with currency"""
        return f"${amount:,.2f}"
    
    def format_us_number(self, amount):
        """Format number in US style without currency"""
        return f"{amount:,.2f}"
    
    def generate_earnings_report(self, chain_df):
        """Generate complete earnings report using war respect data"""
        print("\n" + "="*60)
        print("📋 LOADING AND PROCESSING DATA")
        print("="*60)
        
        # Clean up the data
        chain_df = chain_df.copy()
        
        # Handle war respect data integration
        war_respect_data = None
        if os.path.exists('war_respect_data.csv'):
            print("🔄 Loading war respect data for earnings calculations...")
            war_df = pd.read_csv('war_respect_data.csv', sep=';', encoding='utf-8')
            war_respect_data = {}
            for _, row in war_df.iterrows():
                # Clean member names for matching
                clean_name = re.sub(r'\[\d+\]', '', row['Member']).strip()
                war_respect_data[clean_name] = row['war_respect']
            print(f"✅ Loaded war respect data for {len(war_respect_data)} members")
        
        # Add war respect column to chain data
        if war_respect_data:
            print("\n🔗 Merging war respect data with chain data...")
            chain_df['War_Respect'] = 0.0  # Initialize column
            
            def clean_member_name(name):
                """Clean member name by removing ID brackets and duplicated parts"""
                # Remove ID brackets first
                clean = re.sub(r'\[\d+\]', '', name).strip()
                
                # Handle duplicated names like "JlambJLAMB" -> "Jlamb"
                if len(clean) > 0:
                    # Find the middle point
                    mid = len(clean) // 2
                    first_half = clean[:mid]
                    second_half = clean[mid:]
                    
                    # Check if second half is uppercase version of first half
                    if first_half.upper() == second_half:
                        return first_half
                
                return clean
            
            matches_found = 0
            for i, row in chain_df.iterrows():
                member_name_original = row['Member']
                clean_name = clean_member_name(member_name_original)
                
                # Try to find match in war data
                found_match = False
                if clean_name in war_respect_data:
                    chain_df.at[i, 'War_Respect'] = war_respect_data[clean_name]
                    matches_found += 1
                    found_match = True
                else:
                    # Try case-insensitive matching
                    for war_name in war_respect_data.keys():
                        if clean_name.lower() == war_name.lower():
                            chain_df.at[i, 'War_Respect'] = war_respect_data[war_name]
                            matches_found += 1
                            found_match = True
                            break
                
                if not found_match:
                    # Fallback: use total respect if not found in war data
                    chain_df.at[i, 'War_Respect'] = chain_df.at[i, 'Respect']
                    print(f"⚠️  NO MATCH: {member_name_original} -> using total respect as fallback")
            
            print(f"✅ Successfully matched {matches_found}/{len(chain_df)} members")
        else:
            print("❌ No war respect data available, using chain report respect as-is")
            chain_df['War_Respect'] = chain_df['Respect']

        
        # Clean numeric columns
        numeric_cols = ['War_Respect', 'War']
        for col in numeric_cols:
            if col in chain_df.columns:
                chain_df[col] = chain_df[col].astype(str).str.replace(',', '').astype(float)
        
        # Try to read saves from Excel file first, then CSV
        saves_df = None
        if os.path.exists('saves.xlsx'):
            print("\n📊 Reading saves from XLSX file...")
            saves_df = pd.read_excel('saves.xlsx')
            print(f"✅ Saves XLSX loaded: {len(saves_df)} rows")
        elif os.path.exists('saves.csv'):
            print("\n📊 Reading saves from CSV file...")
            saves_df = pd.read_csv('saves.csv', sep=';', encoding='utf-8')
            print(f"✅ Saves CSV loaded: {len(saves_df)} rows")
        
        if saves_df is not None:
            print(f"   Saves columns: {saves_df.columns.tolist()}")
            
            # Clean member names in saves data for matching
            def clean_saves_name(name):
                # Remove ID brackets and handle duplicated names
                clean = re.sub(r'\[\d+\]', '', str(name)).strip()
                if len(clean) > 0:
                    mid = len(clean) // 2
                    first_half = clean[:mid]
                    second_half = clean[mid:]
                    if first_half.upper() == second_half:
                        return first_half
                return clean
            
            saves_df['Clean_Member'] = saves_df['Member'].apply(clean_saves_name)
            
            # Merge on cleaned names
            chain_df['Clean_Member'] = chain_df['Member'].apply(lambda x: clean_saves_name(x))
            merged_df = chain_df.merge(saves_df[['Clean_Member', 'Saves', 'Save_Score']], 
                                     on='Clean_Member', how='left')
            
            # Fill NaN values with 0 for members who didn't save
            merged_df['Saves'] = merged_df['Saves'].fillna(0)
            merged_df['Save_Score'] = merged_df['Save_Score'].fillna(0)
            
            print(f"✅ Merged saves data: {len(merged_df)} rows")
            
            chain_df = merged_df.drop('Clean_Member', axis=1)  # Remove temporary column
        else:
            print("❌ No saves file found. Adding empty save columns.")
            chain_df['Saves'] = 0
            chain_df['Save_Score'] = 0
        
        # Calculate raw totals from CSV using WAR RESPECT
        total_respect = chain_df['War_Respect'].sum()  # Use war respect only
        total_war_hits = chain_df['War'].sum()
        
        print(f"\n" + "="*60)
        print("📊 RAW TOTALS CALCULATION")
        print("="*60)
        print(f"🎯 War Respect Total: {total_respect:,.2f}")
        print(f"👊 War Hits Total: {total_war_hits:,}")
        
        # Calculate save statistics from merged data
        total_saves = chain_df['Saves'].sum()
        total_save_score = chain_df['Save_Score'].sum()
        save_pay = 0  # Set to 0 for now
        
        print(f"\n💾 Save Statistics:")
        print(f"   Total Saves: {total_saves}")
        print(f"   Total Save Score: {total_save_score:.2f}")
        print(f"   Save Pay: ${save_pay:,.2f}")
        
        # Calculate mod values using WAR RESPECT
        mod_score = total_respect + total_save_score  # Use war respect + save score
        mod_hit = total_war_hits + total_saves  # Use actual saves count
        avg_score_hit = mod_score / mod_hit if mod_hit > 0 else 0
        save_resp = avg_score_hit * 1.2
        
        print(f"\n" + "="*60)
        print("🔧 MOD VALUES CALCULATION")
        print("="*60)
        print(f"📈 Mod Score Calculation:")
        print(f"   {total_respect:,.2f} (war respect) + {total_save_score:.2f} (save score) = {mod_score:,.2f}")
        print(f"📈 Mod Hit Calculation:")
        print(f"   {total_war_hits:,} (war hits) + {total_saves} (saves) = {mod_hit:,}")
        print(f"📊 Average Score/Hit: {avg_score_hit:.2f} ({mod_score:,.2f} ÷ {mod_hit:,})")
        print(f"🆘 Save Resp (120% avg): {save_resp:.2f} ({avg_score_hit:.2f} × 1.2)")
        
        remaining_payout = self.total_payout - save_pay  # Subtract save pay first

        print(f"\n" + "="*60)
        print("💰 POOL CALCULATIONS")
        print("="*60)
        print(f"💵 Remaining Payout Calculation:")
        print(f"   ${self.total_payout:,.2f} (total payout) - ${save_pay:,.2f} (save pay) = ${remaining_payout:,.2f}")
        
        # Calculate pools from remaining payout using correct 60/90 and 30/90 ratios
        hit_pool = remaining_payout * (self.hit_weight / self.total_weight)
        score_pool = remaining_payout * (self.respect_weight / self.total_weight)
        
        print(f"\n🎯 Pool Distribution:")
        print(f"   Hit Pool: ${remaining_payout:,.2f} × ({self.hit_weight}/{self.total_weight}) = ${hit_pool:,.2f}")
        print(f"   Score Pool: ${remaining_payout:,.2f} × ({self.respect_weight}/{self.total_weight}) = ${score_pool:,.2f}")
        print(f"   Hit %: {(self.hit_weight/self.total_weight)*100:.2f}%")
        print(f"   Score %: {(self.respect_weight/self.total_weight)*100:.2f}%")
        
        # Calculate pay rates
        pay_hit = hit_pool / mod_hit if mod_hit > 0 else 0
        pay_score = score_pool / mod_score if mod_score > 0 else 0
        
        print(f"\n" + "="*60)
        print("💎 PAY RATE CALCULATIONS")
        print("="*60)
        print(f"💰 Pay per Hit:")
        print(f"   ${hit_pool:,.2f} (hit pool) ÷ {mod_hit:,} (mod hits) = ${pay_hit:,.2f}")
        print(f"💰 Pay per Score:")
        print(f"   ${score_pool:,.2f} (score pool) ÷ {mod_score:,.2f} (mod score) = ${pay_score:,.2f}")
        
        print(f"\n📋 Final Values Summary:")
        print(f"   Mod Score: {mod_score:,.2f}")
        print(f"   Mod Hit: {mod_hit:,}")
        print(f"   Hit Pool: ${hit_pool:,.2f}")
        print(f"   Score Pool: ${score_pool:,.2f}")
        print(f"   Save Pool: ${save_pay:,.2f}")
        print(f"   Pay per Hit: ${pay_hit:,.2f}")
        print(f"   Pay per Score: ${pay_score:,.2f}")
        
        # Verify totals
        print(f"\n🔍 Verification:")
        print(f"   Hit Pool + Score Pool + Save Pool = ${hit_pool + score_pool + save_pay:,.2f}")
        print(f"   Should equal Total Payout: ${self.total_payout:,.2f}")
        print(f"   Difference: ${abs((hit_pool + score_pool + save_pay) - self.total_payout):,.2f}")
        
        # Calculate individual member earnings using CORRECT formula and WAR RESPECT
        print(f"\n" + "="*60)
        print("👥 INDIVIDUAL MEMBER CALCULATIONS")
        print("="*60)
        
        earnings_data = []
        for _, row in chain_df.iterrows():
            member_respect = row['War_Respect']  # Use war respect
            member_war_hits = row['War']
            member_save_score = row['Save_Score']
            
            # Total member score includes save score
            member_total_score = member_respect + member_save_score
            
            # NEW FORMULA: Hit Earnings + Score Earnings
            hit_earnings = member_war_hits * pay_hit
            score_earnings = member_total_score * pay_score
            total_earnings = hit_earnings + score_earnings
            
            # Calculate shares for display percentages
            hit_share = member_war_hits / mod_hit if mod_hit > 0 else 0
            score_share = member_total_score / mod_score if mod_score > 0 else 0
            
            earnings_data.append({
                'Member': row['Member'],
                'Respect': member_respect,
                'War_Hits': member_war_hits,
                'Save_Score': member_save_score,
                'Total_Score': member_total_score,
                'Respect_Share': score_share * 100,
                'Hit_Share': hit_share * 100,
                'Respect_Earnings': score_earnings,
                'Hit_Earnings': hit_earnings,
                'Total_Earnings': total_earnings,
                'Total_Share': (total_earnings / self.total_payout) * 100
            })
        
        earnings_df = pd.DataFrame(earnings_data)
        
        # Show detailed calculation for GaloSengen
        sample = earnings_df[earnings_df['Member'].str.contains('GaloSengen', na=False)]
        if not sample.empty:
            s = sample.iloc[0]
            print(f"\n🎯 SAMPLE CALCULATION - GaloSengen:")
            print(f"   War Respect: {s['Respect']}")
            print(f"   War Hits: {s['War_Hits']}")
            print(f"   Save Score: {s['Save_Score']}")
            print(f"   Total Score: {s['Total_Score']} ({s['Respect']} + {s['Save_Score']})")
            print(f"   Hit Earnings: ${s['Hit_Earnings']:,.2f} ({s['War_Hits']} × ${pay_hit:,.2f})")
            print(f"   Score Earnings: ${s['Respect_Earnings']:,.2f} ({s['Total_Score']} × ${pay_score:,.2f})")
            print(f"   Total Earnings: ${s['Total_Earnings']:,.2f} (${s['Hit_Earnings']:,.2f} + ${s['Respect_Earnings']:,.2f})")
            print(f"   Expected from PDF: ~$19,616,173")
            print(f"   Difference: ${abs(s['Total_Earnings'] - 19616173):,.2f}")
        
        # Create summary with calculated values
        summary = {
            'total_hits': f"{mod_hit:,}",
            'total_score': f"{mod_score:,.2f}",
            'avg_score_hit': f"{avg_score_hit:.2f}",
            'total_caches': self.format_us_currency(self.total_caches),
            'tax_amount': self.format_us_currency(self.tax_amount),
            'total_payout': self.format_us_currency(self.total_payout),
            'total_saves': f"{total_saves:.2f}",
            'save_resp': f"{save_resp:.2f}",
            'total_save_score': f"{total_save_score:.2f}",
            'save_pay': self.format_us_currency(save_pay),
            'mod_score': f"{mod_score:,.2f}",
            'mod_hit': f"{mod_hit:,}",
            'pay_hit': self.format_us_currency(pay_hit),
            'pay_score': self.format_us_currency(pay_score),
            'respect_pool': self.format_us_currency(score_pool),  # This is now score pool
            'hit_pool': self.format_us_currency(hit_pool),
            'respect_weight': self.respect_weight,
            'hit_weight': self.hit_weight,
            'total_members': len(earnings_df)
        }
        
        print(f"\n" + "="*60)
        print("✅ CALCULATION COMPLETE")
        print("="*60)
        
        return earnings_df, summary
    
    def create_earnings_html_table(self, earnings_df):
        """Create HTML table for earnings display"""
        
        # Clean member names and add profile links
        def format_member(cell):
            match = re.search(r'\[(\d+)]', cell)
            if match:
                torn_id = match.group(1)
                # Extract clean name from the dirty format
                name = re.sub(r'\[\d+\]', '', cell).strip()
                # Handle duplicated names like "RipTheJackerRIPTHEJACKER"
                words = name.split()
                if len(words) >= 2 and words[0].lower() == words[1].lower():
                    name = words[0]
                # Take first half if still too long
                elif len(name) > 15:
                    name = name[:len(name)//2]
                return f'<a href="https://www.torn.com/profiles.php?XID={torn_id}" target="_blank" style="color:#67e8f9;text-decoration:none">{name}</a>'
            return cell
        
        # Create display DataFrame
        display_df = earnings_df.copy()
        display_df['Member'] = display_df['Member'].apply(format_member)
        
        # Format for display
        display_df['Respect %'] = display_df['Respect_Share'].apply(lambda x: f"{x:.2f}%")
        display_df['Hit %'] = display_df['Hit_Share'].apply(lambda x: f"{x:.2f}%")
        display_df['Total %'] = display_df['Total_Share'].apply(lambda x: f"{x:.2f}%")
        display_df['Respect Earnings'] = display_df['Respect_Earnings'].apply(self.format_us_currency)
        display_df['Hit Earnings'] = display_df['Hit_Earnings'].apply(self.format_us_currency)
        display_df['Total Earnings'] = display_df['Total_Earnings'].apply(self.format_us_currency)
        
        # Select columns for display
        display_cols = ['Member', 'Respect', 'War_Hits', 'Save_Score', 'Total_Score', 'Respect %', 'Hit %', 
                       'Respect Earnings', 'Hit Earnings', 'Total Earnings', 'Total %']
        display_df = display_df[display_cols]
        display_df.columns = ['Member', 'War Respect', 'Hits', 'Save Score', 'Total Score', 'Respect %', 'Hit %', 
                             'Respect Earnings', 'Hit Earnings', 'Total Earnings', 'Total %']
        
        # Sort by total earnings (descending)
        # Create a temporary numeric column for sorting
        display_df['_sort_total'] = display_df['Total Earnings'].str.replace('$', '').str.replace(',', '').astype(float)
        display_df = display_df.sort_values('_sort_total', ascending=False)
        display_df = display_df.drop('_sort_total', axis=1)
        
        return display_df.to_html(index=False, escape=False, classes='earnings_report', border=0)


def generate_earnings_report():
    """Generate earnings report from existing chain report CSV"""
    
    # Find chain report CSV
    files = [f for f in os.listdir('.') if f.endswith('.csv') and 'Chain Report' in f]
    if not files:
        print("❌ No Chain Report CSV file found.")
        return
    
    # Read the chain report CSV (semicolon separator, skip first row)
    chain_df = pd.read_csv(files[0], sep=';', skiprows=1, encoding='utf-8')
    chain_df.columns = [
        "Member", "Respect", "Best", "Avg", "Attacks", "Leave", "Mug",
        "Hosp", "War", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"
    ]
    
    print("=== CHAIN REPORT LOADED ===")
    print(f"Chain report rows: {len(chain_df)}")
    
    # Initialize calculator
    calculator = ChainEarningsCalculator(
        total_caches=4209000000.00,
        tax_rate=0.05,
        respect_weight=60,
        hit_weight=30  # Keep these the same, but fix total_weight to 90
    )
    
    # Generate earnings report (saves handling is now inside the calculator)
    earnings_df, summary = calculator.generate_earnings_report(chain_df)
    
    # Print summary
    print("\n=== FINAL SUMMARY ===")
    print(f"Total War Hits: {summary['total_hits']}")
    print(f"Total Score: {summary['total_score']}")
    print(f"Avg Score/Hit: {summary['avg_score_hit']}")
    print(f"Respect Pool: {summary['respect_pool']}")
    print(f"Hit Pool: {summary['hit_pool']}")
    
    # Save detailed earnings to Excel
    earnings_df.to_excel("earnings_breakdown.xlsx", index=False)
    print("\n✅ Detailed earnings saved to 'earnings_breakdown.xlsx'")
    
    # Create HTML table
    html_table = calculator.create_earnings_html_table(earnings_df)
    
    # Load template
    try:
        with open("earnings_report_template.html", "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        print("❌ earnings_report_template.html not found.")
        return
    
    # Replace placeholders
    final_html = template.replace("{{EARNINGS_TABLE}}", html_table)
    final_html = final_html.replace("{{TOTAL_HITS}}", summary['total_hits'])
    final_html = final_html.replace("{{TOTAL_SCORE}}", summary['total_score'])
    final_html = final_html.replace("{{AVG_SCORE_HIT}}", summary['avg_score_hit'])
    final_html = final_html.replace("{{TOTAL_CACHES}}", summary['total_caches'])
    final_html = final_html.replace("{{TAX_AMOUNT}}", summary['tax_amount'])
    final_html = final_html.replace("{{TOTAL_PAYOUT}}", summary['total_payout'])
    final_html = final_html.replace("{{TOTAL_SAVES}}", summary['total_saves'])
    final_html = final_html.replace("{{SAVE_RESP}}", summary['save_resp'])
    final_html = final_html.replace("{{TOTAL_SAVE_SCORE}}", summary['total_save_score'])
    final_html = final_html.replace("{{SAVE_PAY}}", summary['save_pay'])
    final_html = final_html.replace("{{MOD_SCORE}}", summary['mod_score'])
    final_html = final_html.replace("{{MOD_HIT}}", summary['mod_hit'])
    final_html = final_html.replace("{{PAY_HIT}}", summary['pay_hit'])
    final_html = final_html.replace("{{PAY_SCORE}}", summary['pay_score'])
    final_html = final_html.replace("{{RESPECT_POOL}}", summary['respect_pool'])
    final_html = final_html.replace("{{HIT_POOL}}", summary['hit_pool'])
    final_html = final_html.replace("{{RESPECT_WEIGHT}}", str(summary['respect_weight']))
    final_html = final_html.replace("{{HIT_WEIGHT}}", str(summary['hit_weight']))
    final_html = final_html.replace("{{TOTAL_MEMBERS}}", str(summary['total_members']))
    
    with open("earnings_report.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print("✅ HTML earnings report saved to 'earnings_report.html'")
    
    return earnings_df, summary


if __name__ == "__main__":
    generate_earnings_report()