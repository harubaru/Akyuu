FROM python:3.9.6
ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH "${PYTHONPATH}:/"

RUN mkdir /akyuu
WORKDIR /akyuu

COPY . /akyuu
RUN pip install --upgrade pip
RUN pip install -r requirements.txt