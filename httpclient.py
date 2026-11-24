import socket
import os
import threading
#This is our node for the queue
class _Node:
    def __init__(self, value):
        self.value = value
        self.next = None
class EmptyQueueException(Exception):
    pass
#Buidling a queue class to store responses from the server. This will allow for multiple responses to be stored and processed in order.
#This queue will also be able to handle different types of responses, such as text or binary data, and will be able to handle different types of requests, such as GET or POST.
class queue:
    def __init__(self):
        #These are our internal pointers to the head and tail of the queue, as well as a size counter and a condition variable for thread synchronization.
        self._head = None
        self._tail = None
        self._size = 0
        #this threading condition will allow us to synchronize access to the queue between multiple threads, ensuring that only one thread can modify the queue at a time.
        self._cond = threading.Condition()

    def enqueue(self, value):
        node = _Node(value)
        #checks if the thread lock is free
        with self._cond:
            #If the queue is empty, set the head and tail to the new node. Otherwise, add the new node to the end of the queue and update the tail pointer.
            if self._tail is None:
                self._head = self._tail = node
            else:
                self._tail.next = node
                self._tail = node
            self._size += 1
            self._cond.notify()

    def dequeue(self):
        with self._cond:
            if not self.is_empty():
                value = self._head.value
                self._head = self._head.next
                if not self._head:
                    self._tail = None
                self._size -= 1
                return value
            else:
                raise EmptyQueueException("Queue is empty")

    def is_empty(self):
        with self._cond:
            return self._size == 0
    
    def __len__(self):
        with self._cond:
            return self._size
class HttpClient:
    def __init__(self, host="localhost", server_port=6789):
        self.socket = socket.create_connection((host, server_port))
        self.reader = self.socket.makefile("rb")
        self.response = queue()
        self.lock = threading.Lock()
 

    def send_request(self, method, path, params):
            """Send an HTTP request to the server and return the response"""
            try:
                # checks for a connection and connects if not connected
                if not self.socket:
                    self.connect()
                #checks for parameters and appends them to the path if they exist
                if params:
                    parts = []
                    for key, value in params.items():
                        #Escapes quotes and backslashes in the parameter values to ensure they are properly formatted for the query string.
                        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
                        #attaches a key to a vaulue for the request
                        parts.append(f"{key}={escaped}")
                    #Builds the query string in the "?key="value"&"key2="value2" format and appends it to the path.
                    query_string = "?" + "&".join(parts)
                #Build the final request line:
                request_line = f"{method} {path}{query_string} HTTP/1.0\r\n\r\n"
                self.socket.sendall(request_line.encode('utf-8'))
            except OSError as ex:
                print(f"IOException: {ex}")
                return None
               
              

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

    