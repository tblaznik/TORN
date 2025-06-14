import os
import re
import glob
from pathlib import Path

class ChainReportProcessor:
    """
    Processes Torn chain report CSV files and generates HTML reports.
    Reads the single CSV file in the folder and fills the template.
    """
    
    def __init__(self):
        self.faction_name = ""
        self.chain_id = ""
        self.members_data = []
        
    def find_chain_csv(self) -> str:
        """Find the chain report CSV file in current directory."""
        # Look for CSV files with "Chain" in the name
        chain_files = glob.glob("*Chain*.csv")
        if not chain_files:
            # If no "Chain" files, look for any CSV
            csv_files = glob.glob("*.csv")
            if csv_files:
                return csv_files[0]
            return None
        return chain_files[0]
    
    def parse_european_number(self, value: str) -> float:
        """Parse European formatted numbers (comma as decimal, dot as thousands)."""
        if not value or value == '':
            return 0.0
        try:
            # Remove thousands separators (dots) and replace decimal separator (comma with dot)
            clean_value = value.replace('.', '').replace(',', '.')
            return float(clean_value)
        except (ValueError, AttributeError):
            return 0.0
    
    def format_european_number(self, value: float, decimals: int = 0) -> str:
        """Format number using European conventions."""
        if decimals == 0:
            # Format as integer with dot thousands separator
            return f"{int(value):,}".replace(',', '.')
        else:
            # Format with comma decimal separator
            formatted = f"{value:.{decimals}f}"
            parts = formatted.split('.')
            integer_part = f"{int(parts[0]):,}".replace(',', '.')
            return f"{integer_part},{parts[1]}"
    
    def read_csv(self, csv_path: str) -> bool:
        """Read and parse the chain report CSV file."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Split lines and handle Windows line endings
            lines = content.replace('\r\n', '\n').split('\n')
            lines = [line for line in lines if line.strip()]
            
            if len(lines) < 3:
                print("Error: CSV file doesn't have enough lines")
                return False
                
            # Extract faction name from first line
            self.faction_name = lines[0].split(';')[0].strip()
            
            # Extract chain ID from filename
            filename = os.path.basename(csv_path)
            chain_match = re.search(r'(\d+)', filename)
            if chain_match:
                self.chain_id = chain_match.group(1)
            else:
                self.chain_id = "Unknown"
            
            # Get headers from second line
            headers = [h.strip() for h in lines[1].split(';')]
            
            # Process data rows starting from third line
            self.members_data = []
            for line in lines[2:]:
                if not line.strip():
                    continue
                    
                values = [v.strip() for v in line.split(';')]
                
                # Skip if not enough values or empty member name
                if len(values) < len(headers) or not values[0]:
                    continue
                    
                # Create member data dictionary
                member_data = {}
                for i, header in enumerate(headers):
                    member_data[header] = values[i] if i < len(values) else ''
                    
                self.members_data.append(member_data)
                
            print(f"Successfully loaded {len(self.members_data)} members from {self.faction_name}")
            return True
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return False
    
    def calculate_summary_stats(self) -> dict:
        """Calculate summary statistics for the chain report."""
        if not self.members_data:
            return {}
            
        total_members = len(self.members_data)
        total_respect = sum(self.parse_european_number(member.get('Respect', '0')) for member in self.members_data)
        total_attacks = sum(int(member.get('Attacks', '0') or '0') for member in self.members_data)
        total_leave = sum(int(member.get('Leave', '0') or '0') for member in self.members_data)
        total_hosp = sum(int(member.get('Hosp', '0') or '0') for member in self.members_data)
        
        avg_respect = total_respect / total_members if total_members > 0 else 0
        leave_rate = (total_leave / total_attacks * 100) if total_attacks > 0 else 0
        hosp_rate = (total_hosp / total_attacks * 100) if total_attacks > 0 else 0
        
        return {
            'TOTAL_MEMBERS': str(total_members),
            'TOTAL_RESPECT': self.format_european_number(total_respect),
            'TOTAL_ATTACKS': self.format_european_number(total_attacks),
            'AVG_RESPECT': self.format_european_number(avg_respect, 2),
            'LEAVE_RATE': self.format_european_number(leave_rate, 1),
            'HOSP_RATE': self.format_european_number(hosp_rate, 1)
        }
    
    def extract_user_id(self, member_name: str) -> str:
        """Extract user ID from member name format."""
        match = re.search(r'\[(\d+)\]', member_name)
        return match.group(1) if match else None
    
    def generate_table_rows(self) -> str:
        """Generate HTML table rows for all members."""
        if not self.members_data:
            return "<tr><td colspan='15'>No data available</td></tr>"
            
        rows = []
        for member in self.members_data:
            member_name = member.get('Members', '')
            user_id = self.extract_user_id(member_name)
            
            # Create profile link if user ID found
            if user_id:
                member_cell = f'<a href="https://www.torn.com/profiles.php?XID={user_id}" target="_blank" class="member-name">{member_name}</a>'
            else:
                member_cell = member_name
            
            # Create table row
            row = f"""            <tr>
                <td>{member_cell}</td>
                <td>{member.get('Respect', '0')}</td>
                <td>{member.get('Best', '0')}</td>
                <td>{member.get('Avg', '0')}</td>
                <td>{member.get('Attacks', '0')}</td>
                <td>{member.get('Leave', '0')}</td>
                <td>{member.get('Mug', '0')}</td>
                <td>{member.get('Hosp', '0')}</td>
                <td>{member.get('War', '0')}</td>
                <td>{member.get('Assist', '0')}</td>
                <td>{member.get('Retal', '0')}</td>
                <td>{member.get('Overseas', '0')}</td>
                <td>{member.get('Draw', '0')}</td>
                <td>{member.get('Escape', '0')}</td>
                <td>{member.get('Loss', '0')}</td>
            </tr>"""
            
            rows.append(row)
        
        return '\n'.join(rows)
    
    def process_and_generate(self) -> bool:
        """Main processing function - finds CSV, processes it, and generates HTML."""
        # Find the CSV file
        csv_path = self.find_chain_csv()
        if not csv_path:
            print("No chain report CSV file found!")
            return False
        
        print(f"Found CSV file: {csv_path}")
        
        # Read and parse CSV
        if not self.read_csv(csv_path):
            return False
        
        # Load template
        template_path = "chain_report_template.html"
        if not os.path.exists(template_path):
            print(f"Template file not found: {template_path}")
            return False
        
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
        
        # Calculate summary statistics
        summary_stats = self.calculate_summary_stats()
        
        # Generate table rows
        table_rows = self.generate_table_rows()
        
        # Replace template placeholders
        replacements = {
            '{{FACTION_NAME}}': self.faction_name,
            '{{CHAIN_ID}}': self.chain_id,
            '{{TABLE_ROWS}}': table_rows,
            **summary_stats
        }
        
        # Apply all replacements
        html_content = template_content
        for placeholder, value in replacements.items():
            html_content = html_content.replace(placeholder, str(value))
        
        # Write output file
        output_path = "chain_report.html"
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print(f"Chain report generated successfully: {output_path}")
        print(f"Faction: {self.faction_name}")
        print(f"Chain ID: {self.chain_id}")
        print(f"Members: {len(self.members_data)}")
        
        return True


def generate_chain_report():
    """Convenience function to generate chain report."""
    processor = ChainReportProcessor()
    return processor.process_and_generate()


if __name__ == "__main__":
    success = generate_chain_report()
    if success:
        print("✅ Chain report generated successfully!")
    else:
        print("❌ Failed to generate chain report.")
