# Server Architecture

### Note that all JSON bodies will be sent as ONE LINE

## HTTP Endpoints
#### NOTE: I know real HTTP stuff uses JSON bodies for POST requests, but that's kind of annoying with the Project 1 framework so query params will be easier for me to process
#### Error responses will all be 400 Bad Request with message body (example: `{"message": "Group does not exist"}`)
- GET /connection?group={group}
  - Sent after the user joins a group including the automatic joining of group `0` from POST /connection
  - group param can be name or id
  - Returns 200 OK with the list of all users currently connected
- POST /connection?username={username}
  - This is the initial request the client will send when connecting to the server
  - If connection is successful, server sends 201 Created with no body
  - This will automatically join the user into group `0` (the public group) and send a notification to all users in that group **including the user that just joined**
- GET /messages?group={group}
  - Sent when a user joins a new group, including after POST /connection
  - group param can be name or id
  - Returns 200 OK with the 2 most recent messages
  - Example output body:
  
  ``` json
    {
      "messages": 
        [
          {
            "message-id": 1234,
            "sender": "Gavin",
            "timestamp": "2026-11-20T14:46:30Z",
            "subject": "Example"
          },
          {
            "message-id": 5678,
            "sender": "Nick",
            "timestamp": "2026-11-19T14:46:30Z",
            "subject": "Example 2"
          }
       ]
    }
  ```
- GET /messages?group={group}&messageId={messageId}
  - Sent when the user requests a specific message body
  - group param can be name or id
  - Returns 200 OK with the requested message body
- POST /messages?group={group}&subject={subject}&body={body}
  - Honestly this one's kinda fucked, sending the body in the URI but it'll get the job done LMAO
  - group param can be name or id
  - subject and body MUST be wrapped in ""
  - Because of that, if the subject or body contain double quotes or backslashes, they need to be escaped (e.g. subject="he said \"wow\"")
  - Sent when user posts a new message to the board
  - Returns 201 Created with the message's ID
  - Note that this endpoint will send the created message to all connections in the group, **including the one that made the post**
- GET /groups
  - No parameters
  - Sent when the user requests the list of groups available to join
  - Returns 200 OK with a list of groups
  - Groups that the user is currently in will NOT be included in the returned list
  - Example output body:

  ``` json
    {
      "groups": [
        {
          "group-id": 0,
          "name": "Public"
        },
        blah blah blah,
        {
          "group-id": 5,
          "name": "Group 5"
        }
      ]
    }
- POST /groups?group={group}
  - Sent when the user joins a group by id
  - group param can be name or id
  - Returns 201 Created
  - Note that this will send a notification to all users in the joined group that a new user has joined **including the user that just joined**
- DELETE /groups?group={group}
  - Sent when a user leaves a group
  - group param can be name or id
  - Returns 204 No Content
  - Note that this will send a notification to all users in the left group that a user left

## Server Initiated Communication
#### These messages will all be sent from the server when initiated by one of the above endpoints
- Format: json
- The json file will contain two fields:
  - `type`: `new-message`, `user-connect`, `user-disconnect`
  - `body`: format depends on the type:
    - `new-message`: object with fields `group-id`, `message-id`, `sender`, `timestamp`, `subject`
    - `user-connect`: object with fields `group-id`, `username`
    - `user-disconnect`: object with fields `group-id`, `username`
- Server will NOT expect a response of any kind. TCP should handle guaranteed delivery here, so shouldn't need ACKs for these
- Notifications will end with CRLF