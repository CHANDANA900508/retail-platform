FROM python:3.12-slim
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .
RUN useradd -m appuser
USER appuser
ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION
ENV PAYMENT_STATUS=FIXED
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')" || exit 1
CMD ["python", "app.py"]