import os
import socket
import sys
import file_syncer
import client_manager

port = int(sys.argv[1])
root = os.getcwd()

# logged user details:
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
    cu = client_manager.ClientManager(root)
    while True:
        # Waiting for client:
        client_socket, address = server_socket.accept()
        get_data_sock = client_socket.makefile(mode='rb')
        get_identifications(get_data_sock)
        match client_conn_type:

            case "NewUser":
                user_id, client_id = cu.add_user()
                print(user_id)
                sys.stdout.write(user_id)
                client_socket.sendall(user_id.encode() + b'\n')
                client_socket.sendall(client_id.encode() + b'\n')
                user_root = cu.get_user_root(user_id)
                file_syncer.get_files(get_data_sock, user_root)
                get_data_sock.close()
                client_socket.close()

            case "NewClient":
                get_data_sock.close()
                client_id = cu.add_client(user_id)
                client_socket.sendall(client_id.encode() + b'\n')
                user_root = cu.get_user_root(user_id)
                file_syncer.send_files(client_socket, user_root)

            case "Push":
                user_root = cu.get_user_root(user_id)
                cmd = file_syncer.get_update(get_data_sock, user_root, client_os)
                get_data_sock.close()
                if cmd:
                    cu.update_clients(user_id, client_id, cmd)

            case "Pull":
                get_data_sock.close()
                updates = cu.get_updates(user_id, client_id)
                client_socket.sendall((str(len(updates))).encode() + b'\n')
                if updates:
                    client_socket.sendall(sys.platform.encode() + b'\n')
                    user_root = cu.get_user_root(user_id)
                    update = updates.pop(0)
                    file_syncer.send_update(client_socket, user_root, update)
                else:
                    client_socket.close()

            case _:
                raise ValueError("Unknown client connection type")
        clear_logged_client()
