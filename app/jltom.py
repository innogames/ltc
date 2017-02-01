import logging
from BaseHTTPServer import HTTPServer
from SocketServer import ThreadingMixIn

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
logging.basicConfig(level=logging.INFO)
rootLogger = logging.getLogger()
logging.getLogger().addHandler(logging.StreamHandler())
fileHandler = logging.FileHandler("{0}.log".format('log'))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)


from OnlineHandler import OnlineHandler

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class JTLOM:
    def __init__(self,http_port):
        self.http_port = http_port
        self.server = ThreadedHTTPServer(('', http_port), OnlineHandler)
        #self.server.socket = ssl.wrap_socket (self.server .socket, certfile='star_innogames_de.pem', server_side=True)
    def startserver(self):
        rootLogger.info('Httpserver was started on port: ' + str(self.http_port))
        self.server.serve_forever()




