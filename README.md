# CloudService
Cloud service - monitor and update a chosen folder.

While the cloud server is on, a client can connect to the server and backup his chosen folder.
In addition, the server monitors the changes in the folder on the client's computer and changes the directory on the cloud according to those changes.

The communication is based on TCP.

# Instructions
* On one computer, open the server, on the other one, open the client.
* The only argument for the server is the port number.
* The arguments for the client are:
      1. Ip of the server
      2. port of the server
      3. path to the directory
      4. time (in seconds) to sync with the server.

### Notice:
During the first connection, the server creates a unique id for the client and both the client and the server print it onto the screen.\
While the client program is on, the client uses this id.\
If the client wants to get his folder to another computer, he can run the program so that the 5'th argument is the id.\
The server will know how to manage between those computers and keep them updated according to the latest updates.
