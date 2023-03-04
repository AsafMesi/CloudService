import socket
import sys
import os
from connection_logger import ConnectionLogger
from client_manager import ClientManager, ClientData
from file_syncer import get_files, send_files, get_update, send_file
from utils import get_path


if len(sys.argv) != 2:
    raise ValueError("Please Enter port number parameter.")

port = int(sys.argv[1])

log = ConnectionLogger()

# Open server:
server_socket = socket.socket()
server_socket.bind(('', port))
server_socket.listen(200)


def get_identifications(client_sock, client_d):
    with client_sock.makefile(mode='rb') as get_data_sock:
        client_d.u_id = get_data_sock.readline().strip().decode()      # get user's client's id.
        client_d.c_id = get_data_sock.readline().strip().decode()      # get client's id.
        client_d.os = get_data_sock.readline().strip().decode()        # get client's operating system.
        client_d.conn_type = get_data_sock.readline().strip().decode()    # get client's connection type.
    client_sock.sendall(b'1\n')


def push(client_sock, c_manager, client_d):
    user_dir = c_manager.get_user_dir(client_d.u_id)
    c_os = client_d.os
    with client_sock.makefile(mode='rb') as get_data_sock:
        csv_command = get_data_sock.readline().strip().decode()
        cmd_type, is_dir, path = csv_command.split(',', 2)
    server_has_changed = get_update(cmd_type, is_dir, path, client_sock, user_dir, c_os)
    client_sock.sendall(b'1\n')  # approve update

    if server_has_changed:
        if cmd_type == "moved":
            old_path, new_path = path.split(',')
            old_path = get_path(c_os, old_path)
            new_path = get_path(c_os, new_path)
            path = ",".join([old_path, new_path])
        else:
            path = get_path(c_os, path)
        csv_command = ','.join([cmd_type, is_dir, path])
        c_manager.update_clients(client_d, csv_command)
        return f"type: {cmd_type}, is_dir: {is_dir}, path: {path}"
    return None


def send_update(client_sock, command, user_dir):
    cmd_type = command.split(',', 1)[0]
    if cmd_type == "created":
        cmd_type, is_dir, path = command.split(',')
        client_sock.sendall(command.encode() + b'\n')
        if is_dir == "False":
            path = os.path.join(user_dir, path)
            send_file(client_sock, path, user_dir)
    else:
        client_sock.sendall(command.encode() + b'\n')


def pull(client_sock, c_manager, client_d):
    updates = c_manager.get_updates(client_d.u_id, client_d.c_id)
    user_dir = c_manager.get_user_dir(client_d.u_id)
    if updates:
        updates_count = str(len(updates))
        client_socket.sendall(updates_count.encode() + b'\n')
        update = updates.pop(0)
        send_update(client_sock, update, user_dir)
        with client_sock.makefile(mode='rb') as get_synced_sock:
            if not (int(get_synced_sock.readline()) == 1):
                print("Client did not got updated")
                return None
        return update
    client_socket.sendall(b'0\n')
    return None


if __name__ == "__main__":
    cm = ClientManager()
    client_data = ClientData()
    while True:
        client_socket, address = server_socket.accept()
        log.connection_accepted(address)

        get_identifications(client_socket, client_data)
        log.connection_established(client_data.u_id, client_data.c_id)

        if client_data.conn_type == "NewUser":
            client_data.u_id, client_data.c_id = cm.add_user()
            log.user_created(client_data.u_id)

            client_socket.sendall(client_data.u_id.encode() + b'\n')    # send new user ID
            client_socket.sendall(client_data.c_id.encode() + b'\n')    # send new client ID
            client_socket.sendall(sys.platform.encode() + b'\n')           # send server operating system.

            print(client_data.u_id)

            get_files(client_socket, cm.get_user_dir(client_data.u_id), client_data.os)
            log.push_requested("All files (Client -> Server)")

        elif client_data.conn_type == "NewClient":
            client_data.c_id = cm.add_client(client_data.u_id)
            log.client_created(client_data.u_id, client_data.c_id)

            client_socket.sendall(client_data.c_id.encode() + b'\n')     # send new client ID
            client_socket.sendall(sys.platform.encode() + b'\n')         # send server operating system.

            send_files(client_socket, cm.get_user_dir(client_data.u_id))
            log.pull_requested("All files (Server -> Client)")

        elif client_data.conn_type == "Push":
            cmd = push(client_socket, cm, client_data)
            if cmd:
                log.push_requested(cmd)

        elif client_data.conn_type == "Pull":
            cmd = pull(client_socket, cm, client_data)
            if cmd:
                log.pull_requested(cmd)

        else:
            log.connection_error("Unknown connection type!")

        client_socket.close()
        log.connection_ended()
        client_data.clear()
