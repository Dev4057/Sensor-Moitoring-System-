import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import csv
import time
import re
import os
from datetime import datetime
import threading
import collections
import pandas as pd

# Matplotlib imports for embedding the graph
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# --- Dummy function for report generation if the other file is missing ---
# This is to make the script runnable on its own.
# Replace this with your actual import if you have the file.
try:
    from generate_report import generate_report
except ImportError:
    print("Warning: 'generate_report.py' not found. Using a dummy function.")
    def generate_report(start_date, end_date):
        print(f"Dummy report generated from {start_date} to {end_date}")
        # In a real scenario, you would show a messagebox or handle this.
        # For this example, we'll just print to the console.
        messagebox.showinfo("Report Dummy", f"This is a placeholder for the report from\n{start_date} to {end_date}")


# --- Configuration ---
BAUD_RATE = 9600
DATA_DIR = 'data'
CSV_FILE = os.path.join(DATA_DIR, 'data.csv')
MAX_DATA_POINTS = 30 # Number of points to show on the live graph

class SensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor Monitoring System")
        self.root.geometry("900x650")

        self.is_monitoring = False
        self.alert_active = False
        self.serial_thread = None
        self.ser = None

        # --- For dynamic log history ---
        self.history_window = None
        self.history_tree = None

        # Data storage for the graph
        self.timestamps = collections.deque(maxlen=MAX_DATA_POINTS)
        self.temps = collections.deque(maxlen=MAX_DATA_POINTS)
        self.hums = collections.deque(maxlen=MAX_DATA_POINTS)

        # --- Ensure data directory exists ---
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        # --- Style ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Helvetica', 11), padding=5)
        style.configure('TLabel', font=('Helvetica', 11))
        style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Data.TLabel', font=('Helvetica', 22, 'bold'), foreground='#007BFF')
        style.configure('Alert.TLabel', font=('Helvetica', 22, 'bold'), foreground='white', background='red')
        style.configure('Status.TLabel', font=('Helvetica', 10), padding=5)
        style.configure('TLabelframe.Label', font=('Helvetica', 12, 'bold'))
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))

        # --- GUI Layout ---
        top_frame = ttk.Frame(root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X, expand=False)

        # Connection Controls
        conn_lf = ttk.Labelframe(top_frame, text="Connection", padding=10)
        conn_lf.pack(side=tk.LEFT, padx=10, fill=tk.Y)

        ttk.Label(conn_lf, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.port_var = tk.StringVar()
        self.port_selector = ttk.Combobox(conn_lf, textvariable=self.port_var, state='readonly', width=15)
        self.port_selector.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.refresh_button = ttk.Button(conn_lf, text="Refresh", command=self.update_ports_list)
        self.refresh_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Live Data Display
        data_lf = ttk.Labelframe(top_frame, text="Live Readings", padding=10)
        data_lf.pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        self.temp_var = tk.StringVar(value="-- °C")
        self.hum_var = tk.StringVar(value="-- %")

        ttk.Label(data_lf, text="Temperature:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.temp_label = ttk.Label(data_lf, textvariable=self.temp_var, style='Data.TLabel')
        self.temp_label.grid(row=0, column=1, padx=10, pady=5, sticky='e')
        ttk.Label(data_lf, text="Humidity:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
        ttk.Label(data_lf, textvariable=self.hum_var, style='Data.TLabel').grid(row=1, column=1, padx=10, pady=5, sticky='e')

        # Alerts Section
        alert_lf = ttk.Labelframe(top_frame, text="Alerts", padding=10)
        alert_lf.pack(side=tk.LEFT, padx=10, fill=tk.Y)

        self.min_temp_var = tk.StringVar(value="0")
        self.max_temp_var = tk.StringVar(value="40")

        ttk.Label(alert_lf, text="Min Temp (°C):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(alert_lf, textvariable=self.min_temp_var, width=5).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(alert_lf, text="Max Temp (°C):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(alert_lf, textvariable=self.max_temp_var, width=5).grid(row=1, column=1, padx=5, pady=5)

        # Control Buttons
        button_lf = ttk.Labelframe(top_frame, text="Controls", padding=10)
        button_lf.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)

        self.start_button = ttk.Button(button_lf, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(fill=tk.X, expand=True, padx=5, pady=2)

        self.stop_button = ttk.Button(button_lf, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(fill=tk.X, expand=True, padx=5, pady=2)

        self.report_button = ttk.Button(button_lf, text="Generate Report...", command=self.open_report_dialog)
        self.report_button.pack(fill=tk.X, expand=True, padx=5, pady=2)
        
        self.history_button = ttk.Button(button_lf, text="View Log History", command=self.show_log_history)
        self.history_button.pack(fill=tk.X, expand=True, padx=5, pady=2)

        # Graph Frame
        graph_frame = ttk.Frame(root, padding=10)
        graph_frame.pack(expand=True, fill=tk.BOTH)

        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor='#F0F0F0')
        self.ax_temp = self.fig.add_subplot(211)
        self.ax_hum = self.fig.add_subplot(212, sharex=self.ax_temp)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.status_var = tk.StringVar(value="Status: Select a port and press Start.")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, style='Status.TLabel', relief=tk.SUNKEN, anchor='w')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.update_ports_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_ports_list(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_selector['values'] = ports
        if ports:
            self.port_var.set(ports[0])
            self.update_status("Status: Ready to start monitoring.")
        else:
            self.port_var.set("")
            self.update_status("Status: No COM ports found. Please connect a device.")

    def open_report_dialog(self):
        """Opens a dialog for the user to select a date range for the report."""
        try:
            log_data = pd.read_csv(CSV_FILE)
            if log_data.empty:
                raise pd.errors.EmptyDataError
            min_date_str = pd.to_datetime(log_data['Timestamp'].min()).strftime('%Y-%m-%d %H:%M:%S')
            max_date_str = pd.to_datetime(log_data['Timestamp'].max()).strftime('%Y-%m-%d %H:%M:%S')
        except (FileNotFoundError, pd.errors.EmptyDataError):
            messagebox.showerror("Error", "Log file is empty or not found. Cannot generate report.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Report Options")
        dialog.geometry("400x200")

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(expand=True, fill=tk.BOTH)

        ttk.Label(frame, text="Start Date (YYYY-MM-DD HH:MM:SS):").pack(pady=2)
        start_entry = ttk.Entry(frame, width=30)
        start_entry.insert(0, min_date_str)
        start_entry.pack()

        ttk.Label(frame, text="End Date (YYYY-MM-DD HH:MM:SS):").pack(pady=2)
        end_entry = ttk.Entry(frame, width=30)
        end_entry.insert(0, max_date_str)
        end_entry.pack()

        def do_generate():
            self.update_status("Status: Generating report...")
            try:
                generate_report(start_date=start_entry.get(), end_date=end_entry.get())
                messagebox.showinfo("Success", "PDF report has been generated successfully.", parent=dialog)
                self.update_status("Status: Report generated.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to generate report:\n{e}", parent=dialog)
                self.update_status("Status: Error generating report.")

        ttk.Button(frame, text="Generate", command=do_generate).pack(pady=20)

    def on_history_close(self):
        self.history_window.withdraw()

    def show_log_history(self):
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.deiconify()
            self.load_history_data() # Reload data when showing again
            return

        self.history_window = tk.Toplevel(self.root)
        self.history_window.title("Log History")
        self.history_window.geometry("700x500")
        self.history_window.protocol("WM_DELETE_WINDOW", self.on_history_close)

        cols = ('Timestamp', 'Temperature_C', 'Humidity_Percent')
        self.history_tree = ttk.Treeview(self.history_window, columns=cols, show='headings')
        
        for col in cols:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)
        
        self.load_history_data()

        vsb = ttk.Scrollbar(self.history_window, orient="vertical", command=self.history_tree.yview)
        vsb.pack(side='right', fill='y')
        self.history_tree.configure(yscrollcommand=vsb.set)
        self.history_tree.pack(fill='both', expand=True)

    def load_history_data(self):
        # Clear existing data before loading
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        try:
            with open(CSV_FILE, 'r', newline='') as file:
                reader = csv.reader(file)
                next(reader) # Skip header
                for row in reader:
                    self.history_tree.insert("", "end", values=row)
        except (FileNotFoundError, StopIteration):
            pass # No file or empty file, just show an empty table

    def add_log_entry_to_history(self, row_data):
        if self.history_tree and self.history_window and self.history_window.winfo_exists():
            self.history_tree.insert("", "end", values=row_data)
            self.history_tree.yview_moveto(1.0)

    def start_monitoring(self):
        if not self.port_var.get():
            messagebox.showerror("Connection Error", "No COM port selected.")
            return

        self.is_monitoring = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.report_button.config(state=tk.DISABLED)
        self.port_selector.config(state=tk.DISABLED)
        self.refresh_button.config(state=tk.DISABLED)
        self.update_status("Status: Connecting to device...")

        self.timestamps.clear(); self.temps.clear(); self.hums.clear()
        
        self.serial_thread = threading.Thread(target=self.serial_worker, daemon=True)
        self.serial_thread.start()
        self.update_graph()

    def stop_monitoring(self):
        self.is_monitoring = False
        if self.serial_thread and self.serial_thread.is_alive():
            # No need to join a daemon thread, it will exit with the app
            pass
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.report_button.config(state=tk.NORMAL)
        self.port_selector.config(state='readonly')
        self.refresh_button.config(state=tk.NORMAL)
        self.update_status("Status: Monitoring stopped.")
        
    def update_graph(self):
        if not self.is_monitoring: return

        self.ax_temp.clear(); self.ax_hum.clear()

        if self.timestamps:
            self.ax_temp.plot(self.timestamps, self.temps, color='tab:red', marker='o', ls='-')
            self.ax_hum.plot(self.timestamps, self.hums, color='tab:blue', marker='x', ls='--')

        self.ax_temp.set_title("Live Temperature"); self.ax_temp.set_ylabel("Temp (°C)"); self.ax_temp.grid(True, ls='--', alpha=0.6)
        self.ax_hum.set_title("Live Humidity"); self.ax_hum.set_ylabel("Humidity (%)"); self.ax_hum.grid(True, ls='--', alpha=0.6)
        
        self.ax_hum.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        self.fig.autofmt_xdate()
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw()
        
        self.root.after(1000, self.update_graph)

    def serial_worker(self):
        """Handles serial connection, reading, and auto-reconnecting."""
        while self.is_monitoring:
            if self.ser is None or not self.ser.is_open:
                try:
                    selected_port = self.port_var.get()
                    self.update_status(f"Status: Connecting to {selected_port}...")
                    self.ser = serial.Serial(selected_port, BAUD_RATE, timeout=1)
                    time.sleep(2) # Wait for connection to establish
                    self.update_status("Status: Connected and Monitoring...")
                except serial.SerialException:
                    self.update_status("Status: Connection Failed! Retrying...")
                    time.sleep(3) # Wait before retrying
                    continue # Loop back to try connecting again
            else:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        temp, humidity = self.parse_data(line)
                        if temp is not None:
                            self.process_sensor_data(temp, humidity)
                except serial.SerialException:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                    self.ser = None
                    self.update_status("Status: Connection Lost! Reconnecting...")
                    print("Serial connection lost during read.")
                except Exception as e:
                    print(f"An unexpected error occurred while reading: {e}")

        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial port closed.")

    def process_sensor_data(self, temp, humidity):
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = (timestamp_str, f"{temp:.2f}", f"{humidity:.2f}")

        self.timestamps.append(datetime.now())
        self.temps.append(temp)
        self.hums.append(humidity)
        
        self.root.after(0, self.update_gui_labels, temp, humidity)
        self.root.after(0, self.add_log_entry_to_history, row_data)
        self.root.after(0, self.check_alerts, temp)
        
        self.log_to_csv(row_data)

    def check_alerts(self, current_temp):
        try:
            min_val = float(self.min_temp_var.get())
            max_val = float(self.max_temp_var.get())
        except ValueError:
            self.update_status("Status: Invalid alert threshold!", once=True)
            return

        is_alert = not (min_val <= current_temp <= max_val)
        if is_alert != self.alert_active:
            self.alert_active = is_alert
            new_style = 'Alert.TLabel' if is_alert else 'Data.TLabel'
            self.temp_label.config(style=new_style)
            if is_alert:
                self.update_status("Status: !!! TEMPERATURE ALERT !!!")
            else:
                # Only revert status if we are not in another state (like reconnecting)
                if "Monitoring" in self.status_var.get() or "ALERT" in self.status_var.get():
                    self.update_status("Status: Connected and Monitoring...")

    def parse_data(self, line):
        try:
            # This regex is more robust to variations in spacing and wording
            temp_match = re.search(r"Temperature:\s*([\d\.]+)", line)
            hum_match = re.search(r"Humidity:\s*([\d\.]+)", line)
            if temp_match and hum_match:
                return float(temp_match.group(1)), float(hum_match.group(1))
        except (AttributeError, ValueError):
            return None, None
        return None, None

    def update_gui_labels(self, temp, humidity):
        self.temp_var.set(f"{temp:.2f} °C"); self.hum_var.set(f"{humidity:.2f} %")

    def update_status(self, text, once=False):
        def do_update():
            if once and self.status_var.get() == text:
                return
            self.status_var.set(text)
        self.root.after(0, do_update)

    def log_to_csv(self, row_data):
        file_exists = os.path.isfile(CSV_FILE)
        try:
            with open(CSV_FILE, 'a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists or os.path.getsize(CSV_FILE) == 0:
                    writer.writerow(['Timestamp', 'Temperature_C', 'Humidity_Percent'])
                writer.writerow(row_data)
        except IOError as e: print(f"Error writing to CSV: {e}")

    def on_closing(self):
        if self.is_monitoring:
            if messagebox.askyesno("Exit", "Monitoring is active. Are you sure you want to exit?"):
                self.is_monitoring = False # This will signal the thread to stop
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = SensorApp(root)
    root.mainloop()
