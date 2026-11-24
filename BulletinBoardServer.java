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

final class Group {
    public List<OpenConnection> connections = new ArrayList<>();
    public List<Message> messages = new ArrayList<>();
}

final class OpenConnection implements Runnable {
    static final String CRLF = "\r\n";
    static final List<Group> groups = new ArrayList<>(
            Arrays.asList(new Group(), new Group(), new Group(), new Group(), new Group(), new Group()));
    static final List<String> usernames = new ArrayList<>();
    private final List<Group> joinedGroups = new ArrayList<>();
    private Socket socket;
    public String username;
    public DataOutputStream os;

    // Constructor
    public OpenConnection(Socket socket) throws Exception {
        this.socket = socket;
        this.os = new DataOutputStream(socket.getOutputStream());
    }

    // Implement the run() method of the Runnable interface.
    public void run() {
        try {
            processRequests();
        } catch (Exception e) {
            System.out.println(e);
        } finally {
            handleDisconnect();
        }
    }

    private void processRequests() throws Exception {
        InputStream is = socket.getInputStream();
        BufferedReader br = new  BufferedReader(new InputStreamReader(is));

        while (true) {
            String requestLine = br.readLine();
            if (requestLine == null)   // client disconnected
                break;

            // Ignore any extra headers
            String header = br.readLine();
            while (!(header == null || header.equals(""))) {
                header = br.readLine();
            }

            try {
                ParsedRequest request = new ParsedRequest(requestLine);
                handleRequest(request);
            } catch (BadRequestException e) {
                handleBadRequest(e);
            }
        }
        br.close();
    }

    private void handleRequest(ParsedRequest request) throws Exception {
        switch(request.path) {
            case "/messages":
                switch (request.method) {
                    case "GET":
                        String messageId = request.get("messageId");
                        if (messageId != null)
                            getMessageById(request.require("groupId"), messageId);
                        else
                            getMostRecentMessages(request.require("groupId"));
                        break;
                    case "POST":
                        addNewMessage(request.require("groupId"), request.require("subject"), request.require("body"));
                        break;
                    default:
                        throw new BadRequestException(request.method + " " +  request.path + " does not exist");
                }
                break;
            case "/connection":
                switch (request.method) {
                    case "GET":
                        getUsersConnected(request.require("groupId"));
                        break;
                    case "POST":
                        addNewConnection(request.require("username"));
                        break;
                    default:
                        throw new BadRequestException(request.method + " " +  request.path + " does not exist");
                }
                break;
            case "/groups":
                switch (request.method) {
                    case "GET":
                        getJoinableGroups();
                        break;
                    case "POST":
                        joinGroup(request.require("groupId"));
                        break;
                    case "DELETE":
                        leaveGroup(request.require("groupId"));
                        break;
                    default:
                        throw new BadRequestException(request.method + " " +  request.path + " does not exist");
                }
                break;
            default:
                throw new BadRequestException(request.method + " " +  request.path + " does not exist");
        }
    }

    private void getMessageById(String rawGroupId, String messageId) throws Exception {
        Group group = getGroup(rawGroupId);
        if (!joinedGroups.contains(group))
            throw new BadRequestException("Not in requested group");
        String body = "{\"message\": \"";
        List<Message> messages = group.messages;
        synchronized (messages) {
            for (Message message : messages) {
                if (message.messageId == messageId) {
                    body += escapeJson(message.body) + "\"}";
                    sendResponse("200 OK", "application/json", body);
                    return;
                }
            }
        }
        throw new BadRequestException("Message does not exist");
    }

    private void getMostRecentMessages(String rawGroupId) throws Exception {
        Group group = getGroup(rawGroupId);
        if (!joinedGroups.contains(group))
            throw new BadRequestException("Not in requested group");
        String body = "{\"messages\": [";
        List<Message> messages = group.messages;
        synchronized (messages) {
            int len = messages.size();
            for (int i = 1; i <= 2; i++) {
                if (len < i)
                    break;
                if (i == 2)
                    body += ",";
                Message m = messages.get(len - i);
                body += "{\"message-id\":" + m.messageId + ",";
                body += "\"sender\":\"" + escapeJson(m.sender) + "\",";
                body += "\"timestamp\":\"" + m.timestamp + "\",";
                body += "\"subject\":\"" + escapeJson(m.subject) + "\"}";
            }
        }
        body += "]}";

        sendResponse("200 OK", "application/json", body);
    }

    private void addNewMessage(String rawGroupId, String subject, String body) throws Exception{
        Group group = getGroup(rawGroupId);
        if (!joinedGroups.contains(group))
            throw new BadRequestException("Not in requested group");
        Message message = new Message();
        message.sender = this.username;
        message.body = body;
        message.subject = subject;
        message.timestamp = Instant.now();
        List<Message> messages = group.messages;
        synchronized (messages) {
            message.messageId = messages.size();
            messages.add(message);
        }
        sendResponse("201 Created", "text/plain", "");
        sendNewMessageNotif(message);
    }

    private void getUsersConnected(String rawGroupId) throws Exception {
        Group group = getGroup(rawGroupId);
        if (!joinedGroups.contains(group))
            throw new BadRequestException("Not in requested group");
        List<String> usernameList = new ArrayList<>();
        synchronized (group.connections) {
            for (OpenConnection connection : group.connections) {
                usernameList.add(escapeJson(connection.username));
            }
        }

        String body = "{ \"users\": [\"" + String.join("\", \"", usernameList) + "\"]}";
        sendResponse("200 OK", "application/json", body);
    }

    private void addNewConnection(String username) throws Exception{
        if (this.username != null)
            throw new BadRequestException("Already connected");
        if (username.length() == 0)
            throw new BadRequestException("Username must not be blank");
        synchronized (usernames) {
            if (usernames.contains(username))
                throw new BadRequestException("Username already taken");
            usernames.add(username);
        }
        this.username = username;
        Group publicGroup = groups.get(0);
        synchronized (publicGroup.connections) {
            publicGroup.connections.add(this);
        }
        joinedGroups.add(publicGroup);
        sendResponse("201 Created", "text/plain", "");
        sendUserConnectNotif(username, publicGroup);
    }

    private void getJoinableGroups() {
        List<Group> joinableGroups = new ArrayList<>(Arrays.listOf(0, 1, 2, 3, 4, 5));
        for (int i = 0; i < 6; i++) {
            Group group = groups.get(i);
            if (joinedGroups.contains(group))
                joinableGroups.remove(joinableGroups.indexOf(group));
        }
        String body = "\"groups\": [" + String.join(", ", joinableGroups) + "]}";
        sendResponse("200 OK", "application/json", body);
    }

    private void joinGroup(String rawGroupId) {
        // TODO
    }

    private void leaveGroup(String rawGroupId) {
        // TODO
    }

    private void handleBadRequest(Exception e) throws Exception {
        String body = "{\"message\": \"" + escapeJson(e.message) + "\"}";
        sendResponse("400 Bad Request", "application/json", body);
    }

    private void sendUserConnectNotif(String username, Group group) throws Exception {
        String notif =
            "{" +
                "\"type\": \"user-connect\", " +
                "\"body\": {" +
                    "\"group-id\": " + groups.indexOf(group) + ", " +
                    "\"username\": \"" + escapeJson(username) + "\"" +
                "}" +
            "}" + CRLF;
        notifyAllGroupMembers(group, notif);
    }

    private void sendNewMessageNotif(Group group, Message message) {
        String notif =
            "{" +
                "\"type\": \"new-message\", " +
                "\"body\": {" +
                    "\"group-id\": " + groups.indexOf(group) + ", " +
                    "\"message-id\": " + message.messageId + ", " +
                    "\"sender\": \"" + escapeJson(username) + "\", " +
                    "\"timestamp\": \"" + message.timestamp + "\", " +
                    "\"subject\": \"" + escapeJson(message.subject) + "\"" +
                "}" +
            "}" + CRLF;
        notifyAllGroupMembers(group, notif);
    }

    private void handleDisconnect() {
        // TODO
    }

    private void sendResponse(String status, String contentType, String body) throws Exception {
        // Convert once to UTF-8 bytes; the array length is the true Content-Length
        byte[] bodyBytes = body.getBytes(java.nio.charset.StandardCharsets.UTF_8);

        String headers = "HTTP/1.0 " + status + CRLF
                + "Content-Type: " + contentType + CRLF
                + "Content-Length: " + bodyBytes.length + CRLF
                + CRLF;
        synchronized (os) {
            os.write(headers.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            os.write(bodyBytes);
            os.flush();
        }
    }

    private static void notifyAllGroupMembers(Group group, String notif) {
        synchronized (group.connections) {
            for (OpenConnection connection : group.connections) {
                sendNotification(connection.os, notif);
            }
        }
    }

    private static void sendNotification(DataOutputStream os, String notif) {
        synchronized (os) {
            try {
                os.write(notif.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                os.flush();
            } catch (Exception e) {
                System.out.println(e);
            }
        }
    }

    private Group getGroup(String rawGroupId) throws BadRequestException {
        int id;
        try {
            id = Integer.valueOf(rawGroupId);
        } catch (Exception e) {
            throw new BadRequestException("Group id must be integer");
        }
        if (id < 0 || id > 5)
            throw new BadRequestException("Group does not exist");
        Group group = groups.get(id);
        return group;
    }

    private static String escapeJson(String input) {
        StringBuilder ret = new StringBuilder();
        for (char c : input.toCharArray()) {
            switch (c) {
                case '"':
                    ret.append("\\\"");
                    break;
                case '\\':
                    ret.append("\\\\");
                    break;
                case '\n':
                    ret.append("\\n");
                    break;
                case '\r':
                    ret.append("\\r");
                    break;
                case '\t':
                    ret.append("\\t");
                    break;
                default:
                    ret.append(c);
            }
        }
        return ret.toString();
    }
}

final class BadRequestException extends Exception {
    String message;

    BadRequestException(String message) {
        this.message = message;
    }
}

final class ParsedRequest {
    final String method;
    final String path;
    private final Map<String, String> params = new HashMap<>();

    ParsedRequest(String requestLine) throws BadRequestException {
        // Method is before the first space; the HTTP version is after the LAST
        // space. Quoted values may contain spaces, so we can't split on spaces.
        int firstSpace = requestLine.indexOf(' ');
        int lastSpace = requestLine.lastIndexOf(' ');
        if (firstSpace == -1 || lastSpace <= firstSpace
                || !requestLine.substring(lastSpace + 1).startsWith("HTTP/"))
            throw new BadRequestException("HTTP request must start with \"HTTP/\"");

        method = requestLine.substring(0, firstSpace);
        String uri = requestLine.substring(firstSpace + 1, lastSpace).trim();

        // The FIRST '?' separates path from query; later '?'s belong to values.
        int q = uri.indexOf('?');
        if (q == -1) {
            path = uri;
        } else {
            path = uri.substring(0, q);
            parseQuery(uri.substring(q + 1));
        }
    }

    // Returns the value, or null if the param wasn't sent.
    String get(String key) {
        return params.get(key);
    }

    // Returns the value, or throws if missing (use for required params).
    String require(String key) throws BadRequestException {
        String value = params.get(key);
        if (value == null)
            throw new BadRequestException("Missing required parameter: " + key);
        return value;
    }

    private void parseQuery(String query) throws BadRequestException {
        int i = 0;
        while (i < query.length()) {
            int eq = query.indexOf('=', i);
            if (eq == -1)
                throw new BadRequestException("Param missing value");
            String key = query.substring(i, eq);
            i = eq + 1;

            StringBuilder value = new StringBuilder();
            if (i < query.length() && query.charAt(i) == '"') {
                // Quoted value: read to the closing quote, so '&', '=' and
                // spaces inside are preserved. Backslash escapes the next char.
                i++;
                boolean closed = false;
                while (i < query.length()) {
                    char c = query.charAt(i++);
                    if (c == '\\' && i < query.length())
                        value.append(query.charAt(i++));
                    else if (c == '"') {
                        closed = true;
                        break;
                    } else
                        value.append(c);
                }
                if (!closed || (i < query.length() && query.charAt(i) != '&'))
                    throw new BadRequestException("TO CLAUDE: tell me what to put here");
            } else {
                // Unquoted value: read to the next '&'.
                while (i < query.length() && query.charAt(i) != '&')
                    value.append(query.charAt(i++));
            }
            i++; // skip the '&' separator
            params.put(key, value.toString());
        }
    }
}