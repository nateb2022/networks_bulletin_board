import json
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

    def put(self, value):
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
# We have to force get, as well as pop to occur in the same lock
# otherwise we could have a race condition where the queue is empty when we try to pop, but not when we check the size.
# This would cause an exception to be raised, even though there is an item in the queue.
    def get(self, timeout=None):
        #grabs the thread lock
        with self._cond:
            # waits for the queue to have an item to pop, if the queue is empty it will wait for a specified timeout period before raising an exception.
            if not self._cond.wait_for(lambda: self._size > 0, timeout):
                raise EmptyQueueException("Queue is empty")
            #if we call pop, the queue is not empty, so we can grab the front node
            return self._pop()
    def pop(self):
        #using the thread lock, we grab the front node object, change the head pointer to the next node, and return the value of the front node. If the queue is empty, we raise an exception.
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return node.value
    def get_nowait(self):
        with self._cond:
            #this is a non-blocking version of get, it will raise an exception if the queue is empty, rather than waiting for an item to be added, saves threads from being blocked if they are waiting for an item to be added to the queue.
            if self._size == 0:
                raise EmptyQueueException("Queue is empty")
            return self._pop()
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
        self.responses = queue() #These are replies
        self.notifications = queue() #These are captured notifications from the server
        self.lock = threading.Lock()
        #Thread that will read the socket, and place the responses in the queue.
        threading.Thread(target=self._read_loop, daemon=True).start()


    def _read_loop(self):
        while True:
            line = self.reader.readline()
            if not line:
                break
            line = line.decode("utf-8").rstrip("\r\n")
            if line.startswith("HTTP/"):
                #Grab status line
                status_line = int(line.split(" ")[1])

                #read headers
                content_length = 0
                while True:
                    header = self.reader.readline().decode("utf-8").rstrip("\r\n")
                    if header == "":
                        break
                    name, value = header.partition(":")

                    if name.lower() == "content-length":
                        content_length = int(value.strip())

                #read body
                body = self.reader.read(content_length).decode("utf-8")
                #throw the response in the response queue
                self.responses.put((status_line, body))

            #for notifications, we will just put them in the notification queue
            elif line.startswith("{"):
                self.notifications.put(line)
            
    def send_request(self, method, path, params):
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
                with self.lock:
                    #sends the request line to the server and waits for a response to be placed in the response queue.
                    self.socket.sendall(request_line.encode('utf-8'))
                    status_line, body = self.responses.get(timeout=5)
                data = json.loads(body) if body else None
                return status_line, data

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

    def create_post(self, params):
        """Send an HTTP request to the server"""
        try:
            status_line, data = self.send_request("POST", "/messages", params)
            print(status_line, data)
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

if __name__ == "__main__":
    client = HttpClient()
    client.connect()
    if client.socket is None:
        print("Failed to connect to the server.")

    print("Welcome to the Bulletin Board Client! type exit to quit and help for a list of commands.")

    try:
        while True:
            command = input("Enter command: ")
            if command.lower() == "exit":
                print("Disconnecting from the server...")
                client.disconnect()
                break
            elif command.lower() == "connect":
                if client.socket is None:
                    client.connect()
                    if client.socket is None:
                        print("Failed to connect to the server.")
                    else:
                        print("Connected to the server.")
                else:
                    print("Already connected to the server.")
            elif command.lower() == "help":
                print("Available commands:")
                print("  exit - disconnect and exit the client")
                print("  connect - Connect to the server")
                print("  post <group_id> <subject> <message_content> - Create a new post with the specified message")
                print("  help - Show this help message")
                print("  join <board_name> - Join a specific board")
                print("  get_users - Get the list of users")
                print("  get_messages <message_id> - Get the list of messages")
            elif command.startswith("join "):
                board_name = command.split(" ", 1)[1]
                response = client.join_board(board_name)
                print(f"Server response: {response}")
            elif command == "get_users":
                response = client.get_users()
                print(f"Server response: {response}")
            elif command.startswith("get_messages "):
                message_id = command.split(" ", 1)[1]
                response = client.get_messages(message_id)
                print(f"Server response: {response}")
            elif command.startswith("post "):
                # splits the command into its components
                parts = command.split(" ", 3)
                if len(parts) == 4:
                    group_id = parts[1]
                    subject = parts[2]
                    message_content = parts[3]
                    params = {
                        "group_id": group_id,
                        "subject": subject,
                        "message_content": message_content
                    }
                    response = client.create_post(params)
                    print(f"Server response: {response}")
                else:
                    print("Invalid 'post' command format. Use: post <group_id> <subject> <message_content>")
            else:
                print("Unknown command. Type 'help' for a list of commands.")
                continue
    except KeyboardInterrupt:
        print("\n Interrupt, Client shutting down.")
    finally:
        client.disconnect()