FROM python:alpine

RUN pip install googlemaps tinydb
COPY traffic-alert.py /traffic-alert.py
ENTRYPOINT ["/usr/local/bin/python", "/traffic-alert.py"]
