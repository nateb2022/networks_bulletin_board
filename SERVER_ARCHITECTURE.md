# Server Architecture

## HTTP Endpoints
- GET /connection
  - Honestly I'm not 100% sure when this one will be called, I'll leave that up to your discretion, Nate
  - No parameters
  - Returns 200 OK with the list of all users currently connected
- POST /connection
  - JSON message body has field `username`
  - Sent when the client connects to the bulletin board
  - If connection is successful, server sends 201 Created with no body
  - Note that this endpoint will send a notification to all open connections that the new user has joined
- DELETE /connection
  - No parameters
  - Sent when the client disconnects from the bulletin board
  - If disconnection is successful, server sends 204 No Content
  - Note that this endpoint will send a notification to all open connections that the user has disconnected
- GET /messages
  - No parameters
  - Sent after 200 response from POST /connection, requests 2 most recent messages
  - Returns 200 OK with the 2 most recent messages
- GET /messages?messageId={messageId}
  - Sent when the user requests a specific message body
  - Returns 200 OK with the requested message body
  - If the id doesn't exist, returns a 404 Not Found
- POST /messages
  - Body is JSON object with fields `sender`, `subject`, and `body`
  - Sent when user posts a new message to the board
  - Returns 201 Created with the message's ID
  - Note that this endpoint will send the created message to all currently open connections, **including the one that made the post**

## Server Initiated Communication
#### These messages will all be sent from the server when initiated by one of the above endpoints
- Format: json
- The json file will contain two fields:
  - `type`: `new-message`, `user-connect`, `user-disconnect`
  - `body`: format depends on the type:
    - `new-message`: object with fields `message-id`, `sender`, `timestamp`, `subject`
    - `user-connect`: str containing the username
    - `user-disconnect`: str containing the username
- Server will expect a response of some kind
- Two response types: 
  - good (matches above format, everything's all good)
  - bad (format's wrong, either in type or expected body for type, data corrupted in some way)
- NATE, PLEASE ADD IN THE SPECIFIC FORMAT OF THE RESPONSE. I'll leave it up to you what the easiest way to go about it is on your end, just please put the format here