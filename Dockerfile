FROM python:3.12-alpine

RUN pip install --no-cache-dir googlemaps redis requests tzdata
COPY traffic-alert.py /traffic-alert.py
ENTRYPOINT ["/usr/local/bin/python", "/traffic-alert.py"]
