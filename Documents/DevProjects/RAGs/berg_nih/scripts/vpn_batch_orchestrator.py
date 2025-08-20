#!/usr/bin/env python3
"""
VPN Batch Orchestrator - Automated YouTube Transcript Extraction
Corrected Strategy: Switch VPN AFTER each 10-video batch completion
Enhanced with Geographic Diversity to avoid regional detection
"""

import subprocess
import time
import logging
import argparse
import json
import os
import random
from pathlib import Path
from datetime import datetime

class VPNBatchOrchestrator:
    def __init__(self, log_dir="logs"):
        self.processed_videos = 0
        self.current_location = None
        self.locations_used = []
        self.start_time = datetime.now()
        
        # Setup logging
        Path(log_dir).mkdir(exist_ok=True)
        log_file = f"{log_dir}/orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # VPN locations organized by geographic regions for maximum diversity
        # This prevents YouTube's regional detection systems from catching patterns
        self.vpn_regions = {
            "northeast": ["boston-us", "new-york-us", "philadelphia-us"],
            "southeast": ["atlanta-us", "miami-us", "charlotte-us"], 
            "midwest": ["chicago-us", "detroit-us", "louisville-us"],  # Louisville tested ✅
            "south_central": ["dallas-us", "oklahoma-city-us", "houston-us"],  # OK tested ✅
            "mountain": ["denver-us", "phoenix-us", "salt-lake-us"],  # Phoenix tested ✅
            "northwest": ["seattle-us", "portland-us"],  # Seattle tested ✅
            "west": ["los-angeles-us", "san-francisco-us", "idaho-falls-us"]  # Idaho tested ✅
        }
        
        # Flatten for easy access while maintaining region info
        self.vpn_locations = []
        self.location_to_region = {}
        for region, locations in self.vpn_regions.items():
            self.vpn_locations.extend(locations)
            for loc in locations:
                self.location_to_region[loc] = region
    
    def _select_geographically_diverse_location(self):
        """Select location from different geographic region than recent locations"""
        # Get regions of recently used locations
        recent_regions = []
        for loc in self.locations_used[-2:]:  # Last 2 locations
            region = self.location_to_region.get(loc)
            if region:
                recent_regions.append(region)
        
        # Find locations from different regions
        available_locations = []
        for location in self.vpn_locations:
            location_region = self.location_to_region.get(location)
            if location_region not in recent_regions:
                available_locations.append(location)
        
        # If no diverse locations available, use any unused location
        if not available_locations:
            available_locations = [loc for loc in self.vpn_locations 
                                 if loc not in self.locations_used[-3:]]
        
        # Final fallback: use any location
        if not available_locations:
            available_locations = self.vpn_locations
            
        # Prioritize tested locations when available
        tested_locations = ["louisville-us", "idaho-falls-us", "phoenix-us", 
                          "seattle-us", "oklahoma-city-us"]
        
        tested_available = [loc for loc in available_locations if loc in tested_locations]
        if tested_available:
            selected = random.choice(tested_available)
        else:
            selected = random.choice(available_locations)
            
        self.logger.info(f"Geographic diversity selection:")
        self.logger.info(f"Recent regions used: {recent_regions}")
        self.logger.info(f"Selected location: {selected} (region: {self.location_to_region.get(selected)})")
        
        return selected
    
    def switch_vpn_location(self, target_location=None):
        """Switch VPN location with maximum geographic diversity"""
        if target_location is None:
            target_location = self._select_geographically_diverse_location()
        
        self.logger.info(f"Attempting to switch VPN to: {target_location}")
        self.logger.info(f"Target region: {self.location_to_region.get(target_location, 'unknown')}")
        
        # Method 1: Try HMA CLI (if available)
        if self._try_hma_cli(target_location):
            self.current_location = target_location
            self.locations_used.append(target_location)
            self.logger.info(f"Successfully switched to {target_location} via HMA CLI")
            return True
            
        # Method 2: Try OpenVPN script (if available)  
        if self._try_openvpn_script(target_location):
            self.current_location = target_location
            self.locations_used.append(target_location)
            self.logger.info(f"Successfully switched to {target_location} via OpenVPN")
            return True
            
        # Method 3: Manual prompt
        return self._prompt_manual_switch(target_location)
    
    def _try_hma_cli(self, location):
        """Try switching via HMA CLI"""
        try:
            # Try Windows HMA CLI
            hma_path = "/mnt/c/Program Files/HMA! Pro VPN/HMA! Pro VPN.exe"
            if os.path.exists(hma_path):
                cmd = [hma_path, f"-cp:{location}"]
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0:
                    time.sleep(20)  # Wait for VPN to stabilize
                    return True
        except Exception as e:
            self.logger.debug(f"HMA CLI failed: {e}")
        return False
    
    def _try_openvpn_script(self, location):
        """Try switching via OpenVPN script"""
        try:
            # Look for community OpenVPN scripts
            openvpn_script = "hma-openvpn.sh"
            if os.path.exists(openvpn_script):
                cmd = [f"./{openvpn_script}", "-f"]  # Connect to fastest
                result = subprocess.run(cmd, capture_output=True, timeout=120)
                if result.returncode == 0:
                    time.sleep(20)  # Wait for VPN to stabilize
                    return True
        except Exception as e:
            self.logger.debug(f"OpenVPN script failed: {e}")
        return False
    
    def _prompt_manual_switch(self, location):
        """Prompt user for manual VPN switch with geographic guidance"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"MANUAL VPN SWITCH REQUIRED")
        self.logger.info(f"Recommended location: {location}")
        self.logger.info(f"Recommended region: {self.location_to_region.get(location, 'unknown')}")
        self.logger.info(f"")
        self.logger.info(f"🎯 IMPORTANT: Choose location from DIFFERENT region!")
        self.logger.info(f"Recently used regions: {[self.location_to_region.get(loc, 'unknown') for loc in self.locations_used[-2:]]}")
        self.logger.info(f"")
        self.logger.info(f"Available regions to choose from:")
        recent_regions = [self.location_to_region.get(loc) for loc in self.locations_used[-2:]]
        for region, locations in self.vpn_regions.items():
            if region not in recent_regions:
                self.logger.info(f"  ✅ {region.upper()}: {', '.join(locations)}")
            else:
                self.logger.info(f"  ❌ {region.upper()}: {', '.join(locations)} (recently used)")
        self.logger.info(f"{'='*60}")
        
        while True:
            response = input("Press ENTER after switching VPN to different region (or 'q' to quit): ").strip()
            if response.lower() == 'q':
                return False
            if response == "":
                # Verify new IP
                if self._verify_new_ip():
                    self.current_location = location
                    self.locations_used.append(location)
                    return True
                else:
                    self.logger.warning("IP verification failed. Please try switching again.")
    
    def _verify_new_ip(self):
        """Verify VPN switched to new IP"""
        try:
            result = subprocess.run(['curl', '-s', 'ifconfig.me'], 
                                  capture_output=True, text=True, timeout=10)
            new_ip = result.stdout.strip()
            self.logger.info(f"Current IP: {new_ip}")
            time.sleep(15)  # Additional stabilization time
            return True
        except Exception as e:
            self.logger.warning(f"IP verification failed: {e}")
            return False
    
    def run_batch_script(self, start_index, batch_size):
        """Run transcript extraction batch and wait for completion"""
        self.logger.info(f"Starting batch: videos {start_index} to {start_index + batch_size - 1}")
        
        # Use Windows Python via WSL - call Windows UV command
        cmd = [
            'cmd.exe', '/c', 'uv', 'run', 'python', 
            'scripts/transcript_extractor_human_batch.py',
            '--input-file', 'data/processed/berg_filtered_catalog.json',
            '--start-index', str(start_index),
            '--target-videos', str(batch_size)
        ]
        
        self.logger.info(f"Command: {' '.join(cmd)}")
        
        try:
            # Run script and wait for complete termination
            self.logger.info("Starting subprocess...")
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.logger.info(f"Process started with PID: {process.pid}")
            
            # Monitor output in real-time with timeout
            success_count = 0
            timeout_counter = 0
            max_timeout = 30  # 30 seconds timeout for debugging
            
            while True:
                # Check for stdout
                output = process.stdout.readline()
                # Check for stderr immediately
                stderr_line = process.stderr.readline()
                
                if stderr_line:
                    self.logger.error(f"STDERR: {stderr_line.strip()}")
                
                if output == '' and stderr_line == '' and process.poll() is not None:
                    break
                    
                if output:
                    print(f"STDOUT: {output.strip()}")
                    if "Successfully processed video" in output:
                        success_count += 1
                    timeout_counter = 0  # Reset timeout on activity
                else:
                    timeout_counter += 1
                    if timeout_counter > max_timeout:
                        self.logger.error("Process timed out after 30 seconds - killing")
                        process.kill()
                        break
                    time.sleep(1)
            
            return_code = process.wait()  # Ensure complete termination
            
            # Check for errors in stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                self.logger.error(f"Process stderr: {stderr_output}")
                
        except Exception as e:
            self.logger.error(f"Failed to run batch script: {e}")
            return False
        
        self.logger.info(f"Batch completed with return code: {return_code}")
        self.logger.info(f"Successfully processed videos: {success_count}")
        
        return return_code == 0 and success_count > 0
    
    def run_automated_batches(self, total_videos, videos_per_batch=10, start_index=0):
        """Main orchestration loop - Geographic diversity VPN switching"""
        self.processed_videos = start_index
        target_end_index = start_index + total_videos
        
        self.logger.info(f"Starting automated processing with geographic diversity:")
        self.logger.info(f"Using filtered catalog: berg_filtered_catalog.json (2-5 minute videos only)")
        self.logger.info(f"Total target: {total_videos} videos")
        self.logger.info(f"Processing range: {start_index} to {target_end_index - 1}")
        self.logger.info(f"Batch size: {videos_per_batch} videos") 
        self.logger.info(f"Starting from index: {start_index}")
        self.logger.info(f"VPN regions available: {len(self.vpn_regions)}")
        self.logger.info(f"Strategy: Bounce between geographic regions to avoid detection")
        
        while self.processed_videos < target_end_index:
            batch_start_index = self.processed_videos
            batch_size = min(videos_per_batch, target_end_index - self.processed_videos)
            
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"BATCH {(self.processed_videos // videos_per_batch) + 1}")
            self.logger.info(f"Videos: {batch_start_index} to {batch_start_index + batch_size - 1}")
            self.logger.info(f"Current location: {self.current_location}")
            self.logger.info(f"Current region: {self.location_to_region.get(self.current_location, 'unknown')}")
            self.logger.info(f"{'='*50}")
            
            # Run batch script and wait for completion
            success = self.run_batch_script(batch_start_index, batch_size)
            
            if success:
                self.processed_videos += batch_size
                self.logger.info(f"Batch completed successfully!")
                self.logger.info(f"Progress: {self.processed_videos - start_index}/{total_videos} videos")
                
                # Switch VPN AFTER successful batch completion (if not last batch)
                if self.processed_videos < target_end_index:
                    self.logger.info("Switching VPN to different geographic region for next batch...")
                    if not self.switch_vpn_location():
                        self.logger.error("VPN switch failed. Exiting.")
                        return False
                        
                    self.logger.info("Waiting for VPN stabilization...")
                    time.sleep(15)  # Allow VPN to fully stabilize
                    
            else:
                self.logger.error("Batch failed! Attempting recovery...")
                
                # Switch VPN for recovery attempt
                if not self.switch_vpn_location():
                    self.logger.error("Recovery VPN switch failed. Manual intervention required.")
                    return False
                
                self.logger.info("Retrying failed batch with new VPN location...")
                # Don't increment processed_videos - retry same batch
        
        elapsed = datetime.now() - self.start_time
        self.logger.info(f"\nALL BATCHES COMPLETED!")
        self.logger.info(f"Total videos processed: {self.processed_videos}")
        self.logger.info(f"Total time: {elapsed}")
        self.logger.info(f"Geographic diversity used:")
        for i, location in enumerate(self.locations_used):
            region = self.location_to_region.get(location, 'unknown')
            self.logger.info(f"  Batch {i+1}: {location} ({region})")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Automated VPN + YouTube Transcript Extraction (Geographic Diversity)"
    )
    parser.add_argument('--total-videos', type=int, required=True,
                       help='Total number of videos to process')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Videos per batch (default: 10)')
    parser.add_argument('--start-index', type=int, default=0,
                       help='Starting video index (for resume)')
    parser.add_argument('--log-dir', default='logs',
                       help='Directory for log files')
    
    args = parser.parse_args()
    
    orchestrator = VPNBatchOrchestrator(args.log_dir)
    
    try:
        success = orchestrator.run_automated_batches(
            total_videos=args.total_videos,
            videos_per_batch=args.batch_size,
            start_index=args.start_index
        )
        
        if success:
            print(f"\nSuccessfully processed {args.total_videos} videos with geographic diversity!")
        else:
            print(f"\nProcessing failed or was interrupted.")
            
    except KeyboardInterrupt:
        print(f"\nProcessing interrupted by user.")
        print(f"Resume with: --start-index {orchestrator.processed_videos}")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print(f"Resume with: --start-index {orchestrator.processed_videos}")

if __name__ == "__main__":
    main()