import requests
import json
import pandas as pd
import os
import re
from datetime import datetime, timezone, timedelta
from war_report import generate_war_report_content
from chain_report import generate_chain_report_content
from earnings_calculator import calculate_earnings_content
from intel_report import *


class TornReportGenerator:
    def __init__(self, api_key, faction_id=None, war_id=None):
        self.api_key = api_key
        self.faction_id = faction_id
        self.war_id = war_id
        
        # Data storage
        self.war_data = None
        self.chain_data = None
        self.saves_data = None
        self.complete_chain_data = None
        self.intel_data = None
        
        # Data availability flags
        self.war_available = False
        self.chain_available = False
        self.saves_available = False
        
        # Templates
        self.templates = {}
    
    def make_api_request(self, endpoint, api_version="v1"):
        """Make API request to Torn"""
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
    
    def load_war_data(self):
        """Fetch war data from API"""
        print("=== LOADING WAR DATA ===")
        
        # Check if war_id is None
        if self.war_id is None:
            print("War ID is None - war hasn't started yet")
            self.war_available = False
            return True  # Not a failure, just no war yet
        
        # Get faction info if not provided
        if not self.faction_id:
            user_data = self.make_api_request("user/?selections=profile", "v1")
            if user_data and 'faction' in user_data:
                self.faction_id = user_data['faction']['faction_id']
                print(f"Found faction ID: {self.faction_id}")
            else:
                print("Could not determine faction ID")
                return False
        
        # Get specific war data
        war_data = self.make_api_request(f"torn/{self.war_id}?selections=rankedwarreport", "v1")
        
        if war_data and 'rankedwarreport' in war_data:
            report = war_data['rankedwarreport']
            factions = report.get('factions', {})
            
            if str(self.faction_id) in factions:
                print(f"Found our faction {self.faction_id}")
                our_faction = factions[str(self.faction_id)]
                war_info = report.get('war', {})
                
                self.war_data = {
                    'war_id': self.war_id,
                    'war_info': report,
                    'start': war_info.get('start', 0),
                    'end': war_info.get('end', 0),
                    'our_faction': our_faction,
                    'factions': factions
                }
                self.war_available = True
                print("War data loaded successfully")
                return True
            else:
                print(f"Faction {self.faction_id} not in this war")
        
        print("Failed to load war data")
        self.war_available = False
        return True  # Not a critical failure
    
    def load_chain_data(self):
        """Load chain report CSV"""
        print("=== LOADING CHAIN DATA ===")
        
        files = [f for f in os.listdir('.') if f.endswith('.csv') and 'Chain Report' in f]
        if not files:
            print("No Chain Report CSV file found.")
            self.chain_available = False
            return True  # Not a failure, just no data
        
        try:
            df = pd.read_csv(files[0], sep=';', skiprows=1, encoding='utf-8')
            df.columns = [
                "Member", "Respect", "Best", "Avg", "Attacks", "Leave", "Mug",
                "Hosp", "War", "Assist", "Retal", "Overseas", "Draw", "Escape", "Loss"
            ]
            
            # Convert numbers properly handling European formatting
            def convert_european_number(value_str):
                value_str = str(value_str).strip()
                if not value_str or value_str == 'nan':
                    return 0.0
                # European format: . as thousands separator, , as decimal separator
                value_str = value_str.replace('.', '').replace(',', '.')
                return float(value_str)
            
            # Convert numeric columns
            for col in df.columns[1:]:
                df[col] = df[col].apply(convert_european_number)
            
            self.chain_data = df
            self.chain_available = True
            print(f"Chain data loaded: {len(df)} members")
            return True
            
        except Exception as e:
            print(f"Error loading chain data: {e}")
            self.chain_available = False
            return True  # Not a critical failure
    
    def load_saves_data(self):
        """Load saves CSV"""
        print("=== LOADING SAVES DATA ===")
        
        saves_df = None
        if os.path.exists('saves.xlsx'):
            print("Reading saves from XLSX file...")
            try:
                saves_df = pd.read_excel('saves.xlsx')
                self.saves_available = True
            except Exception as e:
                print(f"Error reading saves XLSX: {e}")
                self.saves_available = False
        elif os.path.exists('saves.csv'):
            print("Reading saves from CSV file...")
            try:
                saves_df = pd.read_csv('saves.csv', sep=';', encoding='utf-8')
                self.saves_available = True
            except Exception as e:
                print(f"Error reading saves CSV: {e}")
                self.saves_available = False
        else:
            print("No saves file found.")
            self.saves_available = False
        
        if saves_df is not None:
            print(f"Saves data loaded: {len(saves_df)} rows")
            self.saves_data = saves_df
            return True
        else:
            print("Using empty save data.")
            self.saves_data = pd.DataFrame(columns=['Member', 'Saves', 'Save_Score'])
            return True
    
    def create_complete_chain_data(self):
        """Merge chain data with war data and saves data to create complete dataset"""
        print("=== CREATING COMPLETE CHAIN DATA ===")
        
        if not self.chain_available:
            print("No chain data available - skipping chain data creation")
            return True
        
        df = self.chain_data.copy()
        
        # Extract war respect data from API if available
        war_respect_data = {}
        if self.war_available and self.war_data:
            war_members = self.war_data['our_faction'].get('members', {})
            
            for member_id, member_data in war_members.items():
                member_name = member_data.get('name', f'ID_{member_id}')
                war_respect = member_data.get('score', 0)
                war_respect_data[member_name] = war_respect
            
            print(f"Got war respect data for {len(war_respect_data)} members")
        else:
            print("No war data available - using total respect as fallback")
        
        # Clean member names and match with war data
        def clean_member_name(name):
            # Remove ID brackets first
            clean = re.sub(r'\[\d+\]', '', name).strip()
            
            # Handle duplicated names like "JlambJLAMB" -> "Jlamb"
            if len(clean) > 0:
                mid = len(clean) // 2
                first_half = clean[:mid]
                second_half = clean[mid:]
                
                if first_half.upper() == second_half:
                    return first_half
            
            return clean
        
        # Add war respect column
        df['War_Respect'] = 0.0
        matches_found = 0
        
        for i, row in df.iterrows():
            member_name_original = row['Member']
            clean_name = clean_member_name(member_name_original)
            
            # Try to find match in war data
            found_match = False
            if war_respect_data and clean_name in war_respect_data:
                df.at[i, 'War_Respect'] = war_respect_data[clean_name]
                matches_found += 1
                found_match = True
            elif war_respect_data:
                # Try case-insensitive matching
                for war_name in war_respect_data.keys():
                    if clean_name.lower() == war_name.lower():
                        df.at[i, 'War_Respect'] = war_respect_data[war_name]
                        matches_found += 1
                        found_match = True
                        break
            
            if not found_match:
                # Fallback: use total respect if not found in war data
                df.at[i, 'War_Respect'] = df.at[i, 'Respect']
                print(f"NO MATCH: {member_name_original} -> using total respect as fallback")
        
        if war_respect_data:
            print(f"Successfully matched {matches_found}/{len(df)} members with war data")
        
        # Calculate outside attacks
        df["Outside"] = df["Attacks"] - df["War"]
        
        # Merge with saves data if available
        if self.saves_available and self.saves_data is not None and not self.saves_data.empty:
            # Clean member names in saves data for matching
            self.saves_data['Clean_Member'] = self.saves_data['Member'].apply(clean_member_name)
            df['Clean_Member'] = df['Member'].apply(clean_member_name)
            
            # Merge on cleaned names
            merged_df = df.merge(self.saves_data[['Clean_Member', 'Saves', 'Save_Score']], 
                               on='Clean_Member', how='left')
            
            # Fill NaN values with 0 for members who didn't save
            merged_df['Saves'] = merged_df['Saves'].fillna(0)
            merged_df['Save_Score'] = merged_df['Save_Score'].fillna(0)
            
            df = merged_df.drop('Clean_Member', axis=1)
            print(f"Merged saves data: {df['Saves'].sum()} total saves")
        else:
            # Add empty save columns
            df['Saves'] = 0
            df['Save_Score'] = 0
            print("No saves data to merge")
        
        self.complete_chain_data = df
        print(f"Complete chain data created: {len(df)} members")
        return True
    
    def collect_intel_data(self):
        """Collect war intelligence data"""
        print("=== COLLECTING WAR INTELLIGENCE ===")
        
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
                return self._collect_fresh_intel_data()
            else:
                print("Using existing intel data...")
                return True
        else:
            print(f"\nNo existing intel data found at {json_file_path}")
            print("Need to collect intel data first...")
            
            choice = input("Do you want to collect intel data now? (Y/n): ").strip().upper()
            if choice == 'Y' or choice == 'YES':
                return self._collect_fresh_intel_data()
            else:
                print("Skipping intel collection...")
                return True
    
    def _collect_fresh_intel_data(self):
        """Actually collect the intel data"""
        try:
            # Initialize intel collector
            collector = IntelCollector(self.api_key, self.faction_id)
            
            # Get our faction members
            if not collector.get_our_faction_members():
                print("Failed to get faction members for intel collection")
                return False
            
            # Load enemy intel if available
            if not collector.load_enemy_members_from_xlsx():
                print("No enemy intel file found. Continuing with our faction only.")
            
            # Collect all intel
            self.intel_data = collector.collect_all_intel()
            
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
    
    def load_templates(self):
        """Load all HTML templates"""
        print("=== LOADING TEMPLATES ===")
        
        template_files = {
            'index': 'index_template.html',
            'war_report': 'war_report_template.html',
            'chain_report': 'chain_report_template.html',
            'earnings_report': 'earnings_report_template.html',
            'intel_report': 'intel_template.html',
            'methodology': 'methodology_template.html'
        }
        
        for name, filename in template_files.items():
            try:
                with open(os.path.join('templates', filename), 'r', encoding='utf-8') as f:
                    self.templates[name] = f.read()
                print(f"Loaded template: {filename}")
            except FileNotFoundError:
                print(f"Template not found: {filename}")
                self.templates[name] = self.get_fallback_template(name)
        
        return True
    
    def get_fallback_template(self, template_name):
        """Provide fallback templates if files don't exist"""
        fallbacks = {
            'index': '''<!DOCTYPE html>
<html><head><title>Torn Reports</title></head>
<body><h1>Torn Reports</h1>
<ul>
<li><a href="intel_report.html">War Intel</a></li>
<li><a href="war_report.html">War Report</a></li>
<li><a href="chain_report.html">Chain Report</a></li>
<li><a href="earnings_report.html">Earnings Report</a></li>
<li><a href="methodology.html">Methodology</a></li>
</ul></body></html>''',
            'methodology': '''<!DOCTYPE html>
<html><head><title>Methodology</title></head>
<body><h1>Methodology</h1>
<p>Calculation explanations will go here.</p>
<a href="index.html">Back to Index</a>
</body></html>'''
        }
        return fallbacks.get(template_name, '<html><body><h1>Template Missing</h1></body></html>')
    
    def generate_all_reports(self):
        """Generate content for all reports"""
        print("=== GENERATING REPORTS ===")
        
        # Generate war intel content first (most important)
        try:
            intel_content = generate_intel_report_content()
        except:
            intel_content = None
            print("Intel report generation skipped or failed")
        
        # Generate war report content
        if self.war_available:
            war_content = generate_war_report_content(self.war_data)
        else:
            war_content = None
        
        # Generate chain report content  
        if self.chain_available:
            chain_content = generate_chain_report_content(self.complete_chain_data)
        else:
            chain_content = None
        
        # Generate earnings content
        if self.chain_available and (self.saves_available or not self.saves_data.empty):
            earnings_content = calculate_earnings_content(self.complete_chain_data, total_caches=4209000000.00)
        else:
            earnings_content = None
        
        return {
            'intel': intel_content,
            'war': war_content,
            'chain': chain_content,
            'earnings': earnings_content
        }
    
    def save_html_files(self, report_contents):
        """Fill templates and save HTML files"""
        print("=== SAVING HTML FILES ===")
        
        # Create site directory if it doesn't exist
        os.makedirs('site', exist_ok=True)
        
        # Save index page
        with open("site/index.html", "w", encoding="utf-8") as f:
            f.write(self.templates['index'])
        print("Saved: index.html")
        
        # Save war intel report (generate with embedded data)
        self._generate_intel_html()
        print("Saved: intel_report.html")
        
        # Save war report
        war_html = self.templates['war_report']
        if report_contents['war'] is not None:
            # Replace war-specific placeholders
            war_html = war_html.replace('{{WAR_ID}}', str(self.war_id))
            war_html = war_html.replace('{{TABLE_HTML}}', report_contents['war']['table_html'])
            war_html = war_html.replace('{{WAR_START}}', report_contents['war']['war_start'])
            war_html = war_html.replace('{{WAR_END}}', report_contents['war']['war_end'])
            war_html = war_html.replace('{{WAR_DURATION}}', report_contents['war']['war_duration'])
        else:
            # Show "war hasn't started" message
            no_war_message = '''
            <div class="war-info">
                <h3>War Status</h3>
                <p><strong>Status:</strong> War hasn't started yet</p>
                <p>War data will be available once the ranked war begins.</p>
            </div>
            '''
            war_html = war_html.replace('{{WAR_ID}}', 'N/A')
            war_html = war_html.replace('{{TABLE_HTML}}', no_war_message)
            war_html = war_html.replace('{{WAR_START}}', 'N/A')
            war_html = war_html.replace('{{WAR_END}}', 'N/A')
            war_html = war_html.replace('{{WAR_DURATION}}', 'N/A')
        
        with open("site/war_report.html", "w", encoding="utf-8") as f:
            f.write(war_html)
        print("Saved: war_report.html")
        
        # Save chain report
        chain_html = self.templates['chain_report']
        if report_contents['chain'] is not None:
            chain_html = chain_html.replace('{{CHAIN_TABLE}}', report_contents['chain']['table_html'])
        else:
            no_chain_message = '''
            <div class="header">
                <h1>Chain Report</h1>
            </div>
            <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.8) 0%, rgba(45, 45, 45, 0.6) 100%); border: 2px solid #556B2F; border-radius: 15px; margin: 20px 0;">
                <h3 style="color: #FFD700; margin-bottom: 20px;">No Chain Report Available</h3>
                <p style="color: #d4c5a0;">Please upload a Chain Report CSV file to view chain statistics.</p>
            </div>
            '''
            chain_html = chain_html.replace('{{CHAIN_TABLE}}', no_chain_message)
        
        with open("site/chain_report.html", "w", encoding="utf-8") as f:
            f.write(chain_html)
        print("Saved: chain_report.html")
        
        # Save earnings report
        earnings_html = self.templates['earnings_report']
        if report_contents['earnings'] is not None:
            for key, value in report_contents['earnings']['summary'].items():
                placeholder = '{{' + key.upper() + '}}'
                earnings_html = earnings_html.replace(placeholder, str(value))
            earnings_html = earnings_html.replace('{{EARNINGS_TABLE}}', report_contents['earnings']['table_html'])
        else:
            no_earnings_message = '''
            <div class="header">
                <h1>Earnings Estimate</h1>
            </div>
            <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, rgba(26, 26, 26, 0.8) 0%, rgba(45, 45, 45, 0.6) 100%); border: 2px solid #DAA520; border-radius: 15px; margin: 20px 0;">
                <h3 style="color: #FFD700; margin-bottom: 20px;">Data Not Available</h3>
                <p style="color: #d4c5a0;">Earnings calculations require both Chain Report and Saves data.</p>
                <p style="color: #d4c5a0;">Chain Available: ''' + ('Yes' if self.chain_available else 'No') + '''</p>
                <p style="color: #d4c5a0;">Saves Available: ''' + ('Yes' if self.saves_available else 'No') + '''</p>
            </div>
            '''
            # Replace all placeholders with N/A
            placeholders = ['{{TOTAL_CACHES}}', '{{TAX_AMOUNT}}', '{{TOTAL_PAYOUT}}', '{{TOTAL_HITS}}', 
                          '{{TOTAL_SCORE}}', '{{AVG_SCORE_HIT}}', '{{TOTAL_SAVES}}', '{{TOTAL_SAVE_SCORE}}', 
                          '{{SAVE_PAY}}', '{{PAY_HIT}}', '{{PAY_SCORE}}', '{{RESPECT_WEIGHT}}', '{{HIT_WEIGHT}}', 
                          '{{MOD_SCORE}}', '{{MOD_HIT}}', '{{RESPECT_POOL}}', '{{HIT_POOL}}', '{{TOTAL_MEMBERS}}']
            for placeholder in placeholders:
                earnings_html = earnings_html.replace(placeholder, 'N/A')
            earnings_html = earnings_html.replace('{{EARNINGS_TABLE}}', no_earnings_message)
        
        with open("site/earnings_report.html", "w", encoding="utf-8") as f:
            f.write(earnings_html)
        print("Saved: earnings_report.html")
        
        # Save methodology
        with open("site/methodology.html", "w", encoding="utf-8") as f:
            f.write(self.templates['methodology'])
        print("Saved: methodology.html")

    def _generate_intel_html(self):
        """Generate intel HTML with embedded data"""
        json_file_path = 'site/war_intel_data.json'

        if not os.path.exists(json_file_path):
            print("No intel data found, creating placeholder intel report...")
            with open("site/intel_report.html", "w", encoding="utf-8") as f:
                f.write(self.templates['intel_report'])
            return

        try:
            # Read the JSON data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                intel_data = json.load(f)

            # Convert the data to a JavaScript object string
            intel_data_js = json.dumps(intel_data, indent=2, ensure_ascii=False)

            # Base template
            html_template = self.templates['intel_report']

            # Simple replacement of the marker
            html_content = html_template.replace('const intelData = {};', f'const intelData = {intel_data_js};')

            # Write the final HTML file
            with open("site/intel_report.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("Saved: intel_report.html with intel data")

        except Exception as e:
            print(f"Error generating intel HTML: {e}")
            with open("site/intel_report.html", "w", encoding="utf-8") as f:
                f.write(self.templates['intel_report'])


    def run(self):
        """Main execution flow"""
        print("Starting Torn Report Generator...")
        
        # Collect intelligence data first (with prompt system)
        if not self.collect_intel_data():
            print("Intel data collection failed. Continuing without intelligence...")
        
        # Load all other data
        if not self.load_war_data():
            print("Failed to load war data. Continuing...")
            
        if not self.load_chain_data():
            print("Failed to load chain data. Continuing...")
            
        if not self.load_saves_data():
            print("Failed to load saves data. Continuing...")
        
        # Create complete dataset only if chain data is available
        if self.chain_available:
            if not self.create_complete_chain_data():
                print("Failed to create complete chain data. Continuing...")
        
        # Load templates
        if not self.load_templates():
            print("Failed to load templates. Exiting.")
            return False
        
        # Generate all reports
        report_contents = self.generate_all_reports()
        
        # Save HTML files
        self.save_html_files(report_contents)
        
        print("All reports generated successfully!")
        print("\n=== STRATEGIC INTELLIGENCE READY ===")
        print("War Intel: intel_report.html - CRITICAL for target selection")
        print("War Report: war_report.html - Performance analysis")
        print("Chain Report: chain_report.html - Attack breakdown")
        print("Earnings: earnings_report.html - Payout calculations")
        
        # Display data availability status
        print(f"\nData Availability:")
        print(f"War Data: {'Available' if self.war_available else 'Not Available (war hasn\'t started)'}")
        print(f"Chain Data: {'Available' if self.chain_available else 'Not Available (no CSV file)'}")
        print(f"Saves Data: {'Available' if self.saves_available else 'Not Available (no saves file)'}")
        
        return True


def main():
    API_KEY = "XrSNtZr7UKlaOXFT"
    FACTION_ID = 40959
    WAR_ID = None  # Set to None when war hasn't started yet

    print("=== EPIC MAFIA WAR INTELLIGENCE SYSTEM ===")
    print("Collecting comprehensive intelligence data...")
    print("This includes personal stats, xanax usage, combat effectiveness, and more!")
    
    generator = TornReportGenerator(api_key=API_KEY, faction_id=FACTION_ID, war_id=WAR_ID)
    success = generator.run()
    
    if success:
        print("\nWAR INTELLIGENCE COLLECTION COMPLETE!")
        print("Critical intel now available for strategic decision making.")
        print("Check intel_report.html for comprehensive player analysis.")
    else:
        print("\nReport generation failed. Check the logs above.")


if __name__ == "__main__":
    main()