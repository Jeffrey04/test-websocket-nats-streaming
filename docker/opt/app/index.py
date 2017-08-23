from functools import partial
from nats_stream.aio.client import StreamClient
from nats_stream.aio.subscriber import Subscriber
from nats_stream.aio.publisher import Publisher

from aiohttp import web
import asyncio
import signal
import aiohttp
import logging
from uuid import uuid4
from datetime import datetime

logging.basicConfig(level=logging.INFO & logging.DEBUG & logging.ERROR,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


async def reconnected_cb(sc):
    logger.info("{}: Connected to NATS at {}...".format(datetime.now().isoformat(),
                                                        sc.nc.connected_url.netloc))


async def signal_handler(sc, client):
    if sc.nc.is_closed:
        return
    logger.info("Disconnecting...")
    try:
        asyncio.get_event_loop().create_task(client.unsubscribe())
    except AttributeError:
        pass
    await asyncio.sleep(2)
    asyncio.get_event_loop().create_task(sc.close())


async def _send(item, ws):
    await ws.send_str('{}/from-nats-streaming'.format(item.data.decode('utf-8')))


def signal_register_handler(*args):
    for sig in ("SIGINT", "SIGTERM"):
        for sc, client in args:
            asyncio.get_event_loop().add_signal_handler(
                getattr(signal, sig),
                partial(signal_handler, sc, client))


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sc_pub, sc_sub = StreamClient(), StreamClient()

    _channel = 'test-chatroom'

    pub = Publisher(sc_pub,
                    _channel,
                    lambda ack: logger.info('{}: ack: {}'.format(
                        datetime.now().isoformat(),
                        ack)))
    sub = Subscriber(sc_sub,
                     _channel,
                     partial(_send, ws=ws),
                     max_inflight=100,
                     start_position=0)

    signal_register_handler(((sc_sub, sub), (sc_pub, pub)))

    await sc_pub.connect('test-cluster',
                         'test-pub-{}'.format(uuid4().hex),
                         servers=['nats://streaming:4222'],
                         io_loop=asyncio.get_event_loop(),
                         reconnected_cb=partial(reconnected_cb, sc_sub))

    await sc_sub.connect('test-cluster',
                         'test-sub-{}'.format(uuid4().hex),
                         servers=['nats://streaming:4222'],
                         io_loop=asyncio.get_event_loop(),
                         reconnected_cb=partial(reconnected_cb, sc_sub))

    await sub.subscribe()

    await pub.publish('MoTD'.encode('utf-8'))

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                await pub.publish(msg.data.encode('utf-8'))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.info('ws connection closed with exception %s' %
                        ws.exception())

    logger.info('websocket connection closed')
    await signal_handler(sc_sub, sub)
    await signal_handler(sc_pub, pub)

    return ws

app = web.Application()
app.router.add_get('/api/chat', websocket_handler)
web.run_app(app)
