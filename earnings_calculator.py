import pandas as pd
import re


def format_us_currency(amount):
    """Format number in US style with currency"""
    return f"${amount:,.2f}"


def format_us_number(amount):
    """Format number in US style without currency"""
    return f"{amount:,.2f}"


def format_member_link(cell):
    """Format member names with Torn profile links"""
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


def calculate_earnings_summary(complete_chain_data, total_caches=4209000000.00, tax_rate=0.05, respect_weight=60, hit_weight=30):
    """Calculate earnings summary statistics"""
    
    print("=== CALCULATING EARNINGS SUMMARY ===")
    
    # Basic calculations
    tax_amount = total_caches * tax_rate
    total_payout = total_caches - tax_amount
    total_weight = 90  # respect_weight + hit_weight
    
    print(f"Total Caches: ${total_caches:,.2f}")
    print(f"Tax Amount: ${tax_amount:,.2f} ({total_caches:,.2f} × {tax_rate})")
    print(f"Total Payout: ${total_payout:,.2f}")
    
    # Calculate totals from complete chain data using WAR RESPECT
    total_respect = complete_chain_data['War_Respect'].sum()  # Use war respect only
    total_war_hits = complete_chain_data['War'].sum()
    total_saves = complete_chain_data['Saves'].sum()
    total_save_score = complete_chain_data['Save_Score'].sum()
    
    print(f"War Respect Total: {total_respect:,.2f}")
    print(f"War Hits Total: {total_war_hits:,}")
    print(f"Total Saves: {total_saves}")
    print(f"Total Save Score: {total_save_score:.2f}")
    
    # Calculate mod values using WAR RESPECT
    mod_score = total_respect + total_save_score 
    mod_hit = total_war_hits + total_saves 
    avg_score_hit = mod_score / mod_hit if mod_hit > 0 else 0
    save_resp = avg_score_hit * 1.2
    save_pay = 0  # Set to 0 for now
    
    print(f"Mod Score: {mod_score:,.2f} ({total_respect:,.2f} + {total_save_score:.2f})")
    print(f"Mod Hit: {mod_hit:,} ({total_war_hits:,} + {total_saves})")
    print(f"Average Score/Hit: {avg_score_hit:.2f}")
    print(f"Save Resp (120% avg): {save_resp:.2f}")
    
    # Calculate pool distribution
    remaining_payout = total_payout - save_pay
    hit_pool = remaining_payout * (hit_weight / total_weight)
    score_pool = remaining_payout * (respect_weight / total_weight)
    
    print(f"Hit Pool: ${hit_pool:,.2f} ({remaining_payout:,.2f} × {hit_weight}/{total_weight})")
    print(f"Score Pool: ${score_pool:,.2f} ({remaining_payout:,.2f} × {respect_weight}/{total_weight})")
    
    # Calculate pay rates
    pay_hit = hit_pool / mod_hit if mod_hit > 0 else 0
    pay_score = score_pool / mod_score if mod_score > 0 else 0
    
    print(f"Pay per Hit: ${pay_hit:,.2f}")
    print(f"Pay per Score: ${pay_score:,.2f}")
    
    return {
        'total_caches': total_caches,
        'tax_amount': tax_amount,
        'total_payout': total_payout,
        'total_hits': mod_hit,
        'total_score': mod_score,
        'avg_score_hit': avg_score_hit,
        'total_saves': total_saves,
        'save_resp': save_resp,
        'total_save_score': total_save_score,
        'save_pay': save_pay,
        'mod_score': mod_score,
        'mod_hit': mod_hit,
        'pay_hit': pay_hit,
        'pay_score': pay_score,
        'respect_pool': score_pool,
        'hit_pool': hit_pool,
        'respect_weight': respect_weight,
        'hit_weight': hit_weight,
        'total_members': len(complete_chain_data)
    }


def calculate_individual_earnings(complete_chain_data, summary):
    """Calculate individual member earnings"""
    
    print("=== CALCULATING INDIVIDUAL EARNINGS ===")
    
    pay_hit = summary['pay_hit']
    pay_score = summary['pay_score']
    mod_hit = summary['mod_hit']
    mod_score = summary['mod_score']
    total_payout = summary['total_payout']
    
    earnings_data = []
    
    for _, row in complete_chain_data.iterrows():
        member_respect = row['War_Respect']  # Use war respect
        member_war_hits = row['War']
        member_save_score = row['Save_Score']
        member_saves = row['Saves']
        
        # Total member score includes save score
        member_total_score = member_respect + member_save_score
        
        # Earnings calculation: Hit Earnings + Score Earnings
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
            'Total_Score': member_total_score,
            'Saves': member_saves,
            'Save_Score': member_save_score,
            'Respect_Share': score_share * 100,
            'Hit_Share': hit_share * 100,
            'Respect_Earnings': score_earnings,
            'Hit_Earnings': hit_earnings,
            'Total_Earnings': total_earnings,
            'Total_Share': (total_earnings / total_payout) * 100
        })
    
    earnings_df = pd.DataFrame(earnings_data)
    
    # Show sample calculation for verification
    if not earnings_df.empty:
        sample = earnings_df.iloc[0]  # First member
        print(f"Sample calculation - {sample['Member']}:")
        print(f"   War Respect: {sample['Respect']}")
        print(f"   War Hits: {sample['War_Hits']}")
        print(f"   Save Score: {sample['Save_Score']}")
        print(f"   Total Score: {sample['Total_Score']}")
        print(f"   Hit Earnings: ${sample['Hit_Earnings']:,.2f}")
        print(f"   Score Earnings: ${sample['Respect_Earnings']:,.2f}")
        print(f"   Total Earnings: ${sample['Total_Earnings']:,.2f}")
    
    return earnings_df


def create_earnings_html_table(earnings_df):
    """Create HTML table for earnings display"""
    
    # Create display DataFrame
    display_df = earnings_df.copy()
    display_df['Member'] = display_df['Member'].apply(format_member_link)
    
    # Format for display
    display_df['War_Hits'] = display_df['War_Hits'].astype(int)
    display_df['Saves'] = display_df['Saves'].astype(int)
    display_df['Respect %'] = display_df['Respect_Share'].apply(lambda x: f"{x:.2f}%")
    display_df['Hit %'] = display_df['Hit_Share'].apply(lambda x: f"{x:.2f}%")
    display_df['Total %'] = display_df['Total_Share'].apply(lambda x: f"{x:.2f}%")
    display_df['Respect Earnings'] = display_df['Respect_Earnings'].apply(format_us_currency)
    display_df['Hit Earnings'] = display_df['Hit_Earnings'].apply(format_us_currency)
    display_df['Total Earnings'] = display_df['Total_Earnings'].apply(format_us_currency)
    
    # Select columns for display
    display_cols = ['Member', 'Respect', 'War_Hits', 'Total_Score', 'Saves', 'Save_Score', 'Respect %', 'Hit %', 
                   'Respect Earnings', 'Hit Earnings', 'Total Earnings', 'Total %']
    display_df = display_df[display_cols]
    display_df.columns = ['Member', 'Respect', 'War Hits', 'Total Score', 'Saves', 'Save Score', 'Respect %', 'Hit %', 
                   'Respect Earnings', 'Hit Earnings', 'Total Earnings', 'Total %']
    
    # Sort by total earnings (descending)
    # Create a temporary numeric column for sorting
    display_df['_sort_total'] = display_df['Total Earnings'].str.replace('$', '').str.replace(',', '').astype(float)
    display_df = display_df.sort_values('_sort_total', ascending=False)
    display_df = display_df.drop('_sort_total', axis=1)
    
    return display_df.to_html(index=False, escape=False, classes='earnings_report', border=0)


def calculate_earnings_content(complete_chain_data, total_caches=4209000000.00):
    """Main function to calculate earnings and generate content"""
    
    print("Generating earnings content...")
    
    # Calculate summary statistics
    summary = calculate_earnings_summary(complete_chain_data, total_caches)
    
    # Calculate individual earnings
    earnings_df = calculate_individual_earnings(complete_chain_data, summary)
    
    # Create HTML table
    html_table = create_earnings_html_table(earnings_df)
    
    # Format summary values for template
    formatted_summary = {
        'total_hits': f"{summary['total_hits']:,}",
        'total_score': f"{summary['total_score']:,.2f}",
        'avg_score_hit': f"{summary['avg_score_hit']:.2f}",
        'total_caches': format_us_currency(summary['total_caches']),
        'tax_amount': format_us_currency(summary['tax_amount']),
        'total_payout': format_us_currency(summary['total_payout']),
        'total_saves': f"{summary['total_saves']:.2f}",
        'save_resp': f"{summary['save_resp']:.2f}",
        'total_save_score': f"{summary['total_save_score']:.2f}",
        'save_pay': format_us_currency(summary['save_pay']),
        'mod_score': f"{summary['mod_score']:,.2f}",
        'mod_hit': f"{summary['mod_hit']:,}",
        'pay_hit': format_us_currency(summary['pay_hit']),
        'pay_score': format_us_currency(summary['pay_score']),
        'respect_pool': format_us_currency(summary['respect_pool']),
        'hit_pool': format_us_currency(summary['hit_pool']),
        'respect_weight': summary['respect_weight'],
        'hit_weight': summary['hit_weight'],
        'total_members': summary['total_members']
    }
    
    print("Earnings content generated successfully")
    
    return {
        'table_html': html_table,
        'summary': formatted_summary
    }