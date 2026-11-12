import re
import socket

"""
This is the main FTP client. Study the code and figure out what
each function does before adding to it. You only need to add code
wherever you see a '?'

Assignment 1
Nate Barnhart
"""

CRLF = "\r\n"
loopback = "127.0.0.1"

class FtpClient:

    def __init__(self):
        self.debug = False  # Debug flag
        self.control_socket = None
        self.control_reader = None
        self.control_writer = None
        self.current_response = ""

    def connect(self, username, password):
        """
        Connect to the FTP server
        :param username: the username you use to login to your FTP session
        :param password: the password associated with the username
        """
        try:
            # establish the control socket
            self.control_socket = socket.create_connection((loopback, 21))

            # get references to the socket input and output streams
            self.control_reader = self.control_socket.makefile("r")
            self.control_writer = self.control_socket.makefile("wb")

            # check if the initial connection response code is OK
            if self._check_response(220):
                print("Successfully connected to FTP server")
            # send user name and password to ftp server
            self._send_command(f"USER {username}{CRLF}", 331)
            self._send_command(f"PASS {password}{CRLF}", 230)

        except socket.gaierror as ex:
            print(f"UnknownHostException: {ex}")
        except OSError as ex:
            print(f"IOException: {ex}")

    def get_file(self, file_name):
        """
        Retrieve the file from FTP server after connection is established
        :param file_name: the name of the file to retrieve
        """
        data_port = 0  # initialize the data port
        try:
            # change to current (root) directory first
            self._send_command(f"CWD /{CRLF}", 250)

            # set to passive mode and retrieve the data port number from response
            self.current_response = self._send_command(f"PASV{CRLF}", 227)
            data_port = self._extract_data_port(self.current_response)

            # connect to the data port
            data_socket = socket.create_connection((loopback, data_port))
            data_reader = data_socket.makefile("rb")

            # download file from ftp server
            self._send_command(f"RETR {file_name}{CRLF}", 150)

            # check if the transfer was successful
            self._check_response(226)

            # Write data on a local file
            self._create_local_file(data_reader, file_name)

        except socket.gaierror as ex:
            print(f"UnknownHostException: {ex}")
        except OSError as ex:
            print(f"IOException: {ex}")

    def disconnect(self):
        """Close the FTP connection"""
        try:
            self.control_reader.close()
            self.control_writer.close()
            self.control_socket.close()
        except OSError as ex:
            print(f"IOException: {ex}")

    def _send_command(self, command, expected_response_code):
        """
        Send ftp command
        :param command: the full command line to send to the ftp server
        :param expected_response_code: the expected response code from the ftp server
        :return: the response line from the ftp server after sending the command
        """
        response = ""
        try:
            # send command to the ftp server
            self.control_writer.write(command.encode("ascii"))
            self.control_writer.flush()

            # get response from ftp server
            response = self.control_reader.readline().rstrip("\r\n")
            if self.debug:
                print("Current FTP response:", response)

            # check validity of response
            if not response.startswith(str(expected_response_code)):
                raise IOError("Bad response: " + response)
        except IOError as ex:
            print(f"IOException: {ex}")
        return response

    def _check_response(self, expected_code):
        """
        Check the validity of the ftp response, the response code should
        correspond to the expected response code
        :param expected_code: the expected ftp response code
        :return: response status: True if successful code
        """
        response_status = True
        try:
            self.current_response = self.control_reader.readline().rstrip("\r\n")
            if self.debug:
                print("Current FTP response:", self.current_response)
            if not self.current_response.startswith(str(expected_code)):
                response_status = False
                raise IOError("Bad response: " + self.current_response)
        except IOError as ex:
            print(f"IOException: {ex}")
        return response_status

    def _extract_data_port(self, response_line):
        """
        Given the complete ftp response line of setting data transmission mode
        to passive, extract the port to be used for data transfer
        :param response_line: the ftp response line
        :return: the data port number
        """
        data_port = 0
        match = re.search(r"\((.*?)\)", response_line)
        parts = [""] * 6
        if match:
            parts = match.group(1).split(",")
        if self.debug:
            print(f"Port integers: {parts[4]},{parts[5]}")
        data_port = int(parts[4]) * 256 + int(parts[5])
        if self.debug:
            print("Data Port:", data_port)
        return data_port

    def _create_local_file(self, data_reader, file_name):
        """
        Create the file locally after retrieving data over the FTP data stream.
        :param data_reader: the data input stream
        :param file_name: the name of the file to create
        """
        try:
            with open(file_name, "wb") as fos:
                while True:
                    chunk = data_reader.read(1024)
                    if not chunk:
                        break
                    fos.write(chunk)
            data_reader.close()
        except FileNotFoundError as ex:
            print(f"FileNotFoundException {ex}")
        except OSError as ex:
            print(f"IOException: {ex}")