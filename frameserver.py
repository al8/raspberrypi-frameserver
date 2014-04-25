#!/usr/bin/python

import os
import sys
import SocketServer
import argparse

def getfiles(path):
    items = os.listdir(path)
    fullitems = map(lambda p: os.path.join(path, p), items)  # full path
    files = filter(os.path.isfile, fullitems)
    return map(os.path.basename, files)

class SimpleServer(SocketServer.TCPServer):
    # By setting this we allow the server to re-bind to the address by
    # setting SO_REUSEADDR, meaning you don't have to wait for
    # timeouts when you kill the server and the sockets don't get
    # closed down correctly.
    allow_reuse_address = True

class MyTCPHandler(SocketServer.StreamRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    # def __init__(self, *args, **kwargs):
    #     # self.data = ""
    #     SocketServer.StreamRequestHandler.__init__(self, *args, **kwargs)

    def handle_single(self, cmd):
        print "got command: '%s'" % cmd
        if cmd == "list":
            print "loading files from %s" % options.path
            files = getfiles(options.path)
            return "\t".join(files)
        elif cmd.startswith("del\t"):
            print "deleting files from %s" % options.path
            print "====>", cmd
            cnt = 0
            split = cmd.split("\t")[1:]
            for f in split:
                print "deleting file %s" % f
                fullname = os.path.join(options.path, f)
                if os.path.isfile(fullname):
                    os.remove(fullname)
                    cnt += 1
                else:
                    print "not a file %s" % fullname
            return str(cnt)
        else:
            return ""

    def handle(self):
        # self.request is the TCP socket connected to the client
        data = self.rfile.readline()
        print "{} wrote:".format(self.client_address[0])

        return_string = self.handle_single(data.strip())
        self.request.sendall(return_string + "\n")

        # self.data += data
        # cmd_split = self.data.split("\n")

        # self.data = cmd_split[-1]
        # cmd_split = cmd_split[:-1]

        # for cmd in cmd_split:
        #     return_string = self.handle_single(cmd)
        #     self.request.sendall(return_string + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='server')
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--path", type=str, default=".")
    options = parser.parse_args()

    HOST, PORT = "", options.port

    # Create the server, binding to localhost on port 9999
    server = SimpleServer((HOST, PORT), MyTCPHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()

