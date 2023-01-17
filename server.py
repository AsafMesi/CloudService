from socket import *
import os
import sys
import files_utils as fu
from utils import get_random_id, get_comp_num, update_computers
import connection_utils as cu

# Globals: -----------------------------------------------------------------------------------------------

CHUNKSIZE = 10_000_000
server_has_changed = True  # global var that check if the server has been changed from last push request.
port = int(sys.argv[1])

# Dictionaries:
clients_id_path = {}  # create dictionary that maps id to path in the server.

# create dictionary that maps id to another dictionary of computer number for clients,
# and it's updated from others computer with the id:
data_base = {}

# Open server:
main_socket = socket()
main_socket.bind(('', port))
main_socket.listen(200)

# Send and receive files: --------------------------------------------------------------------------------------


# This function get from a new client without id the dirs and files in client path
def get_files(get_files_sock, c_id):
    line = " "
    while True:
        if not line:
            break  # no more files, client closed connection.
        line = get_files_sock.readline()

        if line.strip().decode() == "empty dirs:":
            while True:
                line = get_files_sock.readline()
                if not line:
                    break
                dir_name = line.strip().decode()
                dir_name = fu.get_path(client_op, dir_name)
                dir_path = os.path.join('AllClients', str(c_id))
                dir_path = os.path.join(dir_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)
        else:
            filename = line.strip().decode()
            filename = fu.get_path(client_op, filename)
            length = int(get_files_sock.readline())

            file_path = os.path.join('AllClients', str(c_id))
            file_path = os.path.join(file_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Read the data in chunks, so it can handle large files.
            with open(file_path, 'wb') as f:
                while length:
                    chunk = min(length, CHUNKSIZE)
                    data = get_files_sock.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    length -= len(data)
                else:  # only runs if while doesn't break and length==0
                    continue
    get_files_sock.close()


# This function send to new client with id the dirs and files in client path (including empty files)
def send_files(on_sock, src_path):
    with on_sock:
        for root, dirs, files in os.walk(src_path):
            for file in files:
                filename = os.path.join(root, file)
                relpath = os.path.relpath(filename, src_path)  # get file name from my_dir (file path)
                file_size = os.path.getsize(filename)

                with open(filename, 'rb') as f:
                    on_sock.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
                    on_sock.sendall(str(file_size).encode() + b'\n')  # send file size.

                    # Send the file in chunks so large files can be handled.
                    while True:
                        data = f.read(CHUNKSIZE)
                        if not data:
                            break
                        on_sock.sendall(data)

        # sending empty directories:
        on_sock.sendall("empty dirs:".encode('utf-8') + b'\n')
        for root, dirs, files in os.walk(src_path):
            for directory in dirs:
                d = os.path.join(root, directory)
                if not os.listdir(d):
                    d = os.path.relpath(d, src_path)
                    on_sock.sendall(d.encode() + b'\n')
        on_sock.sendall('Done.'.encode() + b'\n')


# Push requests - updates from client: ------------------------------------------------------------------------------

# the server gets an update from a client by "push" command. The server performs the operation by the command it gets.
def get_update(c_command, data_sock, c_id):
    global server_has_changed

    if c_command[0] == "created":
        is_dir, src_path = c_command[1], c_command[2]
        src_path = os.path.join(clients_id_path[c_id], src_path)
        src_path = fu.get_path(client_op, src_path)
        if os.path.exists(src_path):  # check if the "create" operation is already made- to avoid duplications.
            server_has_changed = False
            return

        server_has_changed = True
        if is_dir == "True":
            os.makedirs(src_path)  # create the dir
        elif is_dir == "False":
            cu.get_file(data_sock, src_path)  # get the file we need to create from the client

    elif c_command[0] == "deleted":
        is_dir, del_path = c_command[1], c_command[2]
        del_path = os.path.join(clients_id_path[c_id], del_path)
        if not os.path.exists(del_path):  # check if the "delete" operation is already made- to avoid duplications.
            server_has_changed = False
            return

        server_has_changed = True
        if is_dir == "True":
            fu.delete_dir(del_path)  # delete dir and all it's recursive dirs too
        else:
            if os.path.exists(del_path):
                os.remove(del_path)

    elif c_command[0] == "moved":
        is_dir, src_path, dest_path = c_command[1], c_command[2], c_command[3]
        src_path = fu.get_path(client_op, src_path)
        dest_path = fu.get_path(client_op, dest_path)

        src_path = os.path.join(clients_id_path[c_id], src_path)
        dest_path = os.path.join(clients_id_path[c_id], dest_path)
        # check if the "moved" operation is already made- to avoid duplications:
        if not os.path.exists(src_path) and os.path.exists(dest_path):
            server_has_changed = False
            return

        server_has_changed = True
        if is_dir == "False":
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)  # create the path we need to create the file
            os.replace(src_path, dest_path)
        else:  # delete from source path and create the dir in destination path
            fu.delete_dir(src_path)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)


# Pull requests - sent updates to Client: ----------------------------------------------------------------------

# send the current update by methods.
def send_update(cmd, c_path, on_sock):
    cmd_type = cmd.split(',', 1)[0]
    if cmd_type == "created":
        notify_created(cmd, c_path, on_sock)
    elif cmd_type == "deleted":
        notify_deleted(cmd, on_sock)
    elif cmd_type == "moved":
        notify_moved(cmd, on_sock)


def notify_created(curr_update, c_path, on_sock):
    mode, is_dir, new_path = curr_update.split(',')
    with on_sock:
        on_sock.sendall(curr_update.encode() + b'\n')
        if is_dir == "False":
            new_path = os.path.join(c_path, new_path)
            cu.send_file(on_sock, new_path)


def notify_deleted(curr_update, on_sock):
    with on_sock:
        on_sock.sendall(curr_update.encode() + b'\n')


def notify_moved(curr_update, on_sock):
    with on_sock:
        on_sock.sendall(curr_update.encode() + b'\n')


# -------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":

    # Makes folder to store all clients data
    server_dir = os.getcwd()
    allClients = os.path.join(server_dir, 'AllClients')
    os.mkdir(allClients)

    while True:
        # Waiting for client:
        print("\nWaiting for client... \n")
        client_socket, address = main_socket.accept()
        print(f"Accepted client - {address}\n")
        get_data_sock = client_socket.makefile(mode='rb')  # client joined - reading client socket by bytes.

        # identification - get client's ID, computer number, operation system.
        client_id = get_data_sock.readline().strip().decode()  # get from client his ID
        client_comp = get_data_sock.readline().strip().decode()  # get from client his computer number
        client_op = get_data_sock.readline().strip().decode()  # get from client his op = operating system

        client_dir_path = ''

        # Connection between Client and Server for the first time:-----------------------------------------------
        if client_id == 'None':  # if client assign without ID
            client_id = get_random_id(clients_id_path.keys())  # create client id
            client_comp = get_comp_num(data_base, client_id)  # give the client comp_num = '1', also update the database
            client_socket.sendall(client_id.encode() + b'\n')  # send new ID
            print(client_id)
            client_socket.sendall(client_comp.encode() + b'\n')  # send new Computer number (will be 1).
            client_socket.sendall(sys.platform.encode() + b'\n')  # send server op.

            # create & enter his folder name to the dictionary by ID
            os.mkdir(os.path.join(allClients, client_id))
            clients_id_path[client_id] = os.path.join(allClients, client_id)

            # Init: get files to server:
            get_files(get_data_sock, client_id)

        else:  # ID exists:
            client_dir_path = clients_id_path[client_id]  # search for path in AllClients folders
            if client_comp == "-1":  # default for new computer
                client_comp = get_comp_num(data_base, client_id)  # also update the database
                client_socket.sendall(client_comp.encode() + b'\n')  # send new Computer number
                client_socket.sendall(sys.platform.encode() + b'\n')  # send server op name.
                send_files(client_socket, client_dir_path)

            # Connection reconnect between Client and Server for pull or push:------------------------------------
            else:
                # Get connection type - Push or Pull:
                connection_type = get_data_sock.readline().strip().decode()

                if connection_type == "pull":  # client asks for updates
                    # Check if there are updates:
                    if data_base[client_id][client_comp]:  # check if there are updates
                        # get num of updates for current computer:
                        status = str(len(data_base[client_id][client_comp])) + " To go!"
                        client_socket.sendall(status.encode() + b'\n')
                        update = data_base[client_id][client_comp].pop(0)  # get update from data_base dictionary
                        send_update(update, client_dir_path, client_socket)

                    else:  # there are no updates for this computer
                        client_socket.sendall("No updates".encode() + b'\n')

                elif connection_type == "push":  # client want to share update (from watchdog)
                    command_txt = get_data_sock.readline().strip().decode()  # get the update line
                    command = str(command_txt).split(',')
                    get_update(command, get_data_sock, client_id)  # deal with the updates

                    if server_has_changed:  # global var - checks if the update wasn't duplicate
                        command[2] = fu.get_path(client_op, command[2])
                        if command[0] == "moved":
                            command[3] = fu.get_path(client_op, command[3])
                        curr_command = ','.join(command)
                        update_computers(data_base, client_id, client_comp, curr_command)
