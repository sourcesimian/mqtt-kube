import logging

import gevent.pool
import gevent.server
import gevent.socket
import gevent.pywsgi

class Server(object):
    def __init__(self, **config):
        self._c = config
        self._server = None

    def open(self):
        logging.info('Open')
        pool = gevent.pool.Pool(10) # limit to 10 connections
        bind = (
            self._c.get('host', 'localhost'),
            int(self._c['port'])
        )
        logging.info('Server listening on: %s:%s', *bind)
        self._server = gevent.pywsgi.WSGIServer(
            bind,
            self._handle_request,
            spawn=pool)
        self._server.start()

    def close(self):
        logging.info('Close')
        self._server.stop()
        self._server = None

    def _handle_request(self, env, start_response):
        if env['PATH_INFO'] == '/health':
            start_response('200 OK', [('Content-Type', 'text/html')])
            return [b"<b>Healthy</b>"]

        if env['PATH_INFO'] == '/':
            start_response('200 OK', [('Content-Type', 'text/html')])
            return [b"<b>hello world</b>"]

        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return [b'<h1>Not Found</h1>']
