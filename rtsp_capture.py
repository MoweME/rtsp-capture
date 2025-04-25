import cv2
import os
import time
import yaml
import sys
from datetime import datetime, timedelta
import getpass
from croniter import croniter

# Store the original print function
original_print = print

# Configure print function to always flush output
def print_flush(*args, **kwargs):
    """Custom print function that always flushes output - helps with Docker logs."""
    kwargs.update({'flush': True})
    original_print(*args, **kwargs)

# Replace builtin print with our flushing version
print = print_flush

CONFIG_FILE = 'config.yaml'
DEFAULT_SCHEDULE = '*/5 * * * *'

def load_config():
    """Loads configuration from config.yaml."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
                if not isinstance(config, dict):
                    return {}
                return config
        except yaml.YAMLError as e:
            print(f"Error loading {CONFIG_FILE}: {e}. Starting with empty config.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred loading {CONFIG_FILE}: {e}. Starting with empty config.")
            return {}
    return {}

def save_config(config):
    """Saves configuration to config.yaml."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        print(f"Error saving configuration to {CONFIG_FILE}: {e}")

def get_config_value(config, section, key, env_var, prompt_message, is_sensitive=False):
    """Gets config value prioritizing environment variables, then config file, then user input."""
    value = os.environ.get(env_var)
    config_section = config.get(section, {})

    if value:
        # Strip any surrounding quotes from the environment variable value
        value = value.strip('"\'')
        print(f"Using {key} from environment variable {env_var}.")
        if section not in config:
            config[section] = {}
        config[section][key] = value
        return value

    if key in config_section:
        return config_section[key]
    else:
        input_value = None
        while not input_value:
            if is_sensitive:
                input_value = getpass.getpass(prompt_message)
            else:
                input_value = input(prompt_message)

        if section not in config:
            config[section] = {}
        config[section][key] = input_value
        save_config(config)
        return input_value

def capture_screenshot(rtsp_url, output_dir='screenshots'):
    """Captures a single screenshot from the RTSP stream."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(rtsp_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"screenshot_{timestamp}.jpg")
    latest_filename = os.path.join(output_dir, "latest.jpg")

    if not cap.isOpened():
        print(f"Error: Could not open RTSP stream: {rtsp_url}")
        return False

    ret, frame = cap.read()

    if ret:
        # Save timestamped file
        cv2.imwrite(filename, frame)
        print(f"Screenshot saved to {filename}")

        # Save/overwrite latest.jpg
        try:
            cv2.imwrite(latest_filename, frame)
            print(f"Updated {latest_filename}")
            success = True
        except Exception as e:
            print(f"Error saving {latest_filename}: {e}")
            success = False

    else:
        print("Error: Could not read frame from RTSP stream.")
        success = False

    cap.release()
    return success

def main():
    config = load_config()
    section = 'RTSP'

    rtsp_host = get_config_value(config, section, 'host', 'RTSP_HOST', "Enter RTSP stream host (e.g., 192.168.1.100:554): ")
    rtsp_path = get_config_value(config, section, 'path', 'RTSP_PATH', "Enter RTSP stream path (e.g., /stream1): ")
    username = get_config_value(config, section, 'username', 'RTSP_USERNAME', "Enter RTSP username: ")
    password = get_config_value(config, section, 'password', 'RTSP_PASSWORD', "Enter RTSP password: ", is_sensitive=True)
    schedule_str = get_config_value(config, section, 'schedule', 'RTSP_SCHEDULE', f"Enter schedule (minutes or crontab string, default: '{DEFAULT_SCHEDULE}'): ")

    # Clean up schedule string (remove potential quotes and whitespace)
    if schedule_str:
        schedule_str = schedule_str.strip().strip('\'"')

    if not schedule_str:
        schedule_str = DEFAULT_SCHEDULE
        if section not in config:
            config[section] = {}
        config[section]['schedule'] = DEFAULT_SCHEDULE
        save_config(config)

    rtsp_url = f"rtsp://{username}:{password}@{rtsp_host}{rtsp_path}"

    print(f"Starting RTSP capture with schedule: {schedule_str}")
    print("Press Ctrl+C to stop.")

    is_cron_schedule = False
    delay_seconds = None
    cron = None

    try:
        delay_minutes = int(schedule_str)
        delay_seconds = delay_minutes * 60
        print(f"Using fixed delay of {delay_minutes} minutes.")
    except ValueError:
        try:
            now = datetime.now()
            cron = croniter(schedule_str, now)
            is_cron_schedule = True
            print(f"Using crontab schedule: {schedule_str}")
        except Exception as e:
            print(f"Invalid schedule format: '{schedule_str}'. Error: {e}")
            print(f"Please provide an integer number of minutes or a valid crontab string.")
            return

    while True:
        try:
            capture_successful = capture_screenshot(rtsp_url)

            if is_cron_schedule:
                now = datetime.now()
                next_run_dt = cron.get_next(datetime)
                wait_seconds = (next_run_dt - now).total_seconds()
                print(f"Next capture scheduled at: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                wait_seconds = delay_seconds
                next_run_dt = datetime.now() + timedelta(seconds=wait_seconds)
                print(f"Next capture in {delay_minutes} minutes at approx: {next_run_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            if wait_seconds > 0:
                print(f"Waiting for {wait_seconds:.2f} seconds...")
                time.sleep(wait_seconds)
            else:
                print("Next scheduled time is immediate. Capturing again.")
                time.sleep(1)

        except KeyboardInterrupt:
            print("Stopping capture.")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            wait_seconds_on_error = 60
            if is_cron_schedule:
                try:
                    now = datetime.now()
                    next_run_dt = cron.get_next(datetime)
                    wait_seconds_on_error = max(1, (next_run_dt - now).total_seconds())
                except Exception:
                    pass
            elif delay_seconds:
                wait_seconds_on_error = delay_seconds

            print(f"Retrying after approximately {wait_seconds_on_error:.0f} seconds...")
            try:
                time.sleep(wait_seconds_on_error)
            except KeyboardInterrupt:
                print("Stopping capture during retry wait.")
                break

if __name__ == "__main__":
    main()
