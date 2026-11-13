import socket
import os
import threading

loopback = "127.0.0.1"

class HttpClient:
    def __init__(self, server_address, server_port):
        self.server_address = loopback
        self.server_port = 80
        self.socket = None

    def connect(self):
        """Establish a connection to the HTTP server"""
        try:
            self.socket = socket.create_connection((self.server_address, self.server_port))
        except socket.gaierror as ex:
            print(f"UnknownHostException: {ex}")
        except OSError as ex:
            print(f"IOException: {ex}")

    def disconnect(self):
        """Close the HTTP connection"""
        try:
            if self.socket:
                self.socket.close()
        except OSError as ex:
            print(f"IOException: {ex}")

    def create_post(self, request):
        """Send an HTTP request to the server"""
        try:
            request = f"{request}\r\n"
            self.socket.sendall(request.encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            return response
        except OSError as ex:
            print(f"IOException: {ex}")
            return None
    def join_board(self, board_name):
        """Join a specific board on the server"""
        try:
            request = f"JOIN {board_name}\r\n"
            self.socket.sendall(request.encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            return response
        except OSError as ex:
            print(f"IOException: {ex}")
            return None
    def get_users(self):
        """Get the list of users from the server"""
        try:
            request = "GET_USERS\r\n"
            self.socket.sendall(request.encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            return response
        except OSError as ex:
            print(f"IOException: {ex}")
            return None
    def get_messages(self, message_id):
        """Get the list of messages from the server"""
        try:
            request = f"GET_MESSAGES {message_id}\r\n"
            self.socket.sendall(request.encode('utf-8'))
            response = self.socket.recv(4096).decode('utf-8')
            return response
        except OSError as ex:
            print(f"IOException: {ex}")
            return None

    