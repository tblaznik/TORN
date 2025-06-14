import requests
import json
from datetime import datetime, timezone, timedelta
import pandas as pd
import locale

class TornWarReport:
    def __init__(self, api_key, faction_id=None, war_id=None):
        self.api_key = api_key
        self.faction_id = faction_id
        self.war_id = war_id
        
    def format_european_number(self, num):
        """Format numbers with European standards: . as thousands separator, , as decimal"""
        if isinstance(num, (int, float)):
            # Convert to string with comma as decimal separator and dot as thousands separator
            formatted = f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            # Remove trailing zeros after decimal comma
            if ',' in formatted:
                formatted = formatted.rstrip('0').rstrip(',')
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
            return f"{hits_per_min:.5g}".replace('.', ',')  # Use European format
        return 0.0
    
    def calculate_avg_hit_score(self, score, attacks):
        """Calculate average score per hit"""
        if score and attacks and attacks > 0:
            return round(score / attacks, 2)
        return 0.0
        
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
        our_faction_data = war_data.get('our_faction', {})
        
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
        
        # Debug: Print the structure of the first member to see what data is available
        if war_members:
            first_member_id = next(iter(war_members))
            first_member_data = war_members[first_member_id]
            print(f"\nDEBUG - First member data structure:")
            print(f"Member ID: {first_member_id}")
            print(f"Member data keys: {list(first_member_data.keys())}")
            print(f"Full member data: {first_member_data}")
            print()
        
        # Debug: Print our faction data structure
        print(f"\nDEBUG - Our faction data keys: {list(our_faction_data.keys())}")
        print(f"Our faction data: {our_faction_data}")
        print()
        
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
            
            avg_score_hit = member_score / member_attacks if member_attacks > 0 else 0
            
            member_stats[member_id] = {
                'name': member_name,
                'level': member_level,
                'attacks': member_attacks,
                'score': member_score,
                'avg_score_hit': avg_score_hit,
                'faction': 'Our Faction',
                'faction_id': self.faction_id
            }
        
        # Process enemy faction members
        for member_id, member_data in enemy_members.items():
            member_name = member_data.get('name', f'ID_{member_id}')
            member_level = member_data.get('level', 0)
            member_attacks = member_data.get('attacks', 0)
            member_score = member_data.get('score', 0)
            
            enemy_total_attacks += member_attacks
            enemy_total_score += member_score
            
            avg_score_hit = member_score / member_attacks if member_attacks > 0 else 0
            
            member_stats[f"enemy_{member_id}"] = {
                'name': member_name,
                'level': member_level,
                'attacks': member_attacks,
                'score': member_score,
                'avg_score_hit': avg_score_hit,
                'faction': enemy_faction_data.get('name', 'Enemy Faction') if enemy_faction_data else 'Enemy Faction',
                'faction_id': enemy_faction_id
            }
        
        print(f"Processed {total_attacks} our attacks with {total_score} our score")
        print(f"Processed {enemy_total_attacks} enemy attacks with {enemy_total_score} enemy score")
        
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
            'war_end': war_end
        }
    
    def create_report_dataframe(self):
        data = self.generate_war_earnings_data()
        if not data:
            return None, None
        
        # Calculate totals first
        our_total_attacks = sum(stats['attacks'] for stats in data['member_stats'].values() if stats['faction'] == 'Our Faction')
        enemy_total_attacks = sum(stats['attacks'] for stats in data['member_stats'].values() if stats['faction'] != 'Our Faction')
        
        our_rows = []
        enemy_rows = []
        
        for member_id, stats in data['member_stats'].items():
            if stats['attacks'] > 0:  # Only show members who participated
                # Calculate percentages
                if stats['faction'] == 'Our Faction':
                    hit_percentage = (stats['attacks'] / our_total_attacks) * 100 if our_total_attacks > 0 else 0
                    score_percentage = (stats['score'] / data['our_score']) * 100 if data['our_score'] > 0 else 0
                else:
                    hit_percentage = (stats['attacks'] / enemy_total_attacks) * 100 if enemy_total_attacks > 0 else 0
                    score_percentage = (stats['score'] / data['enemy_score']) * 100 if data['enemy_score'] > 0 else 0
                
                row = {
                    'Members': f'<a href="https://www.torn.com/profiles.php?XID={member_id.replace("enemy_", "")}" target="_blank" style="color: #ffffff; text-decoration: none;">{stats["name"]}</a>',
                    'Level': stats['level'],
                    'Attacks': stats['attacks'],
                    'Hit %': f"{hit_percentage:.2f}%",
                    'Score': self.format_european_number(stats['score']),
                    'Score %': f"{score_percentage:.2f}%",
                    'Avg score/hit': self.format_european_number(stats['avg_score_hit'])
                }
                
                if stats['faction'] == 'Our Faction':
                    our_rows.append(row)
                else:
                    enemy_rows.append(row)
        
        if not our_rows and not enemy_rows:
            return None, None, data
        
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
        war_duration_hours = (war_data['war_end'] - war_data['war_start']) / 3600
        war_duration_formatted = self.format_duration_hms(war_duration_hours)
        
        # Calculate battle stats
        our_hits_per_min = self.calculate_battle_stats(war_data['our_attacks'], war_duration_hours)
        our_avg_hit_score = self.calculate_avg_hit_score(war_data['our_score'], war_data['our_attacks'])
        enemy_hits_per_min = self.calculate_battle_stats(war_data['enemy_attacks'], war_duration_hours)
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
                        <div class="stat-number">{self.format_european_number(our_hits_per_min)}</div>
                        <div class="stat-label">Hits/Min</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(our_avg_hit_score)}</div>
                        <div class="stat-label">Avg Hit Score</div>
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
                        <div class="stat-number">{self.format_european_number(enemy_hits_per_min)}</div>
                        <div class="stat-label">Hits/Min</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{self.format_european_number(enemy_avg_hit_score)}</div>
                        <div class="stat-label">Avg Hit Score</div>
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
        html = html.replace('{{OUR_ATTACKS}}', self.format_european_number(war_data['our_attacks']))
        html = html.replace('{{OUR_SCORE}}', self.format_european_number(war_data['our_score']))
        html = html.replace('{{ENEMY_ATTACKS}}', self.format_european_number(war_data['enemy_attacks']))
        html = html.replace('{{ENEMY_SCORE}}', self.format_european_number(war_data['enemy_score']))
        html = html.replace('{{OUR_HITS_PER_MIN}}', self.format_european_number(our_hits_per_min))
        html = html.replace('{{OUR_AVG_HIT_SCORE}}', self.format_european_number(our_avg_hit_score))
        html = html.replace('{{ENEMY_HITS_PER_MIN}}', self.format_european_number(enemy_hits_per_min))
        html = html.replace('{{ENEMY_AVG_HIT_SCORE}}', self.format_european_number(enemy_avg_hit_score))
        html = html.replace('{{ENEMY_FACTION_NAME}}', war_data['enemy_faction_name'])
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
        <p>Our Score: {{OUR_SCORE}} vs Enemy: {{ENEMY_SCORE}}</p>
        {{TABLE_HTML}}
        </body>
        </html>"""

def main():
    API_KEY = "XrSNtZr7UKlaOXFT"
    FACTION_ID = 40959
    WAR_ID = 26833
    
    print("Starting Torn War Report Generator...")
    
    try:
        reporter = TornWarReport(API_KEY, FACTION_ID, WAR_ID)
        result = reporter.create_report_dataframe()
        
        if result and len(result) == 3 and (not result[0].empty or not result[1].empty):
            our_df, enemy_df, raw_data = result
            print("\nWAR EARNINGS REPORT GENERATED!")
            print(f"Our Attacks: {reporter.format_european_number(raw_data['our_attacks'])}")
            print(f"Our Score: {reporter.format_european_number(raw_data['our_score'])}")
            print(f"Enemy Attacks: {reporter.format_european_number(raw_data['enemy_attacks'])}")
            print(f"Enemy Score: {reporter.format_european_number(raw_data['enemy_score'])}")
            
            if not our_df.empty:
                print("\nOur Top 10 Members:")
                print(our_df.head(10).to_string(index=False))
            
            if not enemy_df.empty:
                print("\nEnemy Top 10 Members:")
                print(enemy_df.head(10).to_string(index=False))
            
            # Create styled HTML report
            html_report = reporter.create_styled_html_report(our_df, enemy_df, raw_data)
            with open('war_report.html', 'w', encoding='utf-8') as f:
                f.write(html_report)
            print("\n✅ Styled HTML report saved to 'war_report.html'")
            
        else:
            print("Failed to generate report")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()