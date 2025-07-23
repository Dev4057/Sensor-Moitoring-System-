import serial
import csv
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.ticker import MultipleLocator
from datetime import datetime
import re
import os

# --- Configuration ---
SERIAL_PORT = '/dev/ttyUSB1'
BAUD_RATE = 9600
# Save the CSV file inside the 'data' subfolder
CSV_FILE = 'data/data.csv' 

# --- Setup Data Directory ---
# Ensure the 'data' directory exists
os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

# --- Setup Serial Connection ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2) # Wait for Arduino to reset
    print("✅ Connected to Arduino on", SERIAL_PORT)
except serial.SerialException as e:
    print(f"❌ Error: Could not open serial port {SERIAL_PORT}. Please check the connection and port name.")
    print(e)
    exit()

# --- Setup CSV File ---
# Open in 'a' (append) mode and check if the file is empty to write the header
try:
    # Check if file exists and is not empty
    is_file_empty = os.path.getsize(CSV_FILE) == 0
except FileNotFoundError:
    is_file_empty = True

if is_file_empty:
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write header for separate temperature and humidity columns
        writer.writerow(['Timestamp', 'Temperature_C', 'Humidity_Percent'])
    print(f"✅ Created and initialized {CSV_FILE}")

print(f"✅ Logging data to {CSV_FILE}")


# --- Live Visualization ---
def parse_data(line):
    """Parses Temperature and Humidity from the serial line using regex."""
    try:
        temp_match = re.search(r"Temperature: ([\d\.]+)", line)
        hum_match = re.search(r"Humidity: ([\d\.]+)", line)
        
        temp = float(temp_match.group(1)) if temp_match else None
        humidity = float(hum_match.group(1)) if hum_match else None
        
        return temp, humidity
    except (AttributeError, ValueError):
        return None, None

def animate(i):
    """Reads serial, logs data, and updates the plot."""
    # 1. Read from Arduino
    if ser.in_waiting > 0:
        try:
            line = ser.readline().decode('utf-8').strip()
            print(f"Received: {line}")

            # 2. Parse Data
            temp, humidity = parse_data(line)

            if temp is not None and humidity is not None:
                # 3. Log to CSV
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(CSV_FILE, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([timestamp, temp, humidity])
        except Exception as e:
            print(f"Error reading or logging serial data: {e}")
    
    # 4. Update Plot
    try:
        data = pd.read_csv(CSV_FILE)
        if data.empty:
            return # Don't plot if the file is empty

        data['Timestamp'] = pd.to_datetime(data['Timestamp'])
        
        # Limit to the last 30 data points for a clean view
        data = data.tail(30)

        ax1.clear()
        ax2.clear()

        # Plot Temperature on the first subplot (ax1)
        ax1.plot(data['Timestamp'], data['Temperature_C'], color='tab:red', marker='o', linestyle='-')
        ax1.set_ylabel('Temperature (°C)')
        ax1.set_title('Temperature Data')
        
        # --- Set Y-axis ticks for Temperature ---
        if not data.empty:
            min_temp = data['Temperature_C'].min()
            max_temp = data['Temperature_C'].max()
            # Set Y-limits with some padding
            ax1.set_ylim(min_temp - 4, max_temp + 4)
            # Set ticks to be every 3 degrees
            ax1.yaxis.set_major_locator(MultipleLocator(3))
            ax1.grid(axis='y', linestyle='--', alpha=0.7)

        # Plot Humidity on the second subplot (ax2)
        ax2.plot(data['Timestamp'], data['Humidity_Percent'], color='tab:blue', marker='x', linestyle='--')
        ax2.set_ylabel('Humidity (%)')
        ax2.set_xlabel('Time')
        ax2.set_title('Humidity Data')
        ax2.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Improve formatting for the x-axis labels
        plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
        
        fig.suptitle('Live Sensor Monitor', fontsize=16)
        fig.tight_layout(rect=[0, 0.03, 1, 0.95])

    except pd.errors.EmptyDataError:
        # This is expected on the first run, just ignore it.
        pass
    except Exception as e:
        print(f"Plotting Error: {e}")


# --- Main Execution ---
# Create a figure with two subplots stacked vertically that share the same x-axis
fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, sharex=True, figsize=(10, 8))

# Start the animation
ani = FuncAnimation(fig, animate, interval=1000, cache_frame_data=False)

plt.show()

# This code runs after the plot window is closed
ser.close()
print("✅ Serial port closed.")
