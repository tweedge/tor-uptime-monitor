from os import environ, getenv
from time import sleep, time

import httpx
import stem.control
import stem.process
from stem import Signal
from stem.control import Controller
import socket


# ignore this if not running CI tests
test_ci = 0


def getenv_or_default(environment_variable, value_if_missing):
    if environment_variable in environ:
        present_value = getenv(environment_variable)
        if type(value_if_missing) is int:
            return int(present_value)
        return present_value
    else:
        return value_if_missing


if getenv_or_default("TEST_CI", False):
    # we are doing a short test in CI!
    test_ci = 1

    # we'll test my own websites
    monitor_tor_url = "http://tweedge32j4ib2hrj57l676twj2rwedkkkbr57xcz5z73vpkolws6vid.onion/"
    uptime_report_url = "https://chris.partridge.tech/"
else:
    # check required variables
    monitor_tor_url = getenv_or_default("MONITOR_TOR_URL", False)
    uptime_report_url = getenv_or_default("UPTIME_REPORT_URL", False)

    # we're missing something :(
    if not (monitor_tor_url and uptime_report_url):
        print(f"MONITOR: Missing required environment variables - see README.md")
        exit(1)

# optional variables
monitor_tor_contents = getenv_or_default("MONITOR_TOR_CONTENTS", None)
monitor_tor_timeout = getenv_or_default("MONITOR_TOR_TIMEOUT", 30)
print_tor_messages = getenv_or_default("PRINT_TOR_MESSAGES", "bootstrap_only")
monitor_sleep = getenv_or_default("MONITOR_SLEEP", 30)
restart_after_x_failures = getenv_or_default("RESTART_AFTER_X_FAILURES", 10)
uptime_report_response_code_under = getenv_or_default("UPTIME_REPORT_RESPONSE_CODE_UNDER", 300)


# osminogin/docker-tor-simple variables (don't change these)
SOCKS_PORT = 9050
CONTROL_PORT = 9051


def tor_get(monitor_tor_url, monitor_tor_contents, monitor_tor_timeout):
    time_start = time()

    # check if Tor control port is responsive before attempting connection
    try:
        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            bootstrap_status = controller.get_info("status/bootstrap-phase")
            print(f"TOR: Bootstrap status: {bootstrap_status}")
    except Exception as e:
        print(f"FAIL: Cannot connect to Tor control port: {str(e)}")
        return False

    # check circuit status
    try:
        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            circuits = controller.get_circuits()
            streams = controller.get_streams()
            print(f"DEBUG: {len(circuits)} circuits, {len(streams)} streams")
            for circuit in circuits[:3]:  # show first 3 circuits
                print(f"DEBUG: Circuit {circuit.id} status: {circuit.status}")
    except Exception as debug_e:
        print(f"WARN: Could not get circuit info: {str(debug_e)}")

    # check SOCKS port responsiveness before making the request
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(("127.0.0.1", SOCKS_PORT))
        sock.close()
        if result == 0:
            print("DEBUG: SOCKS port 9050 is reachable")
        else:
            print("DEBUG: SOCKS port 9050 is not reachable")
    except Exception as sock_e:
        print(f"WARN: Error checking SOCKS port: {str(sock_e)}")

    # clearly identify ourselves
    headers = {"User-Agent": "httpx from tweedge/tor-uptime-monitor"}
    # Tor uses port 9050 as the default SOCKS port, and we must use it for DNS resolution, so we'll need to specify SOCKS5H
    session = httpx.Client(proxy=f"socks5h://127.0.0.1:{SOCKS_PORT}", headers=headers)

    try:  # now actually attempt to fetch the page
        result = session.get(monitor_tor_url, timeout=monitor_tor_timeout)
    except httpx.TimeoutException:
        print(f"FAIL: Fetch timed out on {monitor_tor_url} after {monitor_tor_timeout}s")
    except httpx.ConnectError as e:
        if "TTL expired" in str(e):
            print(f"FAIL: Tor circuit TTL expired on {monitor_tor_url}")
        else:
            print(f"FAIL: Connection failed on {monitor_tor_url} due to {str(e)}")
        return False
    except Exception as e:
        print(f"FAIL: Fetch failed on {monitor_tor_url} due to exception {str(e)}")
        return False

    if monitor_tor_contents:
        if not monitor_tor_contents in result.text:
            print(f"FAIL: Fetch completed but couldn't find {monitor_tor_contents} in {monitor_tor_url}")
            return False

    time_taken = round(time() - time_start, 3)
    print(f"OK: Fetched and validated the target URL in {time_taken}s")
    return True


def report_success(uptime_report_url, uptime_report_response_code_under):
    try:
        reported = httpx.get(uptime_report_url)
        reported_status = reported.status_code
        if reported_status < uptime_report_response_code_under:
            print(f"OK: Reported success to uptime monitor (response code: {reported_status})")
        else:
            print(f"WARN: Unexpected response code ({reported_status}) from {uptime_report_url}")
    except Exception as e:
        print(f"WARN: Exception {str(e)} occurred when accessing uptime monitor {uptime_report_url}")


def selectively_print_tor_messages(line):
    if print_tor_messages == "bootstrap_only":
        if "Bootstrapped " in line:
            print(f"TOR: {line}")
    else:
        print(f"TOR: {line}")


print("MONITOR: Starting up tor and preparing to monitor")

tor_process = stem.process.launch_tor_with_config(
    config={
        "SocksPort": str(SOCKS_PORT),
        "ControlPort": str(CONTROL_PORT),
        # more aggressive circuit creation and management
        "CircuitBuildTimeout": "30",  # faster circuit building (default is 60)
        "LearnCircuitBuildTimeout": "1",  # adapt timeouts based on network conditions
        "CircuitStreamTimeout": "30",  # shorter stream timeout to fail fast
        "KeepalivePeriod": "30",  # send keepalive every 30 seconds
        "MaxCircuitDirtiness": "600",  # keep circuits alive for 10 minutes (default is 10m)
        "MaxClientCircuitsPending": "32",  # allow more pending circuits
        "NumEntryGuards": "3",  # use 3 entry guards for redundancy
        "UseEntryGuards": "1",  # always use entry guards
        "StrictNodes": "0",  # not strict about node selection)
        "CircuitPriorityHalflife": "30",  # circuit priority half-life
        "CloseHSClientCircuitsImmediatelyOnTimeout": "1",  # close onion circuits on timeout
        # performance-focused relay selection
        "UseBridges": "0",  # don't use bridges
        "LongLivedPorts": "80,443",  # treat web ports as long-lived
        # aggressive unhealthy circuit removal
        "MaxOnionsPending": "100",  # allow more pending onion connections
        "TrackHostExitsExpire": "1800",  # expire tracking after 30 minutes
    },
    init_msg_handler=selectively_print_tor_messages,
)

repeated_exceptions = 0

while repeated_exceptions < restart_after_x_failures:
    sleep(monitor_sleep)
    response = tor_get(monitor_tor_url, monitor_tor_contents, monitor_tor_timeout)

    if response:
        repeated_exceptions = 0
        report_success(uptime_report_url, uptime_report_response_code_under)
    else:
        repeated_exceptions += 1
        with Controller.from_port(port=CONTROL_PORT) as controller:
            controller.authenticate()
            circuits = controller.get_circuits()

            # ensure we have at least one healthy circuit
            healthy_circuits = [c for c in circuits if c.status == "BUILT"]
            if len(healthy_circuits) == 0:
                print("MONITOR: No healthy circuits found, sending NEWNYM signal to Tor")
                controller.signal(Signal.NEWNYM)

    # if we're testing, run a couple times before exiting
    if test_ci > 0:  # 0 if not testing, 1 if testing
        test_ci += 1
        if test_ci > 3:  # stop after a few tests
            if repeated_exceptions == 0:  # no issues?
                print("SHORT TEST: Completed with no failures!")
                exit(0)
            else:  # possibly an issue!
                print("SHORT TEST: FAILED! Check preceding logs.")
                exit(1)

print("MONITOR: Restarting because we've failed too many times in a row")
exit(1)
