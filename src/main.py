import os
os.environ['TCL_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\artgr\AppData\Local\Programs\Python\Python313\tcl\tk8.6'

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from network_speed import SpeedTester
import platform
import subprocess
import time
import csv
from datetime import datetime, timedelta
import logging
from pathlib import Path
import threading
import json
import os
from ttkthemes import ThemedTk
import sys
import queue
import pystray
from PIL import Image, ImageDraw
import winreg
import ctypes

class NetworkMonitorGUI:
    def __init__(self):
        self.root = ThemedTk(theme="azure")
        self.root.title("Network Monitor")
        self.root.geometry("800x600")
        
        # Configuration with defaults
        self.config = {
            'log_dir': os.path.join(os.path.expanduser('~'), 'NetworkMonitor'),
            'ping_interval': 60,
            'speed_test_interval': 3600,
            'ping_host': '8.8.8.8',
            'run_on_startup': False,
            'minimize_to_tray': True
        }
        
        self.load_config()
        self.setup_gui()
        self.setup_tray()
        
        self.monitoring = False
        self.log_queue = queue.Queue()
        self.update_interval = 1000  # GUI update interval in ms
        self.end_time = None
        
        # Create log directory if it doesn't exist
        os.makedirs(self.config['log_dir'], exist_ok=True)
        
        # Bind window close event
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        
    def create_tray_icon(self):
        """Create a simple icon for the system tray"""
        image = Image.new('RGB', (64, 64), color='white')
        dc = ImageDraw.Draw(image)
        dc.rectangle([16, 16, 48, 48], fill='blue')
        return image
        
    def load_config(self):
        """Load configuration from JSON file"""
        config_path = os.path.join(os.path.expanduser('~'), '.network_monitor_config.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config.update(json.load(f))
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            
    def save_config(self):
        """Save configuration to JSON file"""
        config_path = os.path.join(os.path.expanduser('~'), '.network_monitor_config.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            logging.error(f"Error saving config: {e}")
    
    def setup_gui(self):
        # Create main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings Frame
        settings_frame = ttk.LabelFrame(main_container, text="Settings", padding="5")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Log Directory
        ttk.Label(settings_frame, text="Log Directory:").grid(row=0, column=0, sticky=tk.W)
        self.log_dir_var = tk.StringVar(value=self.config['log_dir'])
        ttk.Entry(settings_frame, textvariable=self.log_dir_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(settings_frame, text="Browse", command=self.browse_log_dir).grid(row=0, column=2)
        
        # Intervals
        ttk.Label(settings_frame, text="Ping Interval (seconds):").grid(row=1, column=0, sticky=tk.W)
        self.ping_interval_var = tk.StringVar(value=str(self.config['ping_interval']))
        ttk.Entry(settings_frame, textvariable=self.ping_interval_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="Speed Test Interval (seconds):").grid(row=2, column=0, sticky=tk.W)
        self.speed_interval_var = tk.StringVar(value=str(self.config['speed_test_interval']))
        ttk.Entry(settings_frame, textvariable=self.speed_interval_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Control Buttons
        control_frame = ttk.Frame(main_container)
        control_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.start_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(control_frame, text="Save Settings", command=self.save_settings).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="View Logs", command=self.view_logs).grid(row=0, column=2, padx=5)
        
        # Status Display
        self.status_var = tk.StringVar(value="Status: Not Monitoring")
        status_label = ttk.Label(main_container, textvariable=self.status_var)
        status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Log Display
        log_frame = ttk.LabelFrame(main_container, text="Recent Events", padding="5")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(3, weight=1)
        
    def browse_log_dir(self):
        directory = filedialog.askdirectory(initialdir=self.log_dir_var.get())
        if directory:
            self.log_dir_var.set(directory)

    def save_settings(self):
        try:
            self.config['log_dir'] = self.log_dir_var.get()
            self.config['ping_interval'] = int(self.ping_interval_var.get())
            self.config['speed_test_interval'] = int(self.speed_interval_var.get())
            self.save_config()
            self.log_queue.put("Settings saved successfully")
        except ValueError:
            self.log_queue.put("Error: Intervals must be valid numbers")

    def toggle_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.start_button.configure(text="Stop Monitoring")
            self.status_var.set("Status: Monitoring Active")
            self.monitor_thread = threading.Thread(target=self.run_monitor)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
        else:
            self.monitoring = False
            self.start_button.configure(text="Start Monitoring")
            self.status_var.set("Status: Monitoring Stopped")
            
    def view_logs(self):
        log_file = os.path.join(self.config['log_dir'], 'network_log.csv')
        if os.path.exists(log_file):
            os.startfile(log_file)
        else:
            self.log_queue.put("No logs found")
    
    def update_log_display(self):
        while True:
            try:
                message = self.log_queue.get_nowait()
                self.log_display.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')}: {message}\n")
                self.log_display.see(tk.END)
            except queue.Empty:
                break
        self.root.after(self.update_interval, self.update_log_display)
        
    def run_monitor(self):
        monitor = NetworkMonitor(
            log_dir=self.config['log_dir'],
            ping_host=self.config['ping_host'],
            log_queue=self.log_queue
        )
        monitor.monitor(
            ping_interval=int(self.ping_interval_var.get()),
            speed_test_interval=int(self.speed_interval_var.get())
        )

    def setup_tray(self):
        """Setup system tray icon and menu"""
        menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Start Monitoring", self.toggle_monitoring_from_tray),
            pystray.MenuItem("Exit", self.quit_app)
        )
        self.icon = pystray.Icon("network_monitor", self.create_tray_icon(), "Network Monitor", menu)
        
    def show_window(self, icon=None):
        """Show the main window"""
        self.root.deiconify()
        self.root.state('normal')
        
    def hide_window(self):
        """Hide the main window"""
        self.root.withdraw()
        if not self.icon.visible:
            self.icon_thread = threading.Thread(target=self.icon.run)
            self.icon_thread.daemon = True
            self.icon_thread.start()
            
    def toggle_monitoring_from_tray(self, icon=None):
        """Toggle monitoring from system tray"""
        self.toggle_monitoring()
        # Update tray menu text
        new_text = "Stop Monitoring" if self.monitoring else "Start Monitoring"
        self.icon.menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem(new_text, self.toggle_monitoring_from_tray),
            pystray.MenuItem("Exit", self.quit_app)
        )
        
    def quit_app(self, icon=None):
        """Properly shut down the application"""
        self.monitoring = False
        if hasattr(self, 'icon'):
            self.icon.stop()
        self.root.quit()
        
    def set_startup(self, enable=True):
        """Set or remove the application from Windows startup"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                               winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE)
            app_path = sys.executable
            
            if enable:
                winreg.SetValueEx(key, "NetworkMonitor", 0, winreg.REG_SZ, f'"{app_path}"')
            else:
                try:
                    winreg.DeleteValue(key, "NetworkMonitor")
                except WindowsError:
                    pass
            
            winreg.CloseKey(key)
            return True
        except WindowsError as e:
            self.log_queue.put(f"Error modifying startup: {str(e)}")
            return False
            
    def setup_gui(self):
        # Create main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Settings Frame
        settings_frame = ttk.LabelFrame(main_container, text="Settings", padding="5")
        settings_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Log Directory
        ttk.Label(settings_frame, text="Log Directory:").grid(row=0, column=0, sticky=tk.W)
        self.log_dir_var = tk.StringVar(value=self.config['log_dir'])
        ttk.Entry(settings_frame, textvariable=self.log_dir_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(settings_frame, text="Browse", command=self.browse_log_dir).grid(row=0, column=2)
        
        # Intervals
        ttk.Label(settings_frame, text="Ping Interval (seconds):").grid(row=1, column=0, sticky=tk.W)
        self.ping_interval_var = tk.StringVar(value=str(self.config['ping_interval']))
        ttk.Entry(settings_frame, textvariable=self.ping_interval_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="Speed Test Interval (seconds):").grid(row=2, column=0, sticky=tk.W)
        self.speed_interval_var = tk.StringVar(value=str(self.config['speed_test_interval']))
        ttk.Entry(settings_frame, textvariable=self.speed_interval_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Run Duration
        ttk.Label(settings_frame, text="Run Duration (hours, 0 for continuous):").grid(row=3, column=0, sticky=tk.W)
        self.duration_var = tk.StringVar(value="0")
        ttk.Entry(settings_frame, textvariable=self.duration_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # Checkboxes for additional options
        self.startup_var = tk.BooleanVar(value=self.config.get('run_on_startup', False))
        ttk.Checkbutton(settings_frame, text="Run on Windows Startup", 
                       variable=self.startup_var, command=self.toggle_startup).grid(row=4, column=0, sticky=tk.W)
        
        self.minimize_var = tk.BooleanVar(value=self.config.get('minimize_to_tray', True))
        ttk.Checkbutton(settings_frame, text="Minimize to System Tray", 
                       variable=self.minimize_var).grid(row=4, column=1, sticky=tk.W)
        
        # Control Buttons
        control_frame = ttk.Frame(main_container)
        control_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="Start Monitoring", command=self.toggle_monitoring)
        self.start_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(control_frame, text="Save Settings", command=self.save_settings).grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="View Logs", command=self.view_logs).grid(row=0, column=2, padx=5)
        
        # Status Display
        self.status_var = tk.StringVar(value="Status: Not Monitoring")
        status_label = ttk.Label(main_container, textvariable=self.status_var)
        status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Timer Display
        self.timer_var = tk.StringVar(value="")
        timer_label = ttk.Label(main_container, textvariable=self.timer_var)
        timer_label.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Log Display
        log_frame = ttk.LabelFrame(main_container, text="Recent Events", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_display = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_display.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(4, weight=1)
        
    def toggle_startup(self):
        """Toggle the application's startup status"""
        success = self.set_startup(self.startup_var.get())
        if success:
            self.config['run_on_startup'] = self.startup_var.get()
            self.save_config()
        
    def on_closing(self):
        """Handle window closing event"""
        if self.minimize_var.get():
            self.hide_window()
        else:
            self.quit_app()
            
    def update_timer(self):
        """Update the countdown timer display"""
        if self.monitoring and self.end_time:
            remaining = self.end_time - datetime.now()
            if remaining.total_seconds() <= 0:
                self.toggle_monitoring()
                self.timer_var.set("Monitoring completed")
            else:
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                seconds = remaining.seconds % 60
                self.timer_var.set(f"Time remaining: {hours:02d}:{minutes:02d}:{seconds:02d}")
                self.root.after(1000, self.update_timer)
        elif self.monitoring:
            self.timer_var.set("Continuous monitoring")
            self.root.after(1000, self.update_timer)
            
    def toggle_monitoring(self):
        """Toggle the monitoring state"""
        if not self.monitoring:
            try:
                duration = float(self.duration_var.get())
                if duration > 0:
                    self.end_time = datetime.now() + timedelta(hours=duration)
                else:
                    self.end_time = None
                
                self.monitoring = True
                self.start_button.configure(text="Stop Monitoring")
                self.status_var.set("Status: Monitoring Active")
                self.monitor_thread = threading.Thread(target=self.run_monitor)
                self.monitor_thread.daemon = True
                self.monitor_thread.start()
                self.update_timer()
            except ValueError:
                self.log_queue.put("Error: Invalid duration value")
        else:
            self.monitoring = False
            self.end_time = None
            self.start_button.configure(text="Start Monitoring")
            self.status_var.set("Status: Monitoring Stopped")
            self.timer_var.set("")

class NetworkMonitor:
    def __init__(self, log_dir, ping_host="8.8.8.8", log_queue=None):
        self.ping_host = ping_host
        self.log_dir = log_dir
        self.log_queue = log_queue
        self.log_file = os.path.join(log_dir, 'network_log.csv')
        self.setup_logging()
        
    def setup_logging(self):
        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(self.log_dir, 'network_events.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Status', 'Ping (ms)', 
                               'Download (Mbps)', 'Upload (Mbps)', 'Event'])
                               
    def check_connection(self):
        """Check if internet connection is available using system ping"""
        try:
            if platform.system().lower() == "windows":
                command = ["ping", "-n", "1", "-w", "1000", self.ping_host]
            else:
                command = ["ping", "-c", "1", "-W", "1", self.ping_host]
                
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
            
            if "time=" in output:  # Successful ping
                ping_time = float(output.split("time=")[1].split("ms")[0].strip())
                return True, ping_time
            return False, None
            
        except subprocess.CalledProcessError:  # Ping failed
            if self.log_queue:
                self.log_queue.put("Network is offline")
            return False, None
        except Exception as e:
            if self.log_queue:
                self.log_queue.put(f"Ping error: {str(e)}")
            return False, None
            
    def measure_speed(self):
        try:
            if self.log_queue:
                self.log_queue.put("Running speed test...")
            st = SpeedTester()
            speed_success, ping_time, download_speed, upload_speed = st.measure_speed()
            
            if speed_success and self.log_queue:
                self.log_queue.put(
                    f"Speed test complete - Ping: {ping_time:.1f}ms, "
                    f"Up: {download_speed:.1f} Mbps, "
                    f"Down: {upload_speed:.1f} Mbps"
                )
            
            return speed_success, ping_time, download_speed, upload_speed
        except Exception as e:
            if self.log_queue:
                self.log_queue.put(f"Speed test error: {str(e)}")
            return False, None, None, None

    def log_data(self, status, ping_time, download_speed, upload_speed, event=""):
        """Log network metrics to CSV"""
        status_text = "Connected" if status else "Disconnected"
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                status_text,
                round(ping_time, 2) if ping_time and ping_time > 0 else "N/A",
                round(download_speed, 2) if download_speed else "N/A",
                round(upload_speed, 2) if upload_speed else "N/A",
                event
            ])
        """Log network metrics to CSV"""
        status_text = "Connected" if status else "Disconnected"
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                status_text,
                round(ping_time, 2) if ping_time else "N/A",
                round(download_speed, 2) if download_speed else "N/A",
                round(upload_speed, 2) if upload_speed else "N/A",
                event
            ])
                
    def monitor(self, ping_interval=60, speed_test_interval=3600):
        """Main monitoring loop"""
        last_speed_test = 0
        last_status = True
        
        if self.log_queue:
            self.log_queue.put(f"Monitoring started - Ping interval: {ping_interval}s, Speed test interval: {speed_test_interval}s")
        
        while True:
            try:
                current_time = time.time()
                
                # Check basic connectivity
                status, ping_time = self.check_connection()
                
                # Determine if we need to run a speed test
                run_speed_test = (current_time - last_speed_test >= speed_test_interval)
                
                if status and run_speed_test:
                    speed_success, ping_time, download_speed, upload_speed = self.measure_speed()
                    if speed_success:
                        last_speed_test = current_time
                else:
                    download_speed = upload_speed = None
                
                # Generate event message
                event = ""
                if status != last_status:
                    event = "Connection Restored" if status else "Connection Lost"
                    if self.log_queue:
                        self.log_queue.put(event)
                    last_status = status
                elif run_speed_test and status:
                    event = "Scheduled Speed Test"
                
                self.log_data(status, ping_time, download_speed, upload_speed, event)
                time.sleep(ping_interval)
                
            except Exception as e:
                if self.log_queue:
                    self.log_queue.put(f"Error: {str(e)}")
                time.sleep(ping_interval)

def main():
    if ctypes.windll.shell32.IsUserAnAdmin():
        app = NetworkMonitorGUI()
        app.update_log_display()
        app.root.mainloop()
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

if __name__ == "__main__":
    main()