FROM python:3

RUN pip install bottle bottle-websocket asyncio-nats-streaming-client ujson aiohttp
COPY opt/app /opt/app

EXPOSE 8080

CMD ["python", "/opt/app/index.py"]