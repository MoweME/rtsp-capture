# rtsp-capture

Captures screenshots from a password-protected RTSP stream at regular intervals.

## Installation

1.  Clone the repository or download the files.
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(This installs `opencv-python`, `PyYAML`, and `croniter`)*

## Configuration

The script requires the RTSP stream URL, username, password, and capture schedule. Configuration is handled in the following order of priority:

1.  **Environment Variables:**
    *   `RTSP_HOST`: The hostname and port of the RTSP stream (e.g., `192.168.1.100:554`).
    *   `RTSP_PATH`: The path of the RTSP stream (e.g., `/stream1`).
    *   `RTSP_USERNAME`: The username for the RTSP stream.
    *   `RTSP_PASSWORD`: The password for the RTSP stream.
    *   `RTSP_SCHEDULE`: The capture schedule. Can be an integer number of minutes (e.g., `5`) or a standard crontab string (e.g., `'*/15 * * * *'` for every 15 minutes, or `'0 9 * * 1-5'` for 9 AM on weekdays).
2.  **Configuration File (`config.yaml`):** If environment variables are not set, the script looks for a `config.yaml` file in the same directory.
    ```yaml
    RTSP:
      host: <your_rtsp_host>:<port>
      path: <your_rtsp_path>
      username: <your_username>
      password: <your_password>
      # Schedule can be minutes (integer) or crontab string
      schedule: '*/30 * * * *' # Example: every 30 minutes
      # schedule: 10           # Example: every 10 minutes
    ```
3.  **User Input:** If neither environment variables nor a complete `config.yaml` file are found, the script will prompt you to enter the required information during the first run. This information will be saved to `config.yaml` (except for the password if provided via environment variable). The default schedule if none is provided is every 5 minutes (`*/5 * * * *`).

## Usage

Run the script from your terminal:

```bash
python rtsp_capture.py
```

The script will start capturing screenshots according to the defined schedule and save them to a `screenshots` directory. Press `Ctrl+C` to stop the script.
