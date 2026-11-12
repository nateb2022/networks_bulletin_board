from csv import writer
from socket import *
import threading
from wsgiref import headers
from FtpClient import FtpClient

"""
Assignment 1
Nate Barnhart
"""
def main():
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
            newRequest = HttpRequest(conn)
            #start a new thread
            newRequest.start()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        listen_socket.close()  

class HttpRequest(threading.Thread):
    CRLF = "\r\n"
    #Thread class to handle HTTP requests
    def __init__(self, conn):
        super().__init__(daemon=True)
        #store the connection object
        self.conn = conn


    def run(self):
        #receive the HTTP request from the client
        try:
            self.process_request()
        except Exception as e:
            print(f"Error processing request: {e}")
        finally:
            self.conn.close()
    def contentType(self, file_name):
        if file_name.endswith(".txt"):
            return "text/plain"
        if file_name.endswith(".html"):
            return "text/html"
        elif file_name.endswith(".jpg") or file_name.endswith(".jpeg"):
            return "image/jpeg"
        elif file_name.endswith(".png"):
            return "image/png"
        elif file_name.endswith(".gif"):
            return "image/gif"
        elif file_name.endswith(".css"):
            return "text/css"
        elif file_name.endswith(".js"):
            return "application/javascript"
        else:
            return "application/octet-stream"
    def sendBytes(self, writer, file):
        #our writer object is our output stream
        #when the file exists, we want to create a buffer to hold the bytes
        #and then copy the bytes to the output stream
        buffer_size = 1024
        while True:
            chunk = file.read(buffer_size)
            #terminate the loop if no more bytes are read
            if not chunk:
                break
            writer.write(chunk)
        writer.flush()
    def process_request(self):
        #grab the sockets input and output streams, stored as objects.
        reader = self.conn.makefile('r')
        writer = self.conn.makefile('wb')
        #read the request line from the client
        request_line = reader.readline()
        #we can split the request line into its seperate pieces
        parts = request_line.split(" ")
        method = parts[0]
        path = parts[1]
        version = parts[2]
        #this will read all the headers until an empty line is encountered
        print("--- Request ---")
        print(f"Request line: {request_line}")
        while True:
            header = reader.readline().strip()
            if header == "":
                break
            print(f"Header: {header}")
        print("----------------")
        #set our staus line, header and body to null for now
        status_line = None
        contentTypeLine = None
        #Change file path to local path for system
        file_name = "." + path
        #open the file, if it exists, and read its contents, if not, set fileExists to False
        #The file object is represented by "file" within the with statement
        #instead of constructing the response based on a boolean, we can just assume that if the try block fails, the file doesnt exist
        #the try:with will close the file automatically after reading
        if(self.contentType(file_name) != "text/plain" ):
            status_line = "HTTP/1.1 403 Forbidden" + self.CRLF
            contentTypeLine = "Content-Type: " + self.contentType(file_name) + self.CRLF
            body = b"<html><body><h1>Error, invalid file type</h1></body></html>"
            writer.write(status_line.encode())
            writer.write(contentTypeLine.encode())
            writer.write(self.CRLF.encode())
            writer.write(body)
            writer.flush()
        else:
            try:
                with open(file_name, 'rb') as file:
                    status_line = "HTTP/1.1 200 OK" + self.CRLF
                    contentTypeLine = "Content-Type: " + self.contentType(file_name) + self.CRLF
                    writer.write(status_line.encode())
                    writer.write(contentTypeLine.encode())
                    writer.write(self.CRLF.encode())
                    self.sendBytes(writer, file)
                    
            except FileNotFoundError:
                status_line = "HTTP/1.1 200 OK" + self.CRLF
                contentTypeLine = "Content-Type: " + self.contentType(file_name) + self.CRLF
                body = b"<html><body><h1>File retrieved from FTP server</h1></body></html>"
                ftpStream = FtpClient()
                ftpStream.debug = True
                while True:
                    try:
                        #basically just a catch if the connect doesnt work, or if the file pull doesnt work but connect does.
                        ftpStream.connect("username", "password")
                        ftpStream.get_file(file_name)
                        break
                    finally:
                        ftpStream.disconnect()
                
            writer.write(status_line.encode())
            writer.write(contentTypeLine.encode())
            writer.write(self.CRLF.encode())
            self.sendBytes(writer, open(file_name, 'rb'))
            writer.flush()

        print("--- Response ---")
        print(status_line.strip())
        print(contentTypeLine.strip())
        print()
        print("----------------")

       


if __name__ == "__main__":
    main()