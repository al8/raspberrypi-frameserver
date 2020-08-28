import socket
import sys
import argparse


def send_remote_command(host, port, command, arguments):
    if len(options.arg) > 0:
        data = command + "\t" + "\t".join(arguments)
    else:
        data = command

    # Create a socket (SOCK_STREAM means a TCP socket)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server and send data
        sock.connect((host, port))
        sock.sendall(data + "\n")

        received = ""
        # Receive data from the server and shut down
        r = sock.recv(4096)
        received += r
        while r:
            r = sock.recv(4096)
            received += r
    finally:
        sock.close()

    print "Sent:     {}".format(data)
    print "Received: {}".format(received)

    return received

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='client')
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--action", type=str, default=None)
    parser.add_argument("-a", "--arg", default=[], action="append")
    options = parser.parse_args()

    HOST, PORT = options.host, options.port

    recv = send_remote_command(HOST, PORT, options.action, options.arg)
