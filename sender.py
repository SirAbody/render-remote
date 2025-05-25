#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 SirAbody. All rights reserved.

import requests
import time
import os
import sys
import json
import cmd
import random
import shutil
import threading
from datetime import datetime
from pathlib import Path
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# Set your server URL here
SERVER_URL = "https://render-remote.onrender.com"

class Sender(cmd.Cmd):
    """
    SirAbody Remote Command System - Sender Module
    """
    def __init__(self, server_url=SERVER_URL):
        super().__init__()
        self.server_url = server_url
        self.active_commands = {}
        self.current_dir = os.getcwd()
    
    def create_banner(self):
        """
        Creates a beautiful banner with the SirAbody logo and system information
        """
        # Get terminal width
        try:
            columns, _ = shutil.get_terminal_size()
            width = min(90, max(70, columns - 4))
        except:
            width = 80  # Default width if can't determine terminal size
            
        # Define a more elegant and simple color scheme
        primary = Fore.BLUE   # Main color for borders and structure
        text = Fore.WHITE    # Normal text color
        accent = Fore.CYAN    # Highlight important information
            
        # Create a more sleek banner
        banner = []
        banner.append(f"{primary}╔{'═' * (width-2)}╗{Style.RESET_ALL}")

        # New simplified but elegant ASCII art logo
        logo = [
            f"{primary}║{Style.RESET_ALL}  ███████╗██╗██████╗  █████╗ ██████╗  ██████╗ ██████╗ ██╗   ██╗{' ' * (width-69)}{primary}║{Style.RESET_ALL}",
            f"{primary}║{Style.RESET_ALL}  ██╔════╝██║██╔══██╗██╔══██╗██╔══██╗██╔═══██╗██╔══██╗╚██╗ ██╔╝{' ' * (width-69)}{primary}║{Style.RESET_ALL}",
            f"{primary}║{Style.RESET_ALL}  ███████╗██║██████╔╝███████║██████╔╝██║   ██║██║  ██║ ╚████╔╝ {' ' * (width-69)}{primary}║{Style.RESET_ALL}",
            f"{primary}║{Style.RESET_ALL}  ╚════██║██║██╔══██╗██╔══██║██╔══██╗██║   ██║██║  ██║  ╚██╔╝  {' ' * (width-69)}{primary}║{Style.RESET_ALL}",
            f"{primary}║{Style.RESET_ALL}  ███████║██║██║  ██║██║  ██║██████╔╝╚██████╔╝██████╔╝   ██║   {' ' * (width-69)}{primary}║{Style.RESET_ALL}",
            f"{primary}║{Style.RESET_ALL}  ╚══════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚═════╝    ╚═╝   {' ' * (width-69)}{primary}║{Style.RESET_ALL}"
        ]
        banner.extend(logo)
        
        # Elegant separator
        banner.append(f"{primary}╠{'═' * (width-2)}╣{Style.RESET_ALL}")

        # System information - Cleaner and more professional
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        banner.append(f"{primary}║{Style.RESET_ALL}  {accent}Remote Command and File Transfer System{' ' * (width-41)}{primary}║{Style.RESET_ALL}")
        banner.append(f"{primary}║{Style.RESET_ALL}  © 2025 SirAbody. All rights reserved.{' ' * (width-38)}{primary}║{Style.RESET_ALL}")
        banner.append(f"{primary}║{Style.RESET_ALL}  Server: {accent}{self.server_url}{' ' * (width-11-len(self.server_url))}{primary}║{Style.RESET_ALL}")
        banner.append(f"{primary}║{Style.RESET_ALL}  Session started: {current_time}{' ' * (width-26-len(current_time))}{primary}║{Style.RESET_ALL}")
        
        # Command help
        banner.append(f"{primary}╠{'═' * (width-2)}╣{Style.RESET_ALL}")
        banner.append(f"{primary}║{Style.RESET_ALL}  Type {accent}help{Style.RESET_ALL} for command list  |  {accent}get{Style.RESET_ALL}/{accent}put{Style.RESET_ALL} for file transfers  |  {accent}exit{Style.RESET_ALL} to quit{' ' * (width-67)}{primary}║{Style.RESET_ALL}")
        banner.append(f"{primary}╚{'═' * (width-2)}╝{Style.RESET_ALL}")
        
        return '\n'.join(banner)
    
    # Use the banner for intro text and customize the prompt
    @property
    def intro(self):
        return self.create_banner()
    
    prompt = f"{Fore.BLUE}SirAbody{Fore.MAGENTA}> {Style.RESET_ALL}"
    def default(self, line):
        """Execute a command on the remote system"""
        if not line.strip():
            return
            
        cmd = line.strip()
        
        # All commands are sent to the remote system, including cd commands
        print(f"Executing remote: {cmd}")
        self.send_command(cmd)
    
    def do_exit(self, arg):
        """Exit the program"""
        print(f"{Fore.RED}Exiting...{Style.RESET_ALL}")
        return True
    
    def do_quit(self, arg):
        """Exit the program"""
        return self.do_exit(arg)
    
    def do_cd(self, arg):
        """Change the current directory on the remote system.
        Usage: cd <directory_path>
        Examples: 
            cd /home/user
            cd ..
            cd ../..
            cd ../folder"""
        path = arg.strip()
        
        # If no path is provided, just execute 'cd' to show current remote directory
        if not path:
            self.send_command("cd")
            return
            
        # Send the cd command to the remote system
        cmd = f"cd {path}"
        print(f"Changing remote directory to: {path}")
        self.send_command(cmd)
        
        # Optionally, we can list the directory contents after changing
        # Add the command to history
        self.cmdqueue.append(cmd)
        self.default(cmd)
        # Wait a bit and check current directory
        time.sleep(0.5)  # Give some time for the cd command to complete
        self.send_command("ls -la || dir")  # This will try 'ls' first, and if it fails, will run 'dir' (Windows)
    
    def do_rfiles(self, arg):
        """List remote files in the current directory.
        Usage: rfiles [directory_path]
        If no directory is provided, lists the current remote directory."""
        
        if arg.strip():
            cmd = f"ls -la {arg.strip()} || dir {arg.strip()}"
            print(f"Listing remote directory: {arg.strip()}")
        else:
            cmd = "ls -la || dir"
            print("Listing current remote directory")
            
        self.send_command(cmd)
    
    def do_lfiles(self, arg):
        """List local files in a specified directory.
        Usage: lfiles [directory_path]
        If no directory is provided, uses the current local directory."""
        
        path = arg.strip() if arg.strip() else "."
        
        try:
            # Convert to absolute path if relative
            if not os.path.isabs(path):
                path = os.path.normpath(os.path.join(os.getcwd(), path))
                
            if not os.path.isdir(path):
                print(f"Error: Not a directory: {path}")
                return
                
            # List all files in the directory
            files = os.listdir(path)
            files.sort()
            
            # Display directory contents
            print(f"\nLocal directory: {path}")
            print("=" * 70)
            print(f"{'Type':<10} {'Size':<12} {'Name':<40}")
            print("-" * 70)
            
            # Add parent directory option
            print(f"{'DIR':<10} {'N/A':<12} {'..':<40}")
            
            # Display directories first, then files
            dirs = []
            regular_files = []
            
            for item in files:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(item)
                else:
                    regular_files.append(item)
            
            # Display directories
            for item in dirs:
                print(f"{'DIR':<10} {'N/A':<12} {item:<40}")
            
            # Display files
            for item in regular_files:
                item_path = os.path.join(path, item)
                size = os.path.getsize(item_path)
                size_str = self._format_size(size)
                print(f"{'FILE':<10} {size_str:<12} {item:<40}")
            
            print("=" * 70)
            print(f"Use 'put <filename>' to upload a file from this directory")
        
        except Exception as e:
            print(f"Error listing directory: {str(e)}")
    
    def _format_size(self, size_bytes):
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"
    def do_quickup(self, arg):
        """Quickly upload files with filename completion.
        Usage: quickup [pattern]
        Searches for files matching the pattern in the current directory and subdirectories."""
        
        if not arg.strip():
            print(f"{Fore.RED}Error: No search pattern provided. Use 'quickup <pattern>'{Style.RESET_ALL}")
            return
        
        pattern = arg.strip()
        matches = []
        
        try:
            # Search for files recursively (up to 2 levels deep)
            for root, dirs, files in os.walk('.', topdown=True, followlinks=False):
                if root.count(os.sep) > 2:  # Limit depth
                    continue
                
                for file in files:
                    if pattern.lower() in file.lower():
                        file_path = os.path.join(root, file)
                        matches.append(file_path)
            
            if not matches:
                print(f"{Fore.RED}No files found matching '{pattern}'{Style.RESET_ALL}")
                return
                
            # If only one match, upload it directly
            if len(matches) == 1:
                self.do_upload(matches[0])
                return
                
            # Display matches for selection
            print(f"\n{Fore.CYAN}Found {len(matches)} files matching '{pattern}':{Style.RESET_ALL}")
            for i, file_path in enumerate(matches):
                size = os.path.getsize(file_path)
                size_str = self._format_size(size)
                print(f"{Fore.YELLOW}{i+1}.{Style.RESET_ALL} {file_path} ({Fore.GREEN}{size_str}{Style.RESET_ALL})")
                
            # Ask user which file to upload
            selection = input(f"\n{Fore.CYAN}Enter number to upload (or 0 to cancel): {Style.RESET_ALL}")
            try:
                selection = int(selection)
                if selection == 0:
                    print(f"{Fore.YELLOW}Upload cancelled{Style.RESET_ALL}")
                    return
                if 1 <= selection <= len(matches):
                    self.do_upload(matches[selection-1])
                else:
                    print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Invalid input. Please enter a number.{Style.RESET_ALL}")
        
        except Exception as e:
            print(f"{Fore.RED}Error during quick upload: {str(e)}{Style.RESET_ALL}")

    def do_get(self, arg):
        """Download a file from the remote system (Shorthand for download).
        Usage: get <file_id> [destination_path]
        If destination is not specified, downloads to current directory."""
        parts = arg.strip().split(" ", 1)
        if not parts[0]:
            print(f"{Fore.RED}❌ Error: No file ID provided{Style.RESET_ALL}")
            print(f"Usage: get <file_id> [destination_path]")
            print(f"Type 'listfiles' to see available files")
            return
            
        file_id = parts[0]
        destination = parts[1] if len(parts) > 1 else "."
        
        self.do_download(f"{file_id} {destination}")
    
    def do_download(self, arg):
        """Download a file from the remote system.
        Usage: download <file_id> <destination_path>
        List available files with 'listfiles'"""
        parts = arg.strip().split(" ", 1)
        if len(parts) < 2:
            print(f"{Fore.RED}❌ Error: Invalid format{Style.RESET_ALL}")
            print(f"Usage: download <file_id> <destination_path>")
            print(f"Type 'listfiles' to see available files")
            return
        
        file_id = parts[0]
        destination = parts[1]
        
        print(f"{Fore.CYAN}📥 Downloading file (ID: {file_id}){Style.RESET_ALL}")
        
        # Convert to absolute path if relative
        if not os.path.isabs(destination):
            destination = os.path.normpath(os.path.join(os.getcwd(), destination))
            print(f"Using absolute path: {destination}")
        
        # Check if destination exists and is a directory
        if not os.path.exists(destination):
            try:
                # Try to create the directory if it doesn't exist
                os.makedirs(destination)
                print(f"{Fore.GREEN}✅ Created directory: {destination}{Style.RESET_ALL}")
            except Exception as e:
                parent_dir = os.path.dirname(destination)
                if os.path.isdir(parent_dir):
                    # It might be a file path, not a directory
                    file_destination = destination
                    destination = parent_dir
                    file_name = os.path.basename(file_destination)
                    print(f"Downloading as file: {file_name}")
                    print(f"To directory: {destination}")
                    self.send_command(f"!download {file_id} {destination} {file_name}")
                    return
                # If parent directory doesn't exist
                else:
                    print(f"{Fore.RED}❌ Error: Could not create directory: {str(e)}{Style.RESET_ALL}")
                    return
        elif not os.path.isdir(destination):
            print(f"{Fore.RED}❌ Error: Destination must be a directory: {destination}{Style.RESET_ALL}")
            return
        
        print(f"Saving to directory: {destination}")
        self.send_command(f"!download {file_id} {destination}")
    
    def do_downloadto(self, arg):
        """Download a file directly to a specified directory.
        Usage: downloadto <file_id> [directory]
        If directory is not specified, downloads to current directory."""
        
        parts = arg.strip().split(" ", 1)
        if not parts[0]:
            print("Error: No file ID provided. Use 'downloadto <file_id> [directory]'")
            print("To see available files, use the 'listfiles' command")
            return
        
        file_id = parts[0]
        destination = parts[1] if len(parts) > 1 and parts[1].strip() else "."
        
        # Convert to absolute path if relative
        if not os.path.isabs(destination):
            destination = os.path.normpath(os.path.join(os.getcwd(), destination))
            
        if not os.path.exists(destination):
            try:
                # Try to create the directory if it doesn't exist
                os.makedirs(destination)
                print(f"Created directory: {destination}")
            except Exception as e:
                print(f"Error: Could not create directory: {destination} - {str(e)}")
                return
        elif not os.path.isdir(destination):
            print(f"Error: The specified path is not a directory: {destination}")
            return
        
        # Convert relative path to absolute path
        destination = os.path.abspath(destination)
        print(f"Downloading file (ID: {file_id}) to {destination}...")
        self.send_command(f"!download {file_id} {destination}")
    def do_put(self, arg):
        """Upload a file to the remote system (Shorthand for upload).
        Usage: put <file_path>
        You can use relative or absolute paths."""
        self.do_upload(arg)
    
    def do_upload(self, arg):
        """Upload a file to the remote system.
        Usage: upload <file_path>
        You can use relative or absolute paths."""
        file_path = arg.strip()
        if not file_path:
            print(f"Error: No file path provided. Use 'upload <file_path>'")
            print(f"Tip: Use 'lfiles' to see local files available for upload")
            return
        
        # Convert to absolute path if relative
        if not os.path.isabs(file_path):
            file_path = os.path.normpath(os.path.join(os.getcwd(), file_path))
            
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            print(f"Current directory: {os.getcwd()}")
            return
        
        if os.path.isdir(file_path):
            # Handle directory uploads with confirmation
            print(f"'{file_path}' is a directory.")
            files_count = sum(len(files) for _, _, files in os.walk(file_path))
            if files_count == 0:
                print("Directory is empty. Nothing to upload.")
                return
                
            print(f"Directory contains {files_count} files.")
            proceed = input("Do you want to upload all files in this directory? (y/n): ").lower()
            
            if proceed != 'y':
                print("Upload cancelled.")
                return
                
            # Upload each file in the directory
            success_count = 0
            for root, _, files in os.walk(file_path):
                for file in files:
                    file_full_path = os.path.join(root, file)
                    try:
                        self._upload_single_file(file_full_path)
                        success_count += 1
                    except Exception as e:
                        print(f"Error uploading {file}: {str(e)}")
            
            print(f"Uploaded {success_count} of {files_count} files from {file_path}")
            return
            
        # Upload a single file
        try:
            self._upload_single_file(file_path)
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
    
    def _upload_single_file(self, file_path):
        """Helper method to upload a single file"""
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        print(f"{Fore.CYAN}📤 Uploading: {file_name} ({self._format_size(file_size)}){Style.RESET_ALL}")
        
        # Show progress spinner
        spinner_thread = threading.Thread(target=self._show_spinner, args=("Uploading",))
        spinner_thread.daemon = True
        spinner_thread.start()
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                response = requests.post(f"{self.server_url}/api/upload-file", files=files)
        except IOError as e:
            self._stop_spinner = True
            spinner_thread.join()
            print(f"\r{' ' * 30}\r", end="")
            print(f"{Fore.RED}❌ Error reading file: {str(e)}{Style.RESET_ALL}")
            raise
        
        # Stop spinner
        self._stop_spinner = True
        spinner_thread.join()
        
        if response.status_code == 200:
            result = response.json()
            file_id = result.get('file_id')
            print(f"\r{' ' * 30}\r", end="")
            print(f"{Fore.GREEN}✅ File uploaded successfully!{Style.RESET_ALL}")
            print(f"File name: {file_name}")
            print(f"File size: {self._format_size(file_size)}")
            print(f"File ID: {file_id}")
            print(f"{Fore.YELLOW}To download on remote system: !download {file_id} <destination_path>{Style.RESET_ALL}")
            return file_id
        else:
            print(f"\r{' ' * 30}\r", end="")
            print(f"{Fore.RED}❌ Error uploading file: {response.status_code} - {response.text}{Style.RESET_ALL}")
            raise Exception(f"Server error: {response.status_code}")
    
    def _show_spinner(self, action_text):
        """Show a spinner animation while performing a long operation"""
        self._stop_spinner = False
        spinner = ['⟾', '⟽', '⟻', '⋿', '⇿', '⏟', '⎯', '⎷']
        i = 0
        while not self._stop_spinner:
            sys.stdout.write(f"\r{Fore.CYAN}{action_text} {spinner[i % len(spinner)]}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write(f"\r{' ' * (len(action_text) + 5)}\r")
        sys.stdout.flush()
    
    def do_listfiles(self, arg):
        """List files available for download"""
        try:
            print(f"{Fore.CYAN}Fetching file list...{Style.RESET_ALL}")
            
            # Show progress spinner
            spinner_thread = threading.Thread(target=self._show_spinner, args=("Fetching files",))
            spinner_thread.daemon = True
            spinner_thread.start()
            
            # Get file list
            response = requests.get(f"{self.server_url}/api/list-files")
            
            # Stop spinner
            self._stop_spinner = True
            spinner_thread.join()
            
            if response.status_code == 200:
                files = response.json()
                if files:
                    print(f"{Fore.CYAN}\nAvailable Files:{Style.RESET_ALL}")
                    print(f"{Fore.BLUE}{'-' * 70}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}{'ID':<20} {'Filename':<30} {'Date & Time':<20}{Style.RESET_ALL}")
                    print(f"{Fore.BLUE}{'-' * 70}{Style.RESET_ALL}")
                    
                    for file_id, file_info in files.items():
                        timestamp = datetime.fromtimestamp(file_info.get("timestamp", 0)).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"{Fore.GREEN}{file_id:<20}{Style.RESET_ALL} {Fore.CYAN}{file_info.get('filename'):<30}{Style.RESET_ALL} {Fore.MAGENTA}{timestamp:<20}{Style.RESET_ALL}")
                    
                    print(f"{Fore.BLUE}{'-' * 70}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}\nTo download a file, use: {Fore.YELLOW}download <file_id> <destination_path>{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}Quick download to current directory: {Fore.YELLOW}downloadto <file_id>{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}No files available for download{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Error listing files: {response.status_code} - {response.text}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error connecting to server: {str(e)}{Style.RESET_ALL}")
    def do_status(self, arg):
        """Check the status of a command.
        Usage: status <command_id>"""
        command_id = arg.strip()
        if not command_id:
            print(f"{Fore.RED}Error: No command ID provided. Use 'status <command_id>'{Style.RESET_ALL}")
            return
        
        try:
            print(f"{Fore.CYAN}Checking status...{Style.RESET_ALL}")
            response = requests.get(f"{self.server_url}/api/command-status/{command_id}")
            if response.status_code == 200:
                status = response.json()
                print(f"{Fore.CYAN}\nCommand: {Fore.WHITE}{status.get('command')}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Status: {Fore.YELLOW}{status.get('status')}{Style.RESET_ALL}")
                
                if status.get('status') == "completed" and status.get('output'):
                    output = status.get('output', {})
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    return_code = output.get('return_code', -1)
                    
                    print(f"{Fore.CYAN}Return code: {Fore.YELLOW}{return_code}{Style.RESET_ALL}")
                    
                    if stdout:
                        print(f"{Fore.GREEN}\nSTDOUT:{Style.RESET_ALL}")
                        print(stdout)
                    
                    if stderr:
                        print(f"{Fore.RED}\nSTDERR:{Style.RESET_ALL}")
                        print(stderr)
            else:
                print(f"{Fore.RED}Error checking command status: {response.status_code} - {response.text}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error connecting to server: {str(e)}{Style.RESET_ALL}")
    
    def do_quickcmd(self, arg):
        """Execute common system commands quickly.
        Usage: qcmd [option]
        Options:
            1 or sysinfo - System information
            2 or proc - List running processes
            3 or net - Network information
            4 or disk - Disk space information"""
        
        cmd_map = {
            "1": "systeminfo" if os.name == "nt" else "uname -a && cat /etc/os-release",
            "2": "tasklist" if os.name == "nt" else "ps aux",
            "3": "ipconfig /all" if os.name == "nt" else "ifconfig -a",
            "4": "wmic logicaldisk get caption,description,providername,size,freespace" 
                if os.name == "nt" else "df -h",
            "sysinfo": "systeminfo" if os.name == "nt" else "uname -a && cat /etc/os-release",
            "proc": "tasklist" if os.name == "nt" else "ps aux",
            "net": "ipconfig /all" if os.name == "nt" else "ifconfig -a",
            "disk": "wmic logicaldisk get caption,description,providername,size,freespace" 
                if os.name == "nt" else "df -h"
        }
        
        if not arg.strip() or arg.strip() not in cmd_map:
            print(f"{Fore.CYAN}Quick commands:{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}1{Fore.WHITE} or {Fore.YELLOW}sysinfo{Fore.WHITE} - System information")
            print(f"{Fore.YELLOW}2{Fore.WHITE} or {Fore.YELLOW}proc{Fore.WHITE} - List running processes")
            print(f"{Fore.YELLOW}3{Fore.WHITE} or {Fore.YELLOW}net{Fore.WHITE} - Network information")
            print(f"{Fore.YELLOW}4{Fore.WHITE} or {Fore.YELLOW}disk{Fore.WHITE} - Disk space information")
            return
        
        command = cmd_map[arg.strip()]
        print(f"{Fore.CYAN}Executing: {Fore.WHITE}{command}{Style.RESET_ALL}")
        self.send_command(command)
    def do_help(self, arg):
        """Show help for commands"""
        if arg:
            # Use the default help behavior for specific commands
            super().do_help(arg)
            return
        
        # Custom help display with fewer colors and better organization
        print(f"\n=== SirAbody Remote Command System - Help ===")
        
        print(f"\n1. Navigation and File Management:")
        print(f"  cd <path>          - Change local directory (supports cd .. and cd ../..)") 
        print(f"  browse [dir]       - List files in local directory")
        print(f"  upload <file_path>  - Upload a file to the server")
        print(f"  quickup <pattern>   - Search for and upload files by pattern")
        
        print(f"\n2. Remote File Operations:")
        print(f"  listfiles          - List files available on the remote server")
        print(f"  download <id> <path> - Download a file to specified path")
        print(f"  downloadto <id> [dir] - Download to current/specified directory")
        
        print(f"\n3. Remote Command Execution:")
        print(f"  <any_command>      - Execute command on the remote system")
        print(f"  status <cmd_id>    - Check status of a command")
        print(f"  quickcmd [option]  - Run predefined system commands:")
        print(f"                      1/sysinfo: System info")
        print(f"                      2/proc: Process list")
        print(f"                      3/net: Network info")
        print(f"                      4/disk: Disk space info")
        
        print(f"\n4. System:")
        print(f"  help               - Display this help message")
        print(f"  exit or quit       - Exit the program")
        
        print(f"\nExamples:")
        print(f"  cd ..              - Go to parent directory")
        print(f"  browse C:/Users     - List files in C:/Users")
        print(f"  upload test.txt     - Upload test.txt from current directory")
        print(f"  downloadto abc123   - Download file with ID abc123 to current dir")
    
    def send_command(self, command):
        """Send a command to the remote system"""
        try:
            data = {
                "command": command
            }
            response = requests.post(
                f"{self.server_url}/api/send-command", 
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                command_id = result.get("command_id")
                self.active_commands[command_id] = command
                print(f"{Fore.GREEN}Command sent successfully!{Style.RESET_ALL}")
                print(f"Command ID: {command_id}")
                
                # Start polling for the command output
                self.poll_command_output(command_id)
            else:
                print(f"{Fore.RED}Error sending command: {response.status_code} - {response.text}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error connecting to server: {str(e)}{Style.RESET_ALL}")
    
    def poll_command_output(self, command_id):
        """Poll for command output with a timeout"""
        start_time = time.time()
        timeout = 60  # Timeout after 60 seconds of waiting
        
        print(f"{Fore.CYAN}Waiting for command to complete...{Style.RESET_ALL}")
        
        # Show spinner while waiting
        spinner_thread = threading.Thread(target=self._show_spinner, args=("Waiting for response",))
        spinner_thread.daemon = True
        spinner_thread.start()
        
        try:
            while time.time() - start_time < timeout:
                response = requests.get(f"{self.server_url}/api/command-status/{command_id}")
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status.get('status') == "completed" and status.get('output'):
                        # Stop spinner
                        self._stop_spinner = True
                        spinner_thread.join()
                        
                        output = status.get('output', {})
                        stdout = output.get('stdout', '')
                        stderr = output.get('stderr', '')
                        return_code = output.get('return_code', -1)
                        
                        print(f"{Fore.GREEN}Command completed with return code: {Fore.YELLOW}{return_code}{Style.RESET_ALL}")
                        
                        if stdout:
                            print(f"{Fore.CYAN}\nSTDOUT:{Style.RESET_ALL}")
                            print(stdout)
                        
                        if stderr:
                            print(f"{Fore.RED}\nSTDERR:{Style.RESET_ALL}")
                            print(stderr)
                        
                        return
                
                # Wait before polling again
                time.sleep(2)
        
        except Exception as e:
            self._stop_spinner = True
            spinner_thread.join()
            print(f"{Fore.RED}Error checking command status: {str(e)}{Style.RESET_ALL}")
        
        # If we got here, command timed out or had an error
        self._stop_spinner = True
        spinner_thread.join()
        print(f"{Fore.RED}\nCommand timed out or error occurred. You can check the status later using:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}status {command_id}{Style.RESET_ALL}")

def clear_screen():
    # Clear the screen based on the operating system
    os.system('cls' if os.name == 'nt' else 'clear')

def display_animated_banner():
    # Display an animated loading effect before showing the main banner
    clear_screen()
    print("Loading SirAbody Remote Command System")
    
    animation = ["-", "\\", "|", "/"]
    
    for i in range(15):
        time.sleep(0.1)
        sys.stdout.write("\r" + Fore.CYAN + "[" + animation[i % len(animation)] + "]" + Style.RESET_ALL)
        sys.stdout.flush()
    
    print("\r" + Fore.GREEN + "[✓]" + Style.RESET_ALL + " System Ready!")
    time.sleep(0.5)
    clear_screen()

if __name__ == "__main__":
    # Allow server URL to be overridden via command line argument
    if len(sys.argv) > 1:
        SERVER_URL = sys.argv[1]
    
    # Display animated banner
    display_animated_banner()
    
    # Start the command loop
    sender = Sender(SERVER_URL)
    try:
        sender.cmdloop()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Program terminated by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
