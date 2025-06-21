import json
import os
import pandas as pd
import requests
import re
import time
from datetime import datetime


class IntelCollector:
    def __init__(self, api_key, faction_id):
        self.api_key = api_key
        self.faction_id = faction_id
        self.our_members = {}
        self.enemy_members = {}
        self.intel_data = {}
    
    def make_api_request(self, endpoint, api_version="v1"):
        """Make API request to Torn with rate limiting"""
        if api_version == "v1":
            # Check if endpoint already has parameters
            if '?' in endpoint:
                url = f"https://api.torn.com/{endpoint}&key={self.api_key}"
            else:
                url = f"https://api.torn.com/{endpoint}?key={self.api_key}"
        else:
            # Check if endpoint already has parameters
            if '?' in endpoint:
                url = f"https://api.torn.com/{api_version}/{endpoint}&key={self.api_key}"
            else:
                url = f"https://api.torn.com/{api_version}/{endpoint}?key={self.api_key}"
        
        print(f"Making API request to: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                print(f"API Error: {data['error']}")
                return None
                
            # Basic rate limiting - sleep between requests
            time.sleep(0.6)  # ~100 requests per minute limit
            return data
            
        except Exception as e:
            print(f"API request failed: {e}")
            return None
    
    def get_our_faction_members(self):
        """Get our faction member list from API"""
        print("=== FETCHING OUR FACTION MEMBERS ===")
        
        faction_data = self.make_api_request(f"faction/{self.faction_id}/members?striptags=true", "v2")
        if faction_data:
            # v2 API returns members directly as a list
            members_dict = {}
            for member in faction_data['members']:
                member_id = str(member.get('id', ''))
                if member_id:
                    members_dict[member_id] = {
                        'name': member.get('name', f'ID_{member_id}'),
                        'level': member.get('level', 0)
                    }

            self.our_members = members_dict
            print(f"Found {len(self.our_members)} members in our faction")
            return True

        print("Failed to fetch faction members")
        return False

    def load_enemy_members_from_xlsx(self, file_path='enemy_intel.xlsx'):
        """Load enemy member IDs from XLSX file"""
        print("=== LOADING ENEMY INTEL FROM XLSX ===")

        try:
            # Try to read XLSX file
            df = pd.read_excel(file_path)

            # Extract player IDs from name column (assuming first column has names with [ID])
            enemy_list = {}
            name_column = df.columns[0]  # Assume first column has names

            for _, row in df.iterrows():
                name_field = str(row[name_column])

                # Extract ID from brackets using regex
                id_match = re.search(r'\[(\d+)\]', name_field)
                if id_match:
                    player_id = id_match.group(1)
                    # Extract clean name (remove ID brackets)
                    clean_name = re.sub(r'\[\d+\]', '', name_field).strip()

                    enemy_list[player_id] = {
                        'name': clean_name,
                        'level': row.get('Level', 0) if len(df.columns) > 1 else 0,
                        'status': row.get('Status', 'Unknown') if len(df.columns) > 2 else 'Unknown'
                    }

            self.enemy_members = enemy_list
            print(f"Loaded {len(self.enemy_members)} enemy members from XLSX")
            return True

        except FileNotFoundError:
            print(f"Enemy intel file '{file_path}' not found. Please upload enemy member data.")
            return False
        except Exception as e:
            print(f"Error loading enemy intel: {e}")
            return False

    def get_player_intel(self, player_id, player_name, faction_type="our"):
        """Fetch comprehensive intel for a single player"""
        print(f"Collecting intel on {player_name} [{player_id}]...")

        # Get personal stats data
        stats_data = self.make_api_request(f"user/{player_id}/personalstats?cat=all", "v2")
        if not stats_data or 'personalstats' not in stats_data:
            return None

        stats = stats_data['personalstats']

        # Get profile data for level, age, life
        profile_data = self.make_api_request(f"user/{player_id}?selections=profile", "v1")
        profile = {}
        if profile_data:
            profile = profile_data

        # Extract profile information
        level = profile.get('level', 0)
        age_days = profile.get('age', 0)
        life = profile.get('life', {}).get('current', 0) if isinstance(profile.get('life'), dict) else 0

        # Calculate derived metrics
        attacks_won = stats.get('attacking', {}).get('attacks', {}).get('won', 0)
        attacks_lost = stats.get('attacking', {}).get('attacks', {}).get('lost', 0)
        win_loss_ratio = attacks_won / attacks_lost if attacks_lost > 0 else attacks_won

        xanax_taken = stats.get('drugs', {}).get('xanax', 0)
        avg_xanax_per_day = xanax_taken / age_days if age_days > 0 else 0

        # Estimate battle stats (may be hidden)
        battle_stats = stats.get('battle_stats', {})
        total_stats = battle_stats.get('total', 0)
        if total_stats == 0:
            # If hidden, estimate from other indicators
            best_damage = stats.get('attacking', {}).get('damage', {}).get('best', 0)
            if best_damage > 15000:
                estimated_stats = "over 200m"
            elif best_damage > 8000:
                estimated_stats = "100m-200m"
            elif best_damage > 4000:
                estimated_stats = "50m-100m"
            else:
                estimated_stats = "Unknown"
        else:
            estimated_stats = f"{total_stats:,}"

        # Compile comprehensive intel
        intel = {
            # Basic Info
            'member':                  player_name,
            'player_id':               player_id,
            'profile_link':            f"https://www.torn.com/profiles.php?XID={player_id}",
            'level':                   level,
            'age':                     age_days,
            'life':                    life,
            'faction_type':            faction_type,

            # Combat Stats
            'attacks_won':             attacks_won,
            'win_loss_ratio':          round(win_loss_ratio, 3),
            'elo_rating':              stats.get('attacking', {}).get('elo', 0),
            'best_damage_made':        stats.get('attacking', {}).get('damage', {}).get('best', 0),
            'ranked_war_hits':         stats.get('attacking', {}).get('faction', {}).get('ranked_war_hits', 0),

            # Critical Substance Intel
            'energy_drinks_drunk':     stats.get('items', {}).get('used', {}).get('energy_drinks', 0),
            'stat_enhancers_used':     stats.get('items', {}).get('used', {}).get('stat_enhancers', 0),
            'xanax_taken':             xanax_taken,
            'avg_xanax_per_day':       round(avg_xanax_per_day, 2),

            # Activity & Investment
            'time_played_days':        round(stats.get('other', {}).get('activity', {}).get('time', 0) / 86400, 1),
            'current_activity_streak': stats.get('other', {}).get('activity', {}).get('streak', {}).get('current', 0),
            'best_activity_streak':    stats.get('other', {}).get('activity', {}).get('streak', {}).get('best', 0),
            'energy_refills':          stats.get('other', {}).get('refills', {}).get('energy', 0),
            'merits_bought':           stats.get('other', {}).get('merits_bought', 0),
            'donator_days':            stats.get('other', {}).get('donator_days', 0),

            # Battle Capability
            'estimated_battle_stats':  estimated_stats,

            # Additional Intel
            'total_drug_usage':        stats.get('drugs', {}).get('total', 0),
            'overdoses':               stats.get('drugs', {}).get('overdoses', 0),
            'networth_total':          stats.get('networth', {}).get('total', 0),
            'last_updated':            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return intel

    def collect_all_intel(self):
        """Collect intel on all faction members"""
        print("=== STARTING COMPREHENSIVE INTEL COLLECTION ===")

        all_intel = {}

        # Collect intel on our faction members
        print(f"\nCollecting intel on {len(self.our_members)} of our members...")
        for member_id, member_data in self.our_members.items():
            member_name = member_data.get('name', f'ID_{member_id}')
            intel = self.get_player_intel(member_id, member_name, "our")
            if intel:
                all_intel[member_id] = intel

        # Collect intel on enemy faction members
        print(f"\nCollecting intel on {len(self.enemy_members)} enemy members...")
        for member_id, member_data in self.enemy_members.items():
            member_name = member_data.get('name', f'ID_{member_id}')
            intel = self.get_player_intel(member_id, member_name, "enemy")
            if intel:
                all_intel[member_id] = intel

        self.intel_data = all_intel
        print(f"\nIntel collection complete! Gathered data on {len(all_intel)} players.")
        return all_intel

    def save_intel_to_file(self, filename='site/war_intel_data.json'):
        """Save collected intel to JSON file for processing"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.intel_data, f, indent=2, ensure_ascii=False)

        print(f"Intel data saved to {filename}")
    
    def get_intel_summary(self):
        """Generate summary statistics of collected intel"""
        if not self.intel_data:
            return "No intel data collected yet."
        
        our_members = [intel for intel in self.intel_data.values() if intel['faction_type'] == 'our']
        enemy_members = [intel for intel in self.intel_data.values() if intel['faction_type'] == 'enemy']
        
        summary = {
            'total_players': len(self.intel_data),
            'our_members': len(our_members),
            'enemy_members': len(enemy_members),
            'high_xanax_users': len([p for p in self.intel_data.values() if p['avg_xanax_per_day'] > 1.0]),
            'heavy_donors': len([p for p in self.intel_data.values() if p['donator_days'] > 1000]),
            'high_elo_players': len([p for p in self.intel_data.values() if p['elo_rating'] > 2500])
        }
        
        return summary


def collect_intel_data(api_key, faction_id):
    """Collect fresh intel data using the existing system"""
    print("=== COLLECTING WAR INTELLIGENCE ===")
    
    try:
        # Initialize intel collector
        collector = IntelCollector(api_key, faction_id)
        
        # Get our faction members
        if not collector.get_our_faction_members():
            print("Failed to get faction members for intel collection")
            return False
        
        # Load enemy intel if available
        if not collector.load_enemy_members_from_xlsx():
            print("No enemy intel file found. Continuing with our faction only.")
        
        # Collect all intel
        intel_data = collector.collect_all_intel()
        
        # Save intel data
        collector.save_intel_to_file()
        
        # Show summary
        summary = collector.get_intel_summary()
        print("\n=== INTEL COLLECTION SUMMARY ===")
        for key, value in summary.items():
            print(f"{key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"Error collecting intel data: {e}")
        return False

def generate_intel_report_html():
    """Generate the complete intel report HTML with embedded data"""
    
    # Check if JSON data already exists
    json_file_path = 'site/war_intel_data.json'
    
    # Prompt user if data exists
    if os.path.exists(json_file_path):
        print(f"\nFound existing intel data: {json_file_path}")
        file_size = os.path.getsize(json_file_path) / 1024  # KB
        print(f"File size: {file_size:.1f} KB")
        
        choice = input("\nDo you want to re-download intel data? This will take time for ~200 players. (Y/n): ").strip().upper()
        
        if choice == 'Y' or choice == 'YES':
            print("\nRe-downloading intel data...")
            # Here you need to provide your API credentials
            API_KEY = input("Enter your Torn API key: ").strip()
            FACTION_ID = input("Enter your faction ID (or press Enter for 40959): ").strip()
            
            if not FACTION_ID:
                FACTION_ID = 40959
            else:
                FACTION_ID = int(FACTION_ID)
            
            if collect_intel_data(API_KEY, FACTION_ID):
                print("Intel data collection completed!")
            else:
                print("Intel data collection failed! Using existing data...")
        else:
            print("Using existing intel data...")
    else:
        print(f"\nNo existing intel data found at {json_file_path}")
        print("Need to collect intel data first...")
        
        choice = input("Do you want to collect intel data now? (Y/n): ").strip().upper()
        if choice == 'Y' or choice == 'YES':
            API_KEY = input("Enter your Torn API key: ").strip()
            FACTION_ID = input("Enter your faction ID (or press Enter for 40959): ").strip()
            
            if not FACTION_ID:
                FACTION_ID = 40959
            else:
                FACTION_ID = int(FACTION_ID)
            
            if not collect_intel_data(API_KEY, FACTION_ID):
                print("Failed to collect intel data. Exiting.")
                return
        else:
            print("Cannot generate report without intel data. Exiting.")
            return
    
    # Now generate the HTML report
    print("\n=== GENERATING HTML REPORT ===")
    
    # Read the JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            intel_data = json.load(f)
        print(f"Loaded intel data for {len(intel_data)} players")
    except Exception as e:
        print(f"Error reading intel data: {e}")
        return
    
    # Read the HTML template
    template_file = 'intel_template.html'
    if not os.path.exists(template_file):
        print(f"Error: {template_file} not found!")
        return
        
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            html_template = f.read()
        print("Loaded HTML template")
    except Exception as e:
        print(f"Error reading template: {e}")
        return
    
    # Convert the data to a JavaScript object string
    intel_data_js = json.dumps(intel_data, indent=2, ensure_ascii=False)
    
    # Find where to insert the data in the script
    script_marker = "const intelData = {};"
    if script_marker in html_template:
        html_content = html_template.replace(script_marker, f"const intelData = {intel_data_js};")
    else:
        # Fallback: insert after <script> tag
        script_start = html_template.find('<script>')
        if script_start != -1:
            insert_pos = script_start + len('<script>')
            html_content = (
                html_template[:insert_pos] + 
                f'\n        const intelData = {intel_data_js};\n        ' +
                html_template[insert_pos:]
            )
        else:
            print("Error: Could not find where to insert data in template!")
            return
    
    # Ensure site directory exists
    os.makedirs('site', exist_ok=True)
    
    # Write the final HTML file
    output_file = 'site/intel_report.html'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Intel report generated successfully: {output_file}")
        print(f"Report contains data for {len(intel_data)} players")
        print("\nWAR INTELLIGENCE READY!")
        print("Open site/intel_report.html in your browser to view the report.")
    except Exception as e:
        print(f"Error writing HTML file: {e}")

def main():
    """Main function"""
    print("=== TORN WAR INTELLIGENCE SYSTEM ===")
    print("This tool generates comprehensive war intelligence reports.")
    print("It analyzes player data for strategic decision making.\n")
    
    generate_intel_report_html()

if __name__ == "__main__":
    main()