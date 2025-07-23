import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime
import os

# --- Configuration ---
CSV_FILE = 'data/data.csv'
REPORTS_DIR = 'reports/'
GRAPH_IMG_PATH = os.path.join(REPORTS_DIR, 'temp_sensor_graph.png')

# Ensure the reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

class PDF(FPDF):
    def header(self):
        # Main Title
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Sensor Data Report', align='C')
        self.ln(7) # Add a small line break

        # Company Name (Subtitle)
        self.set_font('Helvetica', '', 10)
        self.cell(0, 10, 'Pratyag Technocart Pvt. Ltd.', align='C')
        self.ln(15) # Add more space before the content

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_report(start_date=None, end_date=None):
    """
    Generates a PDF report for a specific date range with detailed statistics.
    """
    print("🚀 Starting customized report generation...")

    # 1. Read and Filter Data
    try:
        data = pd.read_csv(CSV_FILE)
        if data.empty:
            raise ValueError("The data file is empty. No report can be generated.")
        
        data['Timestamp'] = pd.to_datetime(data['Timestamp'])

        if start_date and end_date:
            # Ensure user input is timezone-naive before comparison
            start_date = pd.to_datetime(start_date).tz_localize(None)
            end_date = pd.to_datetime(end_date).tz_localize(None)
            mask = (data['Timestamp'] >= start_date) & (data['Timestamp'] <= end_date)
            data = data.loc[mask]
        
        if data.empty:
            raise ValueError("No data found in the selected date range.")

    except FileNotFoundError:
        raise FileNotFoundError(f"The data file '{CSV_FILE}' was not found.")
    except Exception as e:
        print(f"❌ Error reading or filtering data: {e}")
        raise e

    print("✅ Data filtered successfully.")

    # 2. Calculate Detailed Statistics
    temp_stats = data['Temperature_C'].describe()
    hum_stats = data['Humidity_Percent'].describe()
    temp_median = data['Temperature_C'].median()
    hum_median = data['Humidity_Percent'].median()
    temp_std = data['Temperature_C'].std()
    hum_std = data['Humidity_Percent'].std()

    start_time_str = data['Timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = data['Timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
    
    print("✅ Detailed statistics calculated.")

    # 3. Generate and Save Graph
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(10, 6))
    ax1.plot(data['Timestamp'], data['Temperature_C'], color='tab:red', label='Temperature')
    ax1.set_ylabel('Temperature (°C)'); ax1.set_title('Temperature History'); ax1.grid(True, ls='--', alpha=0.6)
    ax2.plot(data['Timestamp'], data['Humidity_Percent'], color='tab:blue', label='Humidity')
    ax2.set_ylabel('Humidity (%)'); ax2.set_xlabel('Timestamp'); ax2.set_title('Humidity History'); ax2.grid(True, ls='--', alpha=0.6)
    plt.xticks(rotation=30, ha='right'); fig.tight_layout()
    plt.savefig(GRAPH_IMG_PATH); plt.close()
    print(f"✅ Graph saved to {GRAPH_IMG_PATH}")

    # 4. Create PDF
    pdf = PDF()
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Data Session Summary', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, f"Report for period: {start_time_str} to {end_time_str}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # Statistics Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Detailed Statistics', 0, 1)
    
    pdf.set_font('Helvetica', '', 10)
    # Headers
    pdf.cell(47.5, 8, 'Statistic', 1, 0, 'C')
    pdf.cell(47.5, 8, 'Temperature (°C)', 1, 0, 'C')
    pdf.cell(47.5, 8, 'Humidity (%)', 1, 0, 'C')
    pdf.cell(47.5, 8, 'Description', 1, 1, 'C')
    # Data Rows
    stats_data = [
        ("Count", f"{temp_stats['count']:.0f}", f"{hum_stats['count']:.0f}", "Number of readings"),
        ("Mean", f"{temp_stats['mean']:.2f}", f"{hum_stats['mean']:.2f}", "Average value"),
        ("Median", f"{temp_median:.2f}", f"{hum_median:.2f}", "Midpoint value"),
        ("Std Dev", f"{temp_std:.2f}", f"{hum_std:.2f}", "Data spread"),
        ("Min", f"{temp_stats['min']:.2f}", f"{hum_stats['min']:.2f}", "Lowest value"),
        ("Max", f"{temp_stats['max']:.2f}", f"{hum_stats['max']:.2f}", "Highest value"),
    ]
    for row in stats_data:
        pdf.cell(47.5, 8, row[0], 1, 0)
        pdf.cell(47.5, 8, row[1], 1, 0)
        pdf.cell(47.5, 8, row[2], 1, 0)
        pdf.cell(47.5, 8, row[3], 1, 1)
    pdf.ln(10)

    # Add Graph
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, 'Historical Data Graph', 0, 1)
    pdf.image(GRAPH_IMG_PATH, x=None, y=None, w=190)
    
    report_filename = f"Sensor_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    pdf.output(report_path)
    
    print(f"✅ PDF report successfully generated: {report_path}")

    os.remove(GRAPH_IMG_PATH)
    print("✅ Temporary graph file removed.")

if __name__ == '__main__':
    # Example of running this script directly
    try:
        generate_report()
    except Exception as e:
        print(str(e))
