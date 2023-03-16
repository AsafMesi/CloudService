import os
import sys
import socket
import time
import file_syncer
import client_observer

if not (5 <= len(sys.argv) <= 6):
    raise ValueError("Please Enter parameters in the form:"
                     " server_ip, server_port, dir_path, update_rate, client_id[optional]")

server_ip = sys.argv[1]
server_port = int(sys.argv[2])
root = sys.argv[3]
pulling_rate = int(sys.argv[4])

user_id = 'None'
client_id = 'None'

if len(sys.argv) == 6:
    user_id = sys.argv[5]

pause_observer = None
resume_observer = None


# connect to server and identity.
def get_server_socket(conn_type):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((server_ip, server_port))
    server_sock.sendall(user_id.encode() + b'\n')  # send user id
    server_sock.sendall(client_id.encode() + b'\n')  # send user's client id
    server_sock.sendall(sys.platform.encode() + b'\n')  # send client's operating system.
    server_sock.sendall(conn_type.encode() + b'\n')  # send client connection type.
    return server_sock


def notify_server(event):
    if event.event_type == "modified":
        if not event.is_directory:
            notify_file_modified(event)
        # else: directory renaming cause move and modified event, so we will ignore the modified event for directories.
        return
    pull()
    match event.event_type:
        case "created":
            notify_created(event)
        case "deleted":
            notify_deleted(event)
        case "moved":
            notify_moved(event)
        case _:
            print("unknown event")


def notify_created(event):
    if os.path.splitext(event.src_path)[1] == ".swp":
        return
    relpath = os.path.relpath(event.src_path, root)
    csv_cmd = f"{event.event_type},{str(event.is_directory)},{relpath}"
    server_sock = get_server_socket("Push")
    server_sock.sendall(csv_cmd.encode() + b'\n')
    if not event.is_directory:
        file_syncer.send_file(server_sock, root, event.src_path)
    server_sock.close()


def notify_deleted(event):
    if os.path.splitext(event.src_path)[1] == ".swp":
        dir_name = os.path.dirname(event.src_path)
        file_name = os.path.basename(event.src_path)[1:-4]  # slice the first "." and the last ".swp"
        src_path = os.path.join(dir_name, file_name)
        event.src_path = src_path
        notify_file_modified(event)
    else:
        relpath = os.path.relpath(event.src_path, root)
        csv_cmd = f"{event.event_type},{str(event.is_directory)},{relpath}"
        server_sock = get_server_socket("Push")
        server_sock.sendall(csv_cmd.encode() + b'\n')
        server_sock.close()


def notify_moved(event):
    old_relpath = os.path.relpath(event.src_path, root)
    new_relpath = os.path.relpath(event.dest_path, root)
    csv_cmd = f"{event.event_type},{str(event.is_directory)},{old_relpath},{new_relpath}"
    server_sock = get_server_socket("Push")
    server_sock.sendall(csv_cmd.encode() + b'\n')
    server_sock.close()


def notify_file_modified(event):
    notify_server(client_observer.FileEvent("deleted", False, event.src_path))
    notify_server(client_observer.FileEvent("created",  False, event.src_path))


def pull():
    pulling = True
    while pulling:
        server_sock = get_server_socket("Pull")
        read_socket = server_sock.makefile(mode='rb')
        updates_count = int(read_socket.readline().strip().decode())
        if updates_count > 0:
            server_os = read_socket.readline().strip().decode()
            pause_observer()
            _ = file_syncer.get_update(read_socket, root, server_os)  # _ = applied_cmd
            resume_observer()
        else:
            pulling = False

        # non-persistent - reconnects for every update.
        read_socket.close()
        server_sock.close()


def init_new_user():
    global user_id, client_id
    server_socket = get_server_socket("NewUser")
    get_data_sock = server_socket.makefile(mode='rb')
    user_id = get_data_sock.readline().strip().decode()
    client_id = get_data_sock.readline().strip().decode()
    get_data_sock.close()
    file_syncer.send_files(server_socket, root)  # persistent - send all files on the same connection.


def init_new_client():
    global root, client_id
    if os.listdir(root):
        raise ValueError(f"Please clear '{root}' directory before getting the content from the server.\n")
    server_socket = get_server_socket("NewClient")
    get_data_sock = server_socket.makefile(mode='rb')
    client_id = get_data_sock.readline().strip().decode()
    file_syncer.get_files(get_data_sock, root)  # persistent - get all files on the same connection.
    get_data_sock.close()
    server_socket.close()


# -------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    if user_id == "None":
        init_new_user()
    else:
        init_new_client()

    observer = client_observer.ClientFileObserver(root, on_any_event=notify_server)

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
