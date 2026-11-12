from WebServer import HttpRequest
from socket import *

class Server:
    def __init__(self):
        self.connections = []
        self.messages = []

    def accept_new_connection(self):
        return

    def main(self):
        #set the port
        port = 6789
        #create the servers listening socket
        listen_socket = socket(AF_INET, SOCK_STREAM)
        listen_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        listen_socket.bind(('', port))
        listen_socket.listen(5)
        listen_socket.settimeout(1)
        print(f"Server listening on port {port}")

        try:
            while True:
                #accept a new connection on the servers listening socket
                try:
                    conn, addr = listen_socket.accept()
                    #Print info about new connection
                except timeout:
                    continue
                print(f"Accepted connection from {addr}")
                #Create a new object to process the message
                new_request = HttpRequest(conn)
                #start a new thread
                new_request.start()
        except KeyboardInterrupt:
            print("Server shutting down.")
        finally:
            listen_socket.close()