# CloudService
A Python application for monitoring and updating a selected folder.  
The communication is based on TCP.

## Description
This code consists of two main files: `server.py` and `client.py`. Before running the code, ensure that you have installed the necessary libraries.

The server file creates a folder called "AllClients" and waits for clients to connect. The client file connects to the server and sends one of four types of request:

1. "New User" - The server creates a unique user ID and a folder with this ID as the name in the "AllClients" folder. Then, the server retrieves all the data from the client's directory.
2. "New Client" - The client connects with an ID and the server sends all the data it has from the folder it created for the user.
3. "Push" - The client sends an update to the server. The server updates the user's folder accordingly and saves this update for other clients of the same user.
4. "Pull" - The client requests an update from the server.

It is important to note that every user can have multiple clients. The client script monitors a specified folder and sends a "push" request to the server every time a change occurs. This ensures that the server can keep all clients of a user up-to-date with the latest changes made by any of them.

## Instructions
To use the code, follow these instructions:

1. Install any libraries required by the code.
2. Run the server with the command `python server.py [PORT_NUMBER]`, where `[PORT_NUMBER]` is the port on which you want the server to listen.
3. Run the client with the command `python client.py [SERVER_IP] [SERVER_PORT] [FOLDER_PATH] [PULLING_RATE] [USER_ID]`, where:
   * `[SERVER_IP]` is the IP address of the server (you can find this using `ipconfig` on Windows or `ifconfig` on Linux).
   * `[SERVER_PORT]` is the port on which the server is listening.
   * `[FOLDER_PATH]` is the path to the folder you want to monitor and back up.
   * `[PULLING_RATE]` is the rate (in seconds) at which you want the client to request updates from the server.
   * `[USER_ID]` is an optional argument for existing users.

### Notice
When a new user connects to the server for the first time, the server generates a unique ID and prints it to the console. After this, the client program will use this ID automatically. If you want to connect from another device to access your backed-up folder, use this ID when running the client. The server will know how to manage updates between devices and keep them all up-to-date.

## Logging

All the connections to the server are being logged in a file called `connectionLog.txt`. The log includes the following information:

- IP address and port of the client when connecting to the server
- User ID and client ID associated with the connection
- Type of request made (New User, New Client, Push, Pull)
- Timestamp of the request
- Whether the connection was successful or not
- Any errors that occurred during the connection


You may want to review the 'connectionLog.txt' file for more information on the connection status.


#### Here is a basic illustraion of how the project structre looks like:
<img src="https://github.com/user-attachments/assets/eb6f5fd0-c0da-4271-8358-c6b26512b10d" alt="image" style="width:40%; height:auto;">

## Authors
Asaf Mesialty & Shir Fintsy
