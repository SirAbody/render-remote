# SirAbody Remote Command System

© 2025 SirAbody. All rights reserved.

## Overview

This project provides a secure remote command execution and file transfer system. It consists of three main components:

1. **Server**: A Flask web application to be hosted on Render.com that facilitates communication between sender and receiver
2. **Sender**: Command-line client to send commands and manage file transfers
3. **Receiver**: Background service that executes commands on the target machine

## Features

- Remote command execution with real-time output streaming
- File uploads and downloads between systems
- Support for all file types including videos and compressed archives
- Clean and professional user interface
- Secure communication between components
- Cross-platform support (Windows, Linux, macOS)

## Setup and Deployment

### Prerequisites

- Python 3.9 or higher
- Git
- Render.com account (for hosting the server)
- GitHub account (for source code hosting)

### Deployment Steps

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/sirabody-remote.git
   git push -u origin main
   ```

2. **Deploy to Render.com**:
   - Create a new Web Service on Render.com
   - Connect your GitHub repository
   - Render will automatically detect the `render.yaml` configuration
   - Or manually configure using:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn server:app`

3. **Configure Clients**:
   - Update the `SERVER_URL` in both `sender.py` and `receiver.py` to your Render.com deployment URL

## Usage

### Receiver (Target Machine)

```bash
# Start the receiver on the machine you want to control
python receiver.py

# Optionally specify a custom server URL
python receiver.py https://your-custom-url.onrender.com
```

### Sender (Controller Machine)

```bash
# Start the sender application
python sender.py

# Optionally specify a custom server URL
python sender.py https://your-custom-url.onrender.com
```

### Sender Commands

- Execute any shell command by typing it directly
- `upload <local_file_path>`: Upload a file to the server
- `download <file_id> <destination_path>`: Download a file from the server
- `listfiles`: List all files available for download
- `status <command_id>`: Check the status of a previously sent command
- `help`: Display available commands
- `exit` or `quit`: Exit the application

## Advanced Usage Examples

### File Transfer

1. From Sender, upload a file:
   ```
   SirAbody> upload C:\path\to\file.zip
   ```

2. On the Receiver, the file can be downloaded using:
   ```
   SirAbody> !download file_id C:\destination\folder
   ```

### Remote Administration

- View system information:
   ```
   SirAbody> systeminfo
   ```

- List running processes:
   ```
   SirAbody> tasklist
   ```

## Security Considerations

- This tool provides remote command execution capabilities which can be dangerous if misused
- Always deploy in secure environments
- Consider adding authentication to the server component
- Use HTTPS for all communications

## License

This project is proprietary software owned by SirAbody.
© 2025 SirAbody. All rights reserved.
