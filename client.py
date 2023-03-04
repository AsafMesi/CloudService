import socket
import os
import sys
import time
from client_file_observer import ClientFileObserver
from file_syncer import FileSyncer, get_files, send_files, send_identifications, get_update

pause_observer = None
resume_observer = None

if not (5 <= len(sys.argv) <= 6):
    raise ValueError("Please Enter parameters in the form:"
                     " server_ip, server_port, dir_path, update_rate, client_id[optional]")

server_ip = sys.argv[1]
server_port = int(sys.argv[2])
dir_path = sys.argv[3]
pulling_rate = int(sys.argv[4])
user_id = 'None'
client_id = 'None'
status = "NewUser"
server_os = os.name

if not os.path.exists(dir_path):
    raise ValueError(f"Directory '{dir_path}' does not exist\nPlease create it and re-run.")

# When running the client with (user_id != None) the server will first send the content of the user's directory.
# todo: Answer the q of real life syncing. (create new folder called mybackup or somthing like that), moving this dir?
if len(sys.argv) == 6:
    user_id = sys.argv[5]
    status = "NewClient"
    if os.listdir(dir_path):
        raise ValueError(f"Please clear '{dir_path}' directory before getting the content from the server.\n")


def init_new_user(server_sock):
    global user_id, client_id, dir_path, server_os
    with server_sock.makefile(mode='rb') as get_data_sock:
        user_id = get_data_sock.readline().strip().decode()  # get new user id
        client_id = get_data_sock.readline().strip().decode()  # get new client id
        server_os = get_data_sock.readline().strip().decode()  # get server op name.
    send_files(server_sock, dir_path)  # upload all `dir_path` content to the server.


def init_new_client(server_sock):
    global client_id, dir_path, server_os
    with server_sock.makefile(mode='rb') as get_data_sock:
        client_id = get_data_sock.readline().strip().decode()  # get new client id
        server_os = get_data_sock.readline().strip().decode()  # get server op name.
    get_files(server_sock, dir_path, server_os)  # upload all my content from the server to `dir_path`.


def init_connection(server_sock, c_type):
    if c_type == 'NewUser':
        init_new_user(server_sock)
    elif c_type == 'NewClient':
        init_new_client(server_sock)
    else:
        server_sock.close()
        raise ValueError(f"Unknown connection type for initialization! got {c_type}.\n")


def pull():
    pulling = True
    while pulling:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.connect((server_ip, server_port))
        send_identifications(server_sock, user_id, client_id, "Pull")
        with server_sock.makefile(mode='rb') as get_update_sock:
            updates_count = int(get_update_sock.readline().strip().decode())
            if updates_count > 0:
                csv_command = get_update_sock.readline().strip().decode()
                cmd_type, is_dir, path = csv_command.split(',', 2)
                pause_observer()
                get_update(cmd_type, is_dir, path, server_sock, dir_path, server_os)
                resume_observer()
                server_sock.sendall(b'1\n')  # approve update
            else:
                pulling = False
        server_sock.close()


def get_push_socket():
    pull()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((server_ip, server_port))
    send_identifications(server_sock, user_id, client_id, "Push")
    return server_sock


# todo: answer the q of what to do in case the id is not valid.
if __name__ == "__main__":
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((server_ip, server_port))  # connect
    send_identifications(server_socket, user_id, client_id, status)  # identify
    init_connection(server_socket, status)  # get or send data.
    server_socket.close()

    # from now on the client app is running, but the client will connect to the server only to send/receive data.
    # -----------------------------------------------------------------------------------------------------------
    status = "Push"
    syncer = FileSyncer(dir_path, get_push_socket)
    observer = ClientFileObserver(dir_path, syncer)

    # While pulling updates, we would like to pause the observer.
    pause_observer = observer.un_schedule
    resume_observer = observer.schedule

    # Start Observing:
    observer.schedule()
    observer.start()
    try:
        while True:
            time.sleep(pulling_rate)
            pull()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
