import logging
import requests
import time
import subprocess
import platform
from typing import Tuple, Optional

class SpeedTester:
    def __init__(self):
        self.download_sizes = [1000000, 5000000, 10000000]  # 1MB, 5MB, 10MB
        self.download_url = "https://speed.cloudflare.com/__down?bytes="
        self.upload_url = "https://speed.cloudflare.com/__up"
        self.timeout = 10  # seconds
        self.ping_host = "8.8.8.8"  # Google DNS

    def check_connection(self) -> bool:
        """Check if internet connection is available"""
        try:
            if platform.system().lower() == "windows":
                command = ["ping", "-n", "1", "-w", "1000", self.ping_host]
            else:
                command = ["ping", "-c", "1", "-W", "1", self.ping_host]
                
            subprocess.check_output(command, stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            logging.error("Network appears to be offline")
            return False
        except Exception as e:
            logging.error(f"Connection check error: {str(e)}")
            return False

    def measure_speed(self) -> Tuple[bool, Optional[float], Optional[float], Optional[float]]:
        try:
            logging.info("Starting speed test...")
            
            # Check connection first
            if not self.check_connection():
                return False, None, None, None
            
            # Test download speed
            download_speed = self.test_download()
            
            # Test upload speed
            upload_speed = self.test_upload()
            
            # Quick ping test
            ping = self.get_ping()
            
            logging.info(f"Speed test complete - Ping: {ping:.1f}ms, Down: {download_speed:.1f}Mbps, Up: {upload_speed:.1f}Mbps")
            return True, ping, download_speed, upload_speed
            
        except Exception as e:
            logging.error(f"Speed test error: {str(e)}")
            return False, None, None, None

    def get_ping(self) -> float:
        """Get ping time in milliseconds"""
        try:
            response = requests.get(f"{self.download_url}1000", timeout=self.timeout)
            return response.elapsed.total_seconds() * 1000
        except:
            return 0.0

    def test_download(self) -> float:
        download_speed = 0
        for size in self.download_sizes:
            url = f"{self.download_url}{size}"
            start_time = time.time()
            response = requests.get(url, stream=True, timeout=self.timeout)
            downloaded = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded += len(chunk)
                    if time.time() - start_time > self.timeout:
                        break
            
            download_time = time.time() - start_time
            if download_time > 0:
                current_speed = (downloaded * 8) / (1000000 * download_time)  # Convert to Mbps
                download_speed = max(download_speed, current_speed)
            
            if download_speed > 10:  # If speed is good enough, stop testing
                break
                
        return download_speed

    def test_upload(self) -> float:
        try:
            data = b'0' * 500000  # 500KB upload test
            start_time = time.time()
            response = requests.post(self.upload_url, data=data, timeout=self.timeout)
            response.raise_for_status()
            upload_time = time.time() - start_time
            
            if upload_time > 0:
                content_length = int(response.headers.get('content-length', 0))
                actual_size = max(len(data), content_length)
                upload_speed = (actual_size * 8) / (1000000 * upload_time)  # Convert to Mbps
                return upload_speed
            return 0.0
            
        except Exception as e:
            logging.error(f"Upload test error: {str(e)}")
            return 0.0