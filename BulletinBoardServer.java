import java.io.* ;
import java.net.* ;
import java.util.* ;
import java.time.*;

public final class BulletinBoardServer {
    public static void main(String[] args) throws Exception {
        int port = 6789;

        // Establish the listen socket.
        ServerSocket serverSocket = new ServerSocket(port);

        // Process HTTP service requests in an infinite loop.
        while (true) {
            // Listen for a TCP connection request.
            Socket connection = serverSocket.accept();

            OpenConnection conn = new OpenConnection(connection);
            Thread thread = new Thread(conn);
            thread.start();
        }
    }
}

final class Message {
    public int messageId;
    public String sender;
    public Instant timestamp;
    public String subject;
    public String body;
}

final class OpenConnection implements Runnable {
    final static String CRLF = "\r\n";
    static List<Message> messages = new ArrayList<>();
    static List<Socket> connections = new ArrayList<>();
    Socket socket;
    String username;
    DataOutputStream os;

    // Constructor
    public OpenConnection(Socket socket) throws Exception {
        this.socket = socket;
        this.username = "";
        this.os = new DataOutputStream(socket.getOutputStream());
    }

    // Implement the run() method of the Runnable interface.
    public void run() {
        try {
            processRequests();
        } catch (Exception e) {
            System.out.println(e);
        }
    }

    private void processRequests() throws Exception {
        InputStream is = socket.getInputStream();
        BufferedReader br = new  BufferedReader(new InputStreamReader(is));

        while (true) {
            String requestLine = br.readLine();
            if (requestLine == null) {   // client disconnected
                break;
            }

            // Extract the filename from the request line.
            handleRequest(requestLine);

            while (!br.nextLine().equals("")) {}

        }
        br.close();
        handleDisconnect();
    }

    private void handleRequest(String requestLine) {
        StringTokenizer tokens = new StringTokenizer(requestLine, " ?=&");
        String method = tokens.nextToken();
        String fileName = tokens.nextToken();

        switch(fileName) {
            case "/messages":
                switch (method) {
                    case "GET":
                        if (tokens.nextToken().equals("messageId"))
                            getMessageById(tokens.nextToken());
                        else
                            getMostRecentMessages();
                        break;
                    case "POST":
                        addNewMessage(requestLine);
                        break;
                    default:
                        handleBadRequest();
                }
                break;
            case "/connection":
                switch (method) {
                    case "GET":
                        getUsersConnected();
                        break;
                    case "POST":
                        if (!tokens.nextToken().equals("username"))
                            handleBadRequest();
                        else
                            addNewConnection(tokens.nextToken());
                        break;
                    default:
                        handleBadRequest();
                }
                break;
            default:
                handleBadRequest();
        }
    }

    private void handleBadRequest() {
        String statusLine = "HTTP/1.0 400 Bad Request" + CRLF;
        String contentTypeLine = "Content-type: text/plain" + CRLF;
        this.os.writeBytes(statusLine);
        this.os.writeBytes(contentTypeLine);
        this.os.writeBytes(CRLF);
    }
}