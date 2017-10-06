import socket
import SocketServer
import threading

import select
import sqlalchemy
import time
import errno
from time import sleep

import sys
from socket import _fileobject, timeout

from select import poll, POLLIN, POLLOUT, POLLERR
from select import epoll, EPOLLIN, EPOLLOUT, EPOLLERR

from sqlalchemy import create_engine, Table, Column, Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, TEXT, TIMESTAMP, BIGINT
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from socket import error as SocketError
from sqlalchemy.engine import reflection

PORT_ = sys.argv[1]
DESTINATION_ = sys.argv[2]
PROXY_ID_ = sys.argv[3]

print "PORT_:" + PORT_
print "DESTINATION_:" + DESTINATION_
print "PROXY_ID_:" + PROXY_ID_

db_engine = create_engine(
    'postgresql://postgres:postgres@localhost:5432/postgres')
db_connection = db_engine.connect()
meta = sqlalchemy.MetaData(bind=db_connection, reflect=True, schema="jltc")
insp = reflection.Inspector.from_engine(db_engine)
Session = sessionmaker(bind=db_engine)
db_session = Session()


def _poll(reads, writes, exceptions, timeout):
    pollfunc = epoll
    read_flag = EPOLLIN
    write_flag = EPOLLOUT
    exc_flag = EPOLLERR
    p = pollfunc()
    for fd in reads:
        p.register(fd, read_flag)
    for fd in writes:
        p.register(fd, write_flag)
    for fd in exceptions:
        p.register(fd, exc_flag)
    return p.poll(timeout)


def _select(readlist, writelist, exceptionallist, timeout):
    return _poll(readlist, writelist, exceptionallist, timeout)


def wait_to_read_data(socket, timeout=0.0):
    sockets = _select([socket], [], [], timeout)
    if isinstance(sockets, tuple):
        return sockets[0]
    return sockets


def wait_to_write_data(socket, timeout=0.0):
    sockets = _select([], [socket], [], timeout)
    if isinstance(sockets, tuple):
        return sockets[1]
    return sockets


if not db_engine.dialect.has_table(db_engine.connect(), "delay_table"):
    delay_table = Table(
        'delay_table',
        meta,
        Column('value', DOUBLE_PRECISION), )
    meta.create_all(db_connection)

proxy = meta.tables['jltc.proxy']


def get_delay(proxy_id):
    statement = sqlalchemy.sql.select(
        [proxy.c.delay]).where(proxy.c.id == proxy_id)
    x = execute_statement(statement, False)[0][0]
    return float(x)


def execute_statement(statement, with_header):
    #log.debug("Executing SQL-query: " + str(statement))
    q = db_engine.execute(statement)
    output = []
    fieldnames = []

    for fieldname in q.keys():
        fieldnames.append(fieldname)

    if with_header:
        output.append(fieldnames)

    for row in q.fetchall():
        values = []
        for fieldname in fieldnames:
            values.append(row[fieldname])

        output.append(values)
    return output


current_incomings = []
current_forwarders = []
BUFFER_SIZE = 4096


class Forwarder(threading.Thread):
    def __init__(self, source):
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.source = source
        self.destination = \
         socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.destination.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.destination.connect((DESTINATION_, 443))
        self.connection_string = str(self.destination.getpeername())
        print "[+] New forwarder: " + self.connection_string

    def run(self):
        try:
            while 1:
                r = wait_to_read_data(self.destination, 1.0)
                if not r:
                    print "[<] Timeout to wait the data from destination"
                else:
                    data = self.destination.recv(BUFFER_SIZE)
                    if len(data) == BUFFER_SIZE:
                        print "[<] Trying to get data from destination"
                        while 1:
                            try:
                                data += self.destination.recv(
                                    BUFFER_SIZE, socket.MSG_DONTWAIT)
                            except:
                                break
                    if data == "":
                        self.close_connection()
                        break
                    print "[<] Received from destination: " + str(len(data))
                    self.source.write_to_source(data)
        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise
            pass
        print "[-] Closed destination"

    def write_to_dest(self, data):
        print "[>] Sending to destination: " + str(len(data))
        wlist = wait_to_write_data(self.destination, 1.0)
        if not wlist:
            raise timeout()
        self.destination.send(data)

    def close_connection(self):
        try:
            self.source.request.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        #self.source.request.close()


class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        delay = get_delay(PROXY_ID_)
        print "[**] Delay: " + str(delay)
        time.sleep(delay)
        self.connection_string = str(self.request.getpeername())
        self.request.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print "[+] Incoming connection:" + str(self.connection_string)
        f = Forwarder(self)
        f.start()
        try:
            while 1:
                r = wait_to_read_data(self.request, 1.0)
                if not r:
                    print "[>] Timeout to wait the data from incoming connection"
                else:
                    print "[>] Trying to get data from incoming connection"
                    data = self.request.recv(BUFFER_SIZE)
                    if (len(data) == BUFFER_SIZE):
                        while 1:
                            try:  #error means no more data
                                data += self.request.recv(BUFFER_SIZE,
                                                          socket.MSG_DONTWAIT)
                            except:
                                break
                    f.write_to_dest(data)
                    if data == "":
                        #f.close_connection()
                        break
                    print "[>] Data from incoming connection: " + str(
                        len(data))

        except SocketError as e:
            if e.errno != errno.ECONNRESET:
                raise
            pass
        print "[-] Close incoming connection"

    def write_to_source(self, data):
        print "[<] Sending to incoming connect: " + str(len(data))
        wlist = wait_to_write_data(self.request, 1.0)
        if not wlist:
            raise timeout()
        self.request.send(data)


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass


if __name__ == "__main__":
    HOST, PORT = "", PORT_
    server = ThreadedTCPServer((HOST, int(PORT)), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    print "[*] LINUX Starting proxy on port: ", port
    try:
        while True:
            sleep(1)
    except:
        pass
    print "[*] Stopping proxy..."
    server.shutdown()
