# syntax=docker/dockerfile:1
FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /vr_app
COPY requirements.txt /vr_app/
RUN pip install -r requirements.txt
COPY . /vr_app/