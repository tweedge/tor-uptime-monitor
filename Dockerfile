FROM osminogin/tor-simple

USER root

COPY ./monitor.py /opt/monitor.py

RUN apk add --no-cache python3 py3-pip
RUN pip3 install 'requests[socks]' logtail-python stem

USER tor

CMD ["python3", "/opt/monitor.py"]