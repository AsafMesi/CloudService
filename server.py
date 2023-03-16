import os
import socket
import sys
import file_syncer
import client_manager
from connection_logger import ConnectionLogger

if not (len(sys.argv) == 2):
    raise ValueError("Please Enter port parameter: [1024 < port < 49152].")

port = int(sys.argv[1])

if not (1024 < port < 49152):
    raise ValueError("Port number should be between: 1025 and 49151.")

root = os.getcwd()  # can be changed to a specific location.

# logged user identifications:  (Can be changed to a dictionary in case of multiple connections).
user_id = None
client_id = None
client_os = None
client_conn_type = None

# Open server:
server_socket = socket.socket()
server_socket.bind(('', port))
server_socket.listen(200)


def clear_logged_client():
    global user_id, client_id, client_os, client_conn_type
    user_id = None
    client_id = None
    client_os = None
    client_conn_type = None


def get_identifications(read_sock):
    global user_id, client_id, client_os, client_conn_type
    user_id = read_sock.readline().strip().decode()      # get user's client's id.
    client_id = read_sock.readline().strip().decode()      # get client's id.
    client_os = read_sock.readline().strip().decode()        # get client's operating system.
    client_conn_type = read_sock.readline().strip().decode()    # get client's connection type.


# -------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    log = ConnectionLogger("ConnectionLog.txt", "CloudService Server connection log")
    cu = client_manager.ClientManager(root)
    while True:
        # Waiting for client:
        client_socket, address = server_socket.accept()
        log.connection_accepted(address)
        get_data_sock = client_socket.makefile(mode='rb')
        get_identifications(get_data_sock)
        match client_conn_type:

            case "NewUser":
                user_id, client_id = cu.add_user()
                sys.stdout.write(user_id)
                sys.stdout.flush()
                client_socket.sendall(user_id.encode() + b'\n')
                client_socket.sendall(client_id.encode() + b'\n')
                user_root = cu.get_user_root(user_id)
                file_syncer.get_files(get_data_sock, user_root)
                get_data_sock.close()
                client_socket.close()
                log.user_created(user_id)

            case "NewClient":
                get_data_sock.close()
                client_id = cu.add_client(user_id)
                client_socket.sendall(client_id.encode() + b'\n')
                user_root = cu.get_user_root(user_id)
                file_syncer.send_files(client_socket, user_root)
                log.client_created(user_id, client_id)

            case "Push":
                user_root = cu.get_user_root(user_id)
                cmd = file_syncer.get_update(get_data_sock, user_root, client_os)
                get_data_sock.close()
                if cmd:
                    cu.update_clients(user_id, client_id, cmd)
                    log.push_requested(user_id, client_id, cmd)

            case "Pull":
                get_data_sock.close()
                updates = cu.get_updates(user_id, client_id)
                client_socket.sendall((str(len(updates))).encode() + b'\n')
                if updates:
                    client_socket.sendall(sys.platform.encode() + b'\n')
                    user_root = cu.get_user_root(user_id)
                    update = updates.pop(0)
                    file_syncer.send_update(client_socket, user_root, update)
                    log.pull_requested(user_id, client_id, update)
                else:
                    client_socket.close()

            case _:
                err = "Unknown client connection type"
                log.connection_error(err)
                raise ValueError(err)

        clear_logged_client()
        log.connection_ended()
