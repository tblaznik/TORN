import requests
import json
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import statistics
from chain_report_module import generate_chain_report


class TornWarReport:
    def __init__(self, api_key, faction_id=None, war_id=None):
        self.api_key = api_key
        self.faction_id = faction_id
        self.war_id = war_id
        
    def format_european_number(self, num):
        """Format numbers with European standards: . as thousands separator, , as decimal"""
        if isinstance(num, (int, float)):
            # Format with 2 decimal places and proper thousands separators
            # First format with standard separators, then swap them
            formatted = f"{num:,.2f}"
            # Swap: comma becomes temp, period becomes comma, temp becomes period
            formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            return formatted
        return str(num)
    
    def convert_to_tct(self, timestamp):
        """Take API timestamp and subtract 2 hours, then display"""
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            # Subtract 2 hours
            tct_dt = dt - timedelta(hours=2)
            return tct_dt.strftime('%Y-%m-%d %H:%M:%S TCT')
        return "Unknown"
    
    def format_duration_hms(self, hours):
        """Format duration as HH:MM:SS"""
        if hours:
            total_seconds = int(hours * 3600)
            hours_part = total_seconds // 3600
            minutes_part = (total_seconds % 3600) // 60
            seconds_part = total_seconds % 60
            return f"{hours_part:02d}:{minutes_part:02d}:{seconds_part:02d}"
        return "00:00:00"
    
    def calculate_battle_stats(self, attacks, duration_hours):
        """Calculate hits per minute"""
        if attacks and duration_hours and duration_hours > 0:
            hits_per_min = attacks / (duration_hours * 60)
            return f"{hits_per_min:.4g}".replace('.', ',')  # Use European format
        return "0,0000"
    
    def calculate_avg_hit_score(self, score, attacks):
        """Calculate average score per hit"""
        if score and attacks and attacks > 0:
            return round(score / attacks, 2)
        return 0.0
    
    # Advanced Metrics Functions
    def calculate_efficiency_score(self, score, duration_hours):
        """Score per minute (combines attack frequency + effectiveness)"""
        if duration_hours and duration_hours > 0:
            return score / (duration_hours * 60)
        return 0.0
    
    def calculate_attack_frequency(self, attacks, duration_hours):
        """Attacks per hour"""
        if duration_hours and duration_hours > 0:
            return attacks / duration_hours
        return 0.0
    
    def calculate_performance_vs_level(self, score, level):
        """Score per level - shows who's punching above their weight"""
        if level and level > 0:
            return score / level
        return 0.0
    
    def calculate_faction_stats(self, member_stats, faction_name):
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
        
    def make_api_request(self, endpoint, api_version="v1"):
        if api_version == "v1":
            url = f"https://api.torn.com/{endpoint}&key={self.api_key}"
        else:
            url = f"https://api.torn.com/{api_version}/{endpoint}&key={self.api_key}"
        
        print(f"Making API request to: {url}")
        try:
            response = requests.get(url)
            print(f"Response status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                print(f"API Error: {data['error']}")
                return None
            return data
        except Exception as e:
            print(f"API request failed: {e}")
            return None
        
    def get_market_price(self, item_id):
        print(f"Getting market price for item ID: {item_id}")
        url = f"https://api.torn.com/v2/market/{item_id}?key={self.api_key}&selections=itemmarket"
        try:
            response = requests.get(url)
            print(f"Response status code: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                print(f"API Error: {data['error']}")
                return None
            return data['itemmarket']['item'].get('average_price', 0)
        except Exception as e:
            print(f"Failed to get market price: {e}")
            return None
    
    def get_faction_info(self):
        print("Getting faction info...")
        if not self.faction_id:
            user_data = self.make_api_request("user/?selections=profile", "v1")
            if user_data and 'faction' in user_data:
                self.faction_id = user_data['faction']['faction_id']
                print(f"Found faction ID: {self.faction_id}")
            else:
                print("Could not determine faction ID")
                return None
        
        faction_data = self.make_api_request(f"faction/{self.faction_id}?selections=basic", "v1")
        if faction_data:
            print(f"Faction name: {faction_data.get('name', 'Unknown')}")
        return faction_data

    def get_specific_war_data(self):
        print(f"Getting rankedwarreport for war ID: {self.war_id}")
        
        war_data = self.make_api_request(f"torn/{self.war_id}?selections=rankedwarreport", "v1")
        
        if war_data and 'rankedwarreport' in war_data:
            report = war_data['rankedwarreport']
            print(f"Got war report data")
            
            factions = report.get('factions', {})
            print(f"Factions in war: {list(factions.keys())}")
            
            if str(self.faction_id) in factions:
                print(f"Found our faction {self.faction_id}")
                our_faction = factions[str(self.faction_id)]
                
                war_info = report.get('war', {})
                return {
                    'war_id': self.war_id,
                    'war_info': report,
                    'start': war_info.get('start', 0),
                    'end': war_info.get('end', 0),
                    'our_faction': our_faction
                }
            else:
                print(f"Faction {self.faction_id} not in this war")
        
        print(f"Failed to get war data")
        return None

    def generate_war_earnings_data(self):
        print("STARTING WAR EARNINGS REPORT GENERATION")
        
        faction_info = self.get_faction_info()
        if not faction_info:
            return None
        
        war_data = self.get_specific_war_data()
        
        if not war_data:
            return None
        
        war_start = war_data.get('start', 0)
        war_end = war_data.get('end', 0)
        war_duration_hours = (war_end - war_start) / 3600
        our_faction_data = war_data.get('our_faction', {})

        war_respect = war_data['war_info']['factions']['40959']['rewards']['respect']
        war_items = war_data['war_info']['factions']['40959']['rewards'].get('items', [])
        print(war_items)
        for id,items in war_items.items():
            print(f"Item ID: {id}, Items: {items}")
            avg_price = self.get_market_price(id)
            print(f"Average market price for item ID {id}: {avg_price}")
        item_df = pd.DataFrame.from_dict(war_items, orient='index').reset_index()
        
        print(item_df)
        
        # Get all factions in the war
        all_factions = war_data['war_info'].get('factions', {})
        print(f"All factions in war: {list(all_factions.keys())}")
        
        # Find enemy faction (the one that's not us)
        enemy_faction_data = None
        enemy_faction_id = None
        for faction_id, faction_data in all_factions.items():
            if str(faction_id) != str(self.faction_id):
                enemy_faction_data = faction_data
                enemy_faction_id = faction_id
                break
        
        if enemy_faction_data:
            print(f"Enemy faction: {enemy_faction_data.get('name', f'ID_{enemy_faction_id}')} (ID: {enemy_faction_id})")
        
        print(f"War period: {self.convert_to_tct(war_start)} to {self.convert_to_tct(war_end)}")
        print(f"Our faction score: {our_faction_data.get('score', 0)}")
        if enemy_faction_data:
            print(f"Enemy faction score: {enemy_faction_data.get('score', 0)}")
        
        war_members = our_faction_data.get('members', {})
        enemy_members = enemy_faction_data.get('members', {}) if enemy_faction_data else {}
        print(f"Found {len(war_members)} our members, {len(enemy_members)} enemy members")
        
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
            efficiency_score = self.calculate_efficiency_score(member_score, war_duration_hours)
            attack_frequency = self.calculate_attack_frequency(member_attacks, war_duration_hours)
            performance_vs_level = self.calculate_performance_vs_level(member_score, member_level)
            
            member_stats[member_id] = {
                'name': member_name,
                'level': member_level,
                'attacks': member_attacks,
                'score': member_score,
                'avg_score_hit': avg_score_hit,
                'faction': 'Our Faction',
                'faction_id': self.faction_id,
                'efficiency_score': efficiency_score,
                'attack_frequency': attack_frequency,
                'performance_vs_level': performance_vs_level
            }
        
        # Process enemy faction members
        for member_id, member_data in enemy_members.items():
            member_name = member_data.get('name', f'ID_{member_id}')
            member_level = member_data.get('level', 0)
            member_attacks = member_data.get('attacks', 0)
            member_score = member_data.get('score', 0)
            
            enemy_total_attacks += member_attacks
            enemy_total_score += member_score
            
            avg_score_hit = round(member_score / member_attacks, 2) if member_attacks > 0 else 0
            
            # Calculate advanced metrics
            efficiency_score = self.calculate_efficiency_score(member_score, war_duration_hours)
            attack_frequency = self.calculate_attack_frequency(member_attacks, war_duration_hours)
            performance_vs_level = self.calculate_performance_vs_level(member_score, member_level)
            
            member_stats[f"enemy_{member_id}"] = {
                'name': member_name,
                'level': member_level,
                'attacks': member_attacks,
                'score': member_score,
                'avg_score_hit': avg_score_hit,
                'faction': enemy_faction_data.get('name', 'Enemy Faction') if enemy_faction_data else 'Enemy Faction',
                'faction_id': enemy_faction_id,
                'efficiency_score': efficiency_score,
                'attack_frequency': attack_frequency,
                'performance_vs_level': performance_vs_level
            }
        
        print(f"Processed {total_attacks} our attacks with {total_score} our score")
        print(f"Processed {enemy_total_attacks} enemy attacks with {enemy_total_score} enemy score")
        
        # Calculate faction-wide statistics
        our_faction_stats = self.calculate_faction_stats(member_stats, 'Our Faction')
        enemy_faction_stats = self.calculate_faction_stats(member_stats, enemy_faction_data.get('name', 'Enemy Faction') if enemy_faction_data else 'Enemy Faction')
        
        return {
            'war_info': war_data,
            'member_stats': member_stats,
            'total_attacks': total_attacks + enemy_total_attacks,
            'total_score': total_score + enemy_total_score,
            'our_attacks': total_attacks,
            'our_score': total_score,
            'enemy_attacks': enemy_total_attacks,
            'enemy_score': enemy_total_score,
            'enemy_faction_name': enemy_faction_data.get('name', 'Enemy Faction') if enemy_faction_data else 'Enemy Faction',
            'war_start': war_start,
            'war_end': war_end,
            'war_duration_hours': war_duration_hours,
            'our_faction_stats': our_faction_stats,
            'enemy_faction_stats': enemy_faction_stats
        }
    
    def create_report_dataframe(self):
        data = self.generate_war_earnings_data()
        if not data:
            return None, None, None
        
        # Calculate totals and averages for comparison
        our_total_attacks = sum(stats['attacks'] for stats in data['member_stats'].values() if stats['faction'] == 'Our Faction')
        enemy_total_attacks = sum(stats['attacks'] for stats in data['member_stats'].values() if stats['faction'] != 'Our Faction')
        
        # Calculate faction averages for comparison
        our_members = [stats for stats in data['member_stats'].values() if stats['faction'] == 'Our Faction' and stats['attacks'] > 0]
        enemy_members = [stats for stats in data['member_stats'].values() if stats['faction'] != 'Our Faction' and stats['attacks'] > 0]
        
        our_avg_score = statistics.mean([m['score'] for m in our_members]) if our_members else 0
        enemy_avg_score = statistics.mean([m['score'] for m in enemy_members]) if enemy_members else 0
        
        our_rows = []
        enemy_rows = []
        
        for member_id, stats in data['member_stats'].items():
            if stats['attacks'] > 0:  # Only show members who participated
                # Calculate percentages
                if stats['faction'] == 'Our Faction':
                    hit_percentage = (stats['attacks'] / our_total_attacks) * 100 if our_total_attacks > 0 else 0
                    score_percentage = (stats['score'] / data['our_score']) * 100 if data['our_score'] > 0 else 0
                    # Performance comparison (above/below faction average)
                    performance_vs_avg = ((stats['score'] - our_avg_score) / our_avg_score) * 100 if our_avg_score > 0 else 0
                else:
                    hit_percentage = (stats['attacks'] / enemy_total_attacks) * 100 if enemy_total_attacks > 0 else 0
                    score_percentage = (stats['score'] / data['enemy_score']) * 100 if data['enemy_score'] > 0 else 0
                    # Performance comparison (above/below faction average)
                    performance_vs_avg = ((stats['score'] - enemy_avg_score) / enemy_avg_score) * 100 if enemy_avg_score > 0 else 0
                
                row = {
                    'Members': f'<a href="https://www.torn.com/profiles.php?XID={member_id.replace("enemy_", "")}" target="_blank" style="color: #ffffff; text-decoration: none;">{stats["name"]}</a>',
                    'Level': stats['level'],
                    'Attacks': stats['attacks'],
                    'Hit %': f"{hit_percentage:.2f}%",
                    'Score': self.format_european_number(stats['score']),
                    'Score %': f"{score_percentage:.2f}%",
                    'Avg score/hit': self.format_european_number(stats['avg_score_hit']),
                    'Efficiency': self.format_european_number(stats['efficiency_score']),
                    'Att/Hr': self.format_european_number(stats['attack_frequency']),
                    'Score/Lvl': self.format_european_number(stats['performance_vs_level']),
                    'vs Avg': f"{performance_vs_avg:+.1f}%"
                }
                
                if stats['faction'] == 'Our Faction':
                    our_rows.append(row)
                else:
                    enemy_rows.append(row)
        
        if not our_rows and not enemy_rows:
            return None, None, None, data
        
        # Create separate DataFrames
        our_df = pd.DataFrame(our_rows) if our_rows else pd.DataFrame()
        enemy_df = pd.DataFrame(enemy_rows) if enemy_rows else pd.DataFrame()
        
        # Sort both by score descending (need to convert back to float for sorting)
        if not our_df.empty:
            our_df['_sort_score'] = our_df['Score'].str.replace('.', '').str.replace(',', '.').astype(float)
            our_df = our_df.sort_values('_sort_score', ascending=False)
            our_df = our_df.drop('_sort_score', axis=1)
            
        if not enemy_df.empty:
            enemy_df['_sort_score'] = enemy_df['Score'].str.replace('.', '').str.replace(',', '.').astype(float)
            enemy_df = enemy_df.sort_values('_sort_score', ascending=False)
            enemy_df = enemy_df.drop('_sort_score', axis=1)
        
        return our_df, enemy_df, data
    
    def create_styled_html_report(self, our_df, enemy_df, war_data):
        """Create a styled HTML table report using templates with European formatting and TCT times"""
        
        # War info with TCT times and duration formatting
        war_start = self.convert_to_tct(war_data['war_start'])
        war_end = self.convert_to_tct(war_data['war_end'])
        war_duration_formatted = self.format_duration_hms(war_data['war_duration_hours'])
        
        # Calculate battle stats
        our_hits_per_min = self.calculate_battle_stats(war_data['our_attacks'], war_data['war_duration_hours'])
        our_avg_hit_score = self.calculate_avg_hit_score(war_data['our_score'], war_data['our_attacks'])
        enemy_hits_per_min = self.calculate_battle_stats(war_data['enemy_attacks'], war_data['war_duration_hours'])
        enemy_avg_hit_score = self.calculate_avg_hit_score(war_data['enemy_score'], war_data['enemy_attacks'])
        
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
        our_stats = war_data.get('our_faction_stats', {})
        enemy_stats = war_data.get('enemy_faction_stats', {})
        
        # Create combined table HTML with side-by-side layout and faction colors (EPIC Mafia = GREEN, Enemy = RED/ORANGE)
        tables_html = f"""
        <div class="tables-container">
            <div class="faction-section">
                <h3 style="background: linear-gradient(135deg, #2d5a2d, #4a8b4a); color: white; padding: 15px; border-radius: 8px;">EPIC Mafia</h3>
                <div class="faction-stats our-stats" style="margin-bottom: 15px;">
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(war_data['our_attacks'])}</div>
                        <div class="stat-label">Our Attacks</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(war_data['our_score'])}</div>
                        <div class="stat-label">Our Score</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{our_hits_per_min}</div>
                        <div class="stat-label">Hits/Min</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(our_avg_hit_score)}</div>
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
                <h3 style="background: linear-gradient(135deg, #cc4d1f, #e55a2b); color: white; padding: 15px; border-radius: 8px;">{war_data['enemy_faction_name']}</h3>
                <div class="faction-stats enemy-stats" style="margin-bottom: 15px;">
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(war_data['enemy_attacks'])}</div>
                        <div class="stat-label">Enemy Attacks</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(war_data['enemy_score'])}</div>
                        <div class="stat-label">Enemy Score</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{enemy_hits_per_min}</div>
                        <div class="stat-label">Hits/Min</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(enemy_avg_hit_score)}</div>
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
        
        # Load template file
        try:
            with open('war_report_template.html', 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            print("Template file not found, creating basic template...")
            template = self.get_default_template()
        
        # Replace placeholders with actual data (using European formatting)
        html = template.replace('{{WAR_ID}}', str(war_data['war_info']['war_id']))
        html = html.replace('{{WAR_START}}', war_start)
        html = html.replace('{{WAR_END}}', war_end)
        html = html.replace('{{WAR_DURATION}}', war_duration_formatted)
        html = html.replace('{{TABLE_HTML}}', tables_html)
        
        return html
    
    def get_default_template(self):
        """Fallback template if file not found"""
        return """<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>War Report</title>
        </head>
        <body>
        <h1>War Report {{WAR_ID}}</h1>
        <p>Period: {{WAR_START}} - {{WAR_END}}</p>
        <p>Duration: {{WAR_DURATION}}</p>
        {{TABLE_HTML}}
        </body>
        </html>"""

def main():
    API_KEY = "XrSNtZr7UKlaOXFT"
    FACTION_ID = 40959
    WAR_ID = 26833

    print("Starting Torn War Report Generator...")

    try:
        reporter = TornWarReport(api_key=API_KEY, faction_id=FACTION_ID, war_id=WAR_ID)
        result = reporter.create_report_dataframe()

        if result and len(result) == 3 and (not result[0].empty or not result[1].empty):
            our_df, enemy_df, raw_data = result

            html_report = reporter.create_styled_html_report(our_df, enemy_df, raw_data)
            html_report = html_report.replace(
                "<div class=\"header\">",
                "<div class=\"header\">\n  <div style='text-align:right'><a href='https://epic-mafia.netlify.app/chain_report.html' style='color:#67e8f9;text-decoration:none;font-size:13px;'>→ Go to Chain Report</a></div>"
            )

            with open("war_report.html", "w", encoding="utf-8") as f:
                f.write(html_report)

            print("\n✅ Styled HTML war report saved to 'war_report.html'")
        else:
            print("Failed to generate war report")

    except Exception as e:
        print(f"Error generating war report: {e}")
        import traceback
        traceback.print_exc()

    print("\nStarting Chain Report Generator...")
    try:
        generate_chain_report()
    except Exception as e:
        print(f"Error generating chain report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

