# tor-uptime-monitor

![Build Status](https://github.com/tweedge/tor-uptime-monitor/actions/workflows/publish.yml/badge.svg)
[![DockerHub Link](https://img.shields.io/docker/pulls/tweedge/tor-uptime-monitor)](https://hub.docker.com/repository/docker/tweedge/tor-uptime-monitor)
[![License](https://img.shields.io/github/license/tweedge/tor-uptime-monitor)](https://github.com/tweedge/tor-uptime-monitor)
[![Written By](https://img.shields.io/badge/written%20by-some%20nerd-red.svg)](https://chris.partridge.tech)
[![Author Also Writes On](https://img.shields.io/mastodon/follow/108210086817505115?domain=https%3A%2F%2Fcybersecurity.theater)](https://cybersecurity.theater/@tweedge)

A small (28MB compressed!) Docker image based on [osminogin/tor-simple](https://hub.docker.com/r/osminogin/tor-simple/), [httpx](https://www.python-httpx.org/), and socksio, which checks to see if a Tor site is online and pings a (clearnet) uptime monitor if so. It can be configured with as few as 2 environment variables. This was created to be a simple mechanism to increase assurance that my Tor site is up, connecting my Tor site's uptime to monitors that have the ability to remind me via emails/texts/etc.

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

The following environment variables are available to configure your monitor's behavior:

* `MONITOR_TOR_CONTENTS` **[HIGHLY RECOMMENDED]** is a string that must be present in the body of the URL you're checking on Tor, to ensure your site is truly up and not returning an error (default: don't check for any text)
* `MONITOR_TOR_TIMEOUT` configures the request timeout (in seconds) while fetching the URL you're checking via Tor (default: 30)
* `MONITOR_SLEEP` configures how long (in seconds) to sleep between attempts to access the URL on Tor (default: 30)

And if you're a real nerd, you can also tweak these probably-OK-to-leave-at-default variables:

* `PRINT_TOR_MESSAGES` configures what messages you want to see from Tor. Currently this has one option: `bootstrap_only` (which is the default) will only print bootstrapping messages so you can see if Tor comes up. Setting this to anything else will print all messages from Tor.
* `RESTART_AFTER_X_FAILURES` configures how many consecutive failures to tolerate before exiting this script, which if you've set the Docker restart policy to "always," prompts creation of a new container (default: 5)
* `UPTIME_REPORT_RESPONSE_CODE_UNDER` configures when to show a warning in the logs if a the uptime reporting URL gave an unexpectedly high response code (default: 300 - i.e. any sub-300 response code is OK and won't show a warning)

### Automatic Updates

As Tor users may be more sensitive to minor security or privacy updates than the norm, this package is automatically rebuilt weekly, ensuring all dependencies are kept up to date. A short test is performed to ensure the new version is able to access my site over Tor, and if the test passes with no errors, the new image is automatically published to `tweedge/tor-uptime-monitor:latest`.

You can ensure that your copy of this uptime monitor is kept up to date automatically (with all your environment variables/settings intact!) by using [watchtower](https://hub.docker.com/r/containrrr/watchtower).