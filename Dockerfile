FROM osminogin/tor-simple

USER root

COPY ./monitor.py /opt/monitor.py

RUN apk add --no-cache python3 py3-httpx py3-stem py3-pysocks

USER tor

CMD ["python3", "-u", "/opt/monitor.py"]