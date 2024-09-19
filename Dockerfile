FROM python:alpine

RUN pip install googlemaps tinydb
COPY test.py /test.py
ENTRYPOINT ["/usr/local/bin/python", "/test.py"]
