# test-websocket-nats-streaming

The code is not meant for production use, it is an experiment of using websocket to serve as a frontend for nats-streaming. It doesn't really do anything except echo whatever message sent to the endpoint.

Requires docker and docket-compose to run. In order to run just

```
docker-compose up -d
```

Then run the included test.html, and check the javascript console for output
