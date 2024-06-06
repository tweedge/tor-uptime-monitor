# tor-uptime-monitor

[![DockerHub Link](https://img.shields.io/docker/pulls/tweedge/tor-uptime-monitor)](https://hub.docker.com/repository/docker/tweedge/tor-uptime-monitor)
[![License](https://img.shields.io/github/license/tweedge/tor-uptime-monitor)](https://github.com/tweedge/tor-uptime-monitor)
[![Written By](https://img.shields.io/badge/written%20by-some%20nerd-red.svg)](https://chris.partridge.tech)
[![Author Also Writes On](https://img.shields.io/mastodon/follow/108210086817505115?domain=https%3A%2F%2Fcybersecurity.theater)](https://cybersecurity.theater/@tweedge)

A small (30MB!) Docker image based on [osminogin/tor-simple](https://hub.docker.com/r/osminogin/tor-simple/), configured with environment variables, which checks to see if a Tor site is online and pings a (clearnet) uptime monitor if so. This was intended to be a one-stop-shop to increase assurance that my Tor site is up, connecting Tor uptime to monitors that have the ability to remind me via emails/texts/etc.

*Tor is bundled in this Docker image and controlled via [stem](https://stem.torproject.org/)!* It's completely hands-free and works natively in plain old Docker. Whenever the URL can't be accessed over Tor, instead of failing immediately it'll also request a new identity via sending `NEWNYM` to the Tor control port, which can help move the monitor to a better-functioning circuit.

### Example Usage

```
$ docker run --detach \
    --name tor-uptime-monitor \
    --restart=always \
    -e MONITOR_TOR_URL=http://tweedge32j4ib2hrj57l676twj2rwedkkkbr57xcz5z73vpkolws6vid.onion/ \
    -e UPTIME_REPORT_URL=https://ping.ohdear.app/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee \
    tweedge/tor-uptime-monitor
```

### Configuration

Two environment variables **must** be set (and the container will stop if these are missing):

* `MONITOR_TOR_URL` is the URL that you want to access on Tor, ex. your Onion site
* `UPTIME_REPORT_URL` is the URL what you want to access whenn (and only when) your Tor site was successfully accessed

The following environment variables are also available to configure your monitor's behavior:

* `MONITOR_TOR_CONTENTS` **[HIGHLY RECOMMENDED]** is a string that must be present in the body of the URL you're checking on Tor, to ensure your site is truly up and not returning an error (default: don't check for any text)
* `MONITOR_TOR_TIMEOUT` configures the request timeout (in seconds) while fetching the URL you're checking via Tor (default: 30)
* `MONITOR_SLEEP` configures how long (in seconds) to sleep between attempts to access the URL on Tor (default: 30)
* `RESTART_AFTER_X_FAILURES` configures how many consecutive failures to tolerate before exiting this script, which if you've set the Docker restart policy to "always," prompts creation of a new container (default: 5)
* `UPTIME_REPORT_RESPONSE_CODE_UNDER` configures when to show a warning in the logs if a the uptime reporting URL gave an unexpectedly high response code (default: 300 - i.e. any sub-300 response code is OK and won't show a warning)
