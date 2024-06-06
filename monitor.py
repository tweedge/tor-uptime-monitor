from os import environ, getenv
from time import sleep

import requests
import stem.control
import stem.process
from stem import Signal
from stem.control import Controller


def getenv_or_default(environment_variable, value_if_missing):
    if environment_variable in environ:
        present_value = getenv(environment_variable)
        if type(value_if_missing) is int:
            return int(present_value)
        return present_value
    else:
        return value_if_missing


# required variables
monitor_tor_url = getenv_or_default("MONITOR_TOR_URL", False)
uptime_report_url = getenv_or_default("UPTIME_REPORT_URL", False)

if not (monitor_tor_url and uptime_report_url):
    print(f"SYSTEM: Missing required environment variables - see README.md")
    exit(1)

# optional variables
monitor_tor_contents = getenv_or_default("MONITOR_TOR_CONTENTS", None)
monitor_tor_timeout = getenv_or_default("MONITOR_TOR_TIMEOUT", 30)
monitor_sleep = getenv_or_default("MONITOR_SLEEP", 30)
restart_after_x_failures = getenv_or_default("RESTART_AFTER_X_FAILURES", 10)
uptime_report_response_code_under = getenv_or_default(
    "UPTIME_REPORT_RESPONSE_CODE_UNDER", 300
)

# osminogin/docker-tor-simple variables (don't change these)
SOCKS_PORT = 9050
CONTROL_PORT = 9051

user_agent = requests.utils.default_headers()["User-Agent"]
user_agent = f"{user_agent} (via https://github.com/tweedge/tor-uptime-monitor)"


def tor_get(monitor_tor_url, monitor_tor_contents, monitor_tor_timeout):
    session = requests.session()

    # Tor uses the 9050 port as the default socks port and we must use it to resolve too
    session.proxies = {
        "http": f"socks5h://127.0.0.1:{SOCKS_PORT}",
        "https": f"socks5h://127.0.0.1:{SOCKS_PORT}",
    }

    session.headers.update({"User-Agent": user_agent})

    try:
        result = session.get(monitor_tor_url, timeout=monitor_tor_timeout)
    except Exception as e:
        print(f"FAIL: Fetch failed on {monitor_tor_url} due to exception {str(e)}")
        return False

    if monitor_tor_contents:
        if not monitor_tor_contents in result.text:
            print(
                f"FAIL: Fetch completed but couldn't find {monitor_tor_contents} in {monitor_tor_url}"
            )
            return False

    print(f"OK: Fetched and validated the target URL")
    return True


def report_success(uptime_report_url, uptime_report_response_code_under):
    try:
        reported = requests.get(uptime_report_url)
        reported_status = reported.status_code
        if reported_status < uptime_report_response_code_under:
            print(
                f"OK: Reported success to uptime monitor (response code: {reported_status})"
            )
        else:
            print(
                f"WARN: Unexpected response code ({reported_status}) from {uptime_report_url}"
            )
    except Exception as e:
        print(
            f"WARN: Exception {str(e)} occurred when accessing uptime monitor {uptime_report_url}"
        )


def print_bootstrap_lines(line):
    if "Bootstrapped " in line:
        print(f"TOR: {line}")


print("SYSTEM: Starting up tor and preparing to monitor")

tor_process = stem.process.launch_tor_with_config(
    config={
        "SocksPort": str(SOCKS_PORT),
        "ControlPort": str(CONTROL_PORT),
    },
    init_msg_handler=print_bootstrap_lines,
)

sleep(monitor_sleep)  # give it a bit to start up
repeated_exceptions = 0

while repeated_exceptions < restart_after_x_failures:
    response = tor_get(monitor_tor_url, monitor_tor_contents, monitor_tor_timeout)

    if response:
        report_success(uptime_report_url, uptime_report_response_code_under)
        repeated_exceptions = 0
    else:
        repeated_exceptions += 1

        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)

    sleep(monitor_sleep)

print("SYSTEM: Restarting because we've failed too many times in a row")
exit(1)
