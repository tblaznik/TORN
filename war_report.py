import pandas as pd
import statistics
from datetime import datetime, timedelta


def convert_to_tct(timestamp):
    """Take API timestamp and subtract 2 hours, then display"""
    if timestamp:
        dt = datetime.fromtimestamp(timestamp)
        # Subtract 2 hours
        tct_dt = dt - timedelta(hours=2)
        return tct_dt.strftime('%Y-%m-%d %H:%M:%S TCT')
    return "Unknown"


def format_duration_hms(hours):
    """Format duration as HH:MM:SS"""
    if hours:
        total_seconds = int(hours * 3600)
        hours_part = total_seconds // 3600
        minutes_part = (total_seconds % 3600) // 60
        seconds_part = total_seconds % 60
        return f"{hours_part:02d}:{minutes_part:02d}:{seconds_part:02d}"
    return "00:00:00"


def format_number_american(num):
    """Format numbers with American standards: comma as thousands separator, period as decimal"""
    if isinstance(num, (int, float)):
        return f"{num:,.2f}"
    return str(num)


def calculate_battle_stats(attacks, duration_hours):
    """Calculate hits per minute"""
    if attacks and duration_hours and duration_hours > 0:
        hits_per_min = attacks / (duration_hours * 60)
        return f"{hits_per_min:.4f}"
    return "0.0000"


def calculate_avg_hit_score(score, attacks):
    """Calculate average score per hit"""
    if score and attacks and attacks > 0:
        avg = round(score / attacks, 2)
        return format_number_american(avg)
    return "0.00"


def calculate_efficiency_score(score, duration_hours):
    """Score per minute (combines attack frequency + effectiveness)"""
    if duration_hours and duration_hours > 0:
        return score / (duration_hours * 60)
    return 0.0


def calculate_attack_frequency(attacks, duration_hours):
    """Attacks per hour"""
    if duration_hours and duration_hours > 0:
        return attacks / duration_hours
    return 0.0


def calculate_performance_vs_level(score, level):
    """Score per level - shows who's punching above their weight"""
    if level and level > 0:
        return score / level
    return 0.0


def calculate_faction_stats(member_stats, faction_name):
    """Calculate advanced faction-wide statistics"""
    faction_members = [stats for stats in member_stats.values() if stats['faction'] == faction_name]
    if not faction_members:
        return {}
    
    # Get all scores for statistical analysis
    scores = [member['score'] for member in faction_members if member['attacks'] > 0]
    attacks = [member['attacks'] for member in faction_members if member['attacks'] > 0]
    
    if not scores:
        return {}
    
    # Calculate statistics
    avg_score = statistics.mean(scores)
    score_std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
    
    # Participation rate (members who attacked vs total members)
    total_members = len([m for m in member_stats.values() if m['faction'] == faction_name])
    participating_members = len(scores)
    participation_rate = (participating_members / total_members) * 100 if total_members > 0 else 0
    
    # Consistency rating (lower std dev relative to mean = more consistent)
    consistency_rating = (score_std_dev / avg_score) * 100 if avg_score > 0 else 0
    
    return {
        'avg_score': avg_score,
        'score_std_dev': score_std_dev,
        'participation_rate': participation_rate,
        'consistency_rating': consistency_rating,
        'total_members': total_members,
        'participating_members': participating_members
    }


def process_war_data(war_data):
    """Process raw war data into member statistics"""
    war_start = war_data.get('start', 0)
    war_end = war_data.get('end', 0)
    war_duration_hours = (war_end - war_start) / 3600
    our_faction_data = war_data.get('our_faction', {})
    
    # Get all factions in the war
    all_factions = war_data['war_info'].get('factions', {})
    
    # Find enemy faction (the one that's not us)
    enemy_faction_data = None
    enemy_faction_id = None
    faction_id = war_data.get('our_faction', {}).get('faction_id')
    
    for fid, faction_data in all_factions.items():
        if str(fid) != str(faction_id):
            enemy_faction_data = faction_data
            enemy_faction_id = fid
            break
    
    war_members = our_faction_data.get('members', {})
    enemy_members = enemy_faction_data.get('members', {}) if enemy_faction_data else {}
    
    member_stats = {}
    total_attacks = 0
    total_score = 0
    enemy_total_attacks = 0
    enemy_total_score = 0
    
    # Process our faction members
    for member_id, member_data in war_members.items():
        member_name = member_data.get('name', f'ID_{member_id}')
        member_level = member_data.get('level', 0)
        member_attacks = member_data.get('attacks', 0)
        member_score = member_data.get('score', 0)
        
        total_attacks += member_attacks
        total_score += member_score
        
        avg_score_hit = round(member_score / member_attacks, 2) if member_attacks > 0 else 0
        
        # Calculate advanced metrics
        efficiency_score = calculate_efficiency_score(member_score, war_duration_hours)
        attack_frequency = calculate_attack_frequency(member_attacks, war_duration_hours)
        performance_vs_level = calculate_performance_vs_level(member_score, member_level)
        
        member_stats[member_id] = {
            'name': member_name,
            'level': member_level,
            'attacks': member_attacks,
            'score': member_score,
            'avg_score_hit': avg_score_hit,
            'faction': 'Our Faction',
            'faction_id': faction_id,
            'efficiency_score': efficiency_score,
            'attack_frequency': attack_frequency,
            'performance_vs_level': performance_vs_level
        }
    
    # Process enemy faction members
    enemy_faction_name = enemy_faction_data.get('name', 'Enemy Faction') if enemy_faction_data else 'Enemy Faction'
    for member_id, member_data in enemy_members.items():
        member_name = member_data.get('name', f'ID_{member_id}')
        member_level = member_data.get('level', 0)
        member_attacks = member_data.get('attacks', 0)
        member_score = member_data.get('score', 0)
        
        enemy_total_attacks += member_attacks
        enemy_total_score += member_score
        
        avg_score_hit = round(member_score / member_attacks, 2) if member_attacks > 0 else 0
        
        # Calculate advanced metrics
        efficiency_score = calculate_efficiency_score(member_score, war_duration_hours)
        attack_frequency = calculate_attack_frequency(member_attacks, war_duration_hours)
        performance_vs_level = calculate_performance_vs_level(member_score, member_level)
        
        member_stats[f"enemy_{member_id}"] = {
            'name': member_name,
            'level': member_level,
            'attacks': member_attacks,
            'score': member_score,
            'avg_score_hit': avg_score_hit,
            'faction': enemy_faction_name,
            'faction_id': enemy_faction_id,
            'efficiency_score': efficiency_score,
            'attack_frequency': attack_frequency,
            'performance_vs_level': performance_vs_level
        }
    
    # Calculate faction-wide statistics
    our_faction_stats = calculate_faction_stats(member_stats, 'Our Faction')
    enemy_faction_stats = calculate_faction_stats(member_stats, enemy_faction_name)
    
    return {
        'member_stats': member_stats,
        'total_attacks': total_attacks + enemy_total_attacks,
        'total_score': total_score + enemy_total_score,
        'our_attacks': total_attacks,
        'our_score': total_score,
        'enemy_attacks': enemy_total_attacks,
        'enemy_score': enemy_total_score,
        'enemy_faction_name': enemy_faction_name,
        'war_start': war_start,
        'war_end': war_end,
        'war_duration_hours': war_duration_hours,
        'our_faction_stats': our_faction_stats,
        'enemy_faction_stats': enemy_faction_stats
    }


def create_report_dataframes(processed_data):
    """Create separate DataFrames for our faction and enemy faction"""
    
    # Calculate totals and averages for comparison
    our_total_attacks = sum(stats['attacks'] for stats in processed_data['member_stats'].values() if stats['faction'] == 'Our Faction')
    enemy_total_attacks = sum(stats['attacks'] for stats in processed_data['member_stats'].values() if stats['faction'] != 'Our Faction')
    
    # Calculate faction averages for comparison
    our_members = [stats for stats in processed_data['member_stats'].values() if stats['faction'] == 'Our Faction' and stats['attacks'] > 0]
    enemy_members = [stats for stats in processed_data['member_stats'].values() if stats['faction'] != 'Our Faction' and stats['attacks'] > 0]
    
    our_avg_score = statistics.mean([m['score'] for m in our_members]) if our_members else 0
    enemy_avg_score = statistics.mean([m['score'] for m in enemy_members]) if enemy_members else 0
    
    our_rows = []
    enemy_rows = []
    
    for member_id, stats in processed_data['member_stats'].items():
        if stats['attacks'] > 0:  # Only show members who participated
            # Calculate percentages
            if stats['faction'] == 'Our Faction':
                hit_percentage = (stats['attacks'] / our_total_attacks) * 100 if our_total_attacks > 0 else 0
                score_percentage = (stats['score'] / processed_data['our_score']) * 100 if processed_data['our_score'] > 0 else 0
                # Performance comparison (above/below faction average)
                performance_vs_avg = ((stats['score'] - our_avg_score) / our_avg_score) * 100 if our_avg_score > 0 else 0
            else:
                hit_percentage = (stats['attacks'] / enemy_total_attacks) * 100 if enemy_total_attacks > 0 else 0
                score_percentage = (stats['score'] / processed_data['enemy_score']) * 100 if processed_data['enemy_score'] > 0 else 0
                # Performance comparison (above/below faction average)
                performance_vs_avg = ((stats['score'] - enemy_avg_score) / enemy_avg_score) * 100 if enemy_avg_score > 0 else 0
            
            row = {
                'Members': f'<a href="https://www.torn.com/profiles.php?XID={member_id.replace("enemy_", "")}" target="_blank" style="color: #ffffff; text-decoration: none;">{stats["name"]}</a>',
                'Level': stats['level'],
                'Attacks': stats['attacks'],
                'Hit %': f"{hit_percentage:.2f}%",
                'Score': format_number_american(stats['score']),
                'Score %': f"{score_percentage:.2f}%",
                'Avg score/hit': format_number_american(stats['avg_score_hit']),
                'Efficiency': format_number_american(stats['efficiency_score']),
                'Att/Hr': format_number_american(stats['attack_frequency']),
                'Score/Lvl': format_number_american(stats['performance_vs_level']),
                'vs Avg': f"{performance_vs_avg:+.1f}%"
            }
            
            if stats['faction'] == 'Our Faction':
                our_rows.append(row)
            else:
                enemy_rows.append(row)
    
    # Create separate DataFrames
    our_df = pd.DataFrame(our_rows) if our_rows else pd.DataFrame()
    enemy_df = pd.DataFrame(enemy_rows) if enemy_rows else pd.DataFrame()
    
    # Sort both by score descending (need to parse American format for sorting)
    if not our_df.empty:
        our_df['_sort_score'] = our_df['Score'].str.replace(',', '').astype(float)
        our_df = our_df.sort_values('_sort_score', ascending=False)
        our_df = our_df.drop('_sort_score', axis=1)
        
    if not enemy_df.empty:
        enemy_df['_sort_score'] = enemy_df['Score'].str.replace(',', '').astype(float)
        enemy_df = enemy_df.sort_values('_sort_score', ascending=False)
        enemy_df = enemy_df.drop('_sort_score', axis=1)
    
    return our_df, enemy_df


def create_styled_html_tables(our_df, enemy_df, processed_data):
    """Create HTML tables with faction statistics"""
    
    # War info with TCT times and duration formatting
    war_start = convert_to_tct(processed_data['war_start'])
    war_end = convert_to_tct(processed_data['war_end'])
    war_duration_formatted = format_duration_hms(processed_data['war_duration_hours'])
    
    # Calculate battle stats with American formatting
    our_hits_per_min = calculate_battle_stats(processed_data['our_attacks'], processed_data['war_duration_hours'])
    our_avg_hit_score = calculate_avg_hit_score(processed_data['our_score'], processed_data['our_attacks'])
    enemy_hits_per_min = calculate_battle_stats(processed_data['enemy_attacks'], processed_data['war_duration_hours'])
    enemy_avg_hit_score = calculate_avg_hit_score(processed_data['enemy_score'], processed_data['enemy_attacks'])
    
    # Convert DataFrames to HTML tables
    our_table_html = ""
    enemy_table_html = ""
    
    if not our_df.empty:
        our_table_html = our_df.to_html(
            classes='war_report',
            table_id='our_faction_table', 
            index=False,
            escape=False,
            border=0
        )
    
    if not enemy_df.empty:
        enemy_table_html = enemy_df.to_html(
            classes='war_report',
            table_id='enemy_faction_table', 
            index=False,
            escape=False,
            border=0
        )
    
    # Add faction statistics to the stats boxes
    our_stats = processed_data.get('our_faction_stats', {})
    enemy_stats = processed_data.get('enemy_faction_stats', {})
    
    # Create combined table HTML with side-by-side layout and faction colors
    tables_html = f"""
    <div class="tables-container">
        <div class="faction-section">
            <h3 style="background: linear-gradient(135deg, #2d5a2d, #4a8b4a); color: white; padding: 15px; border-radius: 8px;">EPIC Mafia</h3>
            <div class="faction-stats our-stats" style="margin-bottom: 15px;">
                <div class="stat-box">
                    <div class="stat-number">{processed_data['our_attacks']:,}</div>
                    <div class="stat-label">Our Attacks</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{format_number_american(processed_data['our_score'])}</div>
                    <div class="stat-label">Our Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{our_hits_per_min}</div>
                    <div class="stat-label">Hits/Min</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{our_avg_hit_score}</div>
                    <div class="stat-label">Avg Hit Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{our_stats.get('participation_rate', 0):.1f}%</div>
                    <div class="stat-label">Participation</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{our_stats.get('consistency_rating', 0):.1f}%</div>
                    <div class="stat-label">Consistency</div>
                </div>
            </div>
            {our_table_html}
        </div>
        
        <div class="faction-section">
            <h3 style="background: linear-gradient(135deg, #cc4d1f, #e55a2b); color: white; padding: 15px; border-radius: 8px;">{processed_data['enemy_faction_name']}</h3>
            <div class="faction-stats enemy-stats" style="margin-bottom: 15px;">
                <div class="stat-box">
                    <div class="stat-number">{processed_data['enemy_attacks']:,}</div>
                    <div class="stat-label">Enemy Attacks</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{format_number_american(processed_data['enemy_score'])}</div>
                    <div class="stat-label">Enemy Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{enemy_hits_per_min}</div>
                    <div class="stat-label">Hits/Min</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{enemy_avg_hit_score}</div>
                    <div class="stat-label">Avg Hit Score</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{enemy_stats.get('participation_rate', 0):.1f}%</div>
                    <div class="stat-label">Participation</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{enemy_stats.get('consistency_rating', 0):.1f}%</div>
                    <div class="stat-label">Consistency</div>
                </div>
            </div>
            {enemy_table_html}
        </div>
    </div>
    """
    
    return {
        'table_html': tables_html,
        'war_start': war_start,
        'war_end': war_end,
        'war_duration': war_duration_formatted
    }


def generate_war_report_content(war_data):
    """Main function to generate war report content"""
    print("Generating war report content...")
    
    # Process raw war data
    processed_data = process_war_data(war_data)
    
    # Create DataFrames
    our_df, enemy_df = create_report_dataframes(processed_data)
    
    # Create HTML content
    html_content = create_styled_html_tables(our_df, enemy_df, processed_data)
    
    print("War report content generated successfully")
    return html_content