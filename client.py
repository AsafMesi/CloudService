import socket
import os
import sys
import time
from watchdog.observers import polling
from watchdog.events import PatternMatchingEventHandler

# Globals: -----------------------------------------------------------------------------------------------

CHUNKSIZE = 1_000_000

server_ip = sys.argv[1]
server_port = int(sys.argv[2])
path = sys.argv[3]
time_cycle = int(sys.argv[4])
client_id = ''
server_op = 'linux'  # The server will override this value.
client_comp = "-1"

# If the client has no id - then he will send 'False' to the server - which means he is a new client.
if len(sys.argv) < 6:
    client_id = 'None'
else:
    client_id = sys.argv[5]


# Utils Functions: --------------------------------------------------------------------------------------------

# This function set the path sep to '\\' in case of windows path and '/' otherwise.
# Because most of the operation systems works with linux sep - we set the src sep to '/' by default.
def get_path(src_platform, src_path, src_sep='/'):
    if src_platform == 'win32':
        src_sep = '\\'
    if os.sep != src_sep:
        src_path = src_path.replace(src_sep, os.sep)
    return src_path


# We use the socket to make push/pull request. we always Identify: --------------------------------------------

# connect to server and identity.
def get_server_socket():
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket.connect((server_ip, server_port))
    new_socket.sendall(client_id.encode() + b'\n')  # send client id
    new_socket.sendall(client_comp.encode() + b'\n')  # send client comp
    new_socket.sendall(sys.platform.encode() + b'\n')  # send client's op.
    return new_socket


# connect to server with push request
def get_push_socket():
    push_sock = get_server_socket()
    push_sock.sendall("push".encode() + b'\n')
    return push_sock


# connect to server with pull request
def get_pull_socket():
    pull_sock = get_server_socket()
    pull_sock.sendall("pull".encode() + b'\n')
    return pull_sock


# Send and receive files: --------------------------------------------------------------------------------------

# send files and empty directories.
def send_files(on_sock, src_path):
    with on_sock:
        for root, dirs, files in os.walk(src_path):
            for file in files:
                filename = os.path.join(root, file)
                relpath = os.path.relpath(filename, src_path)  # get file name from my_dir (file path)
                filesize = os.path.getsize(filename)

                print(f'Sending {relpath}')

                with open(filename, 'rb') as f:
                    on_sock.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
                    on_sock.sendall(str(filesize).encode() + b'\n')  # send file size.

                    # Send the file in chunks so large files can be handled.
                    while True:
                        data = f.read(CHUNKSIZE)
                        if not data:
                            break
                        on_sock.sendall(data)

        # sending empty directories.
        on_sock.sendall("empty dirs:".encode('utf-8') + b'\n')
        for root, dirs, files in os.walk(src_path):
            for directory in dirs:
                d = os.path.join(root, directory)
                if not os.listdir(d):
                    d = os.path.relpath(d, src_path)
                    print(d)
                    on_sock.sendall(d.encode() + b'\n')
        print('Done.')


def get_files(get_files_sock):
    line = " "
    while True:
        if not line:
            break  # no more files, client closed connection.
        line = get_files_sock.readline()

        if line.strip().decode() == "empty dirs:":
            while True:
                line = get_files_sock.readline()
                if line.strip().decode() == 'Done.':
                    line = ''
                    break
                dir_name = line.strip().decode()
                dir_name = get_path(server_op, dir_name)
                print(f'empty dir {dir_name} ... \n', end='', flush=True)
                dir_path = os.path.join(path, dir_name)
                os.mkdir(dir_path)
        else:
            filename = line.strip().decode()
            filename = get_path(server_op, filename)
            length = int(get_files_sock.readline())
            print(f'Downloading {filename}...\n  Expecting {length:,} bytes...', end='', flush=True)

            file_path = os.path.join(path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Read the data in chunks so it can handle large files.
            with open(file_path, 'wb') as f:
                while length:
                    chunk = min(length, CHUNKSIZE)
                    data = get_files_sock.read(chunk)
                    if not data:
                        break
                    f.write(data)
                    length -= len(data)
                else:  # only runs if while doesn't break and length==0
                    print('Complete')
                    continue

            # socket was closed early.
            print('Incomplete')
            break
    get_files_sock.close()


def send_file(on_sock, src_path):
    with on_sock:
        filename = src_path
        relpath = os.path.basename(filename)  # get file name from my_dir (file path)
        filesize = os.path.getsize(filename)

        print(f'Sending {relpath}')

        with open(filename, 'rb') as f:
            on_sock.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
            on_sock.sendall(str(filesize).encode() + b'\n')  # send file size.

            # Send the file in chunks so large files can be handled.
            while True:
                data = f.read(CHUNKSIZE)
                if not data:
                    break
                on_sock.sendall(data)

# Observer - check for changes:

def on_any_event(event):
    src_path = os.path.relpath(event.src_path, path)  # get relative path
    notify_server(event, event.event_type, src_path)


# After getting an alert about change - notify server
def notify_server(event, event_type, src_path):

    if event_type == "created":
        notify_created(event.is_directory, src_path)

    if event_type == "deleted":
        notify_deleted(event.is_directory, src_path)

    if event_type == "moved":
        dest_path = os.path.relpath(event.dest_path, path)  # get relative path
        notify_moved(event.is_directory, src_path, dest_path)


def notify_created(is_dir, new_path):
    if os.path.splitext(new_path)[1] == ".swp":
        return
    else:
        sock = get_push_socket()
        curr_update = "created" + ',' + str(is_dir) + ',' + new_path
        print(curr_update)
        with sock:
            sock.sendall(curr_update.encode() + b'\n')
            if not is_dir:
                new_path = os.path.join(path, new_path)
                send_file(sock, new_path)


def notify_deleted(is_dir, old_path):
    if os.path.splitext(old_path)[1] == ".swp":
        notify_file_modified(old_path)
    else:
        sock = get_push_socket()
        curr_update = "deleted" + ',' + str(is_dir) + ',' + old_path
        print(curr_update)
        with sock:
            sock.sendall(curr_update.encode() + b'\n')


def notify_moved(is_dir, src_path, dest_path):
    sock = get_push_socket()
    curr_update = "moved" + ',' + str(is_dir) + ',' + src_path + ',' + dest_path
    with sock:
        sock.sendall(curr_update.encode() + b'\n')


# call only when .swp has been deleted.
def notify_file_modified(file_path):
    dir_name = os.path.dirname(file_path)
    swp_name = os.path.basename(file_path)
    file_name = swp_name[1:-4]  # slice the first "." and the last ".swp"
    file_path = os.path.join(dir_name, file_name)
    notify_deleted(False, file_path)
    notify_created(False, file_path)


# Pull requests - get updates from Server: ----------------------------------------------------------------------

def pull():
    pull_socket = get_pull_socket()
    update_socket = pull_socket.makefile('rb')
    status = update_socket.readline().strip().decode()
    print(status)
    if status != "No updates":
        command = update_socket.readline().strip().decode().split(',')
        get_update(command, update_socket)
        pull()


def get_update(cmd, on_sock):
    if cmd[0] == "created":
        is_dir, src_path = cmd[1], cmd[2]
        src_path = os.path.join(path, src_path)
        if is_dir == "True" and not os.path.exists(src_path):
            os.mkdir(src_path)
            print("created dir")
        elif is_dir == "False":
            get_file(on_sock, src_path)

    elif cmd[0] == "deleted":
        is_dir, del_path = cmd[1], cmd[2]
        del_path = os.path.join(path, del_path)
        if is_dir == "True":
            if os.listdir(del_path):
                print("error")
            os.rmdir(del_path)
        else:
            os.remove(del_path)

    elif cmd[0] == "moved":
        is_dir, src_path, dest_path = cmd[1], cmd[2], cmd[3]
        src_path = os.path.join(path, src_path)
        dest_path = os.path.join(path, dest_path)
        if is_dir == "False":
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            os.replace(src_path, dest_path)
        else:
            delete_dir(src_path)
            if not os.path.exists(dest_path):
                os.mkdir(dest_path)


def get_file(on_socket, file_path):  # type - makefile('rb')
    file_name = on_socket.readline()
    length = int(on_socket.readline())
    create_dirs(os.path.dirname(file_path))
    with open(file_path, 'wb') as f:
        while length:
            chunk = min(length, CHUNKSIZE)
            data = on_socket.read(chunk)
            if not data:
                break
            f.write(data)
            length -= len(data)
        else:  # only runs if while doesn't break and length==0
            print('Complete')


def create_dirs(d_path):
    if not os.path.exists(d_path):
        create_dirs(os.path.dirname(d_path))
        os.mkdir(d_path)


def delete_dir(path_to_del):
    if not os.path.exists(path_to_del):
        return
    for root, dirs, files in os.walk(path_to_del, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            os.rmdir(dir_path)
    os.rmdir(path_to_del)


# -------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    server_socket = get_server_socket()
    get_data_sock = server_socket.makefile(mode='rb')

    # First Time activating the Client - Initialization: -----------------------------------------------------------

    if client_id == 'None':
        client_id = get_data_sock.readline().strip().decode()  # get new ID
        client_comp = get_data_sock.readline().strip().decode()  # get new Computer number ("1")
        server_op = get_data_sock.readline().strip().decode()  # get server op name.
        get_data_sock.close()
        print(f"ID: {client_id}")
        print(f"Computer number:  {client_comp}")
        send_files(server_socket, path)  # will send files and close socket.

    else:
        client_comp = get_data_sock.readline().strip().decode()  # get new Computer number
        server_op = get_data_sock.readline().strip().decode()  # get server op name.
        print(f"Computer number:  {client_comp}")
        get_files(get_data_sock)  # pull the directory from server, will close makefile object ("get_data_sock").
        server_socket.close()

    # -----------------------------------------------------------------------------------------------------------
    # from now on the client app is running, but the client will connects to the server only to get/receive data.

    patterns = ["*"]  # contains the file patterns we want to handle (in my scenario, I will handle all the files)
    ignore_patterns = None  # contains the patterns that we don’t want to handle.
    ignore_directories = False  # a boolean that we set to True if we want to be notified just for regu
    # lar files.
    case_sensitive = False  # boolean that if set to “True”, made the patterns we introduced “case sensitive”.

    # Create event handler:
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

    # specify to the handler that we want this function to be called when an event is raised:
    my_event_handler.on_any_event = on_any_event

    # create an Observer:
    go_recursively = True  # a boolean that allow me to catch all the event that occurs even in sub directories.
    my_observer = polling.PollingObserver()  # better Observer
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)

    # -----------------------------------------------------------------------------------------------------------
    # start the Observer:
    my_observer.start()
    try:
        while True:
            time.sleep(time_cycle)
            pull()
    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()

    my_observer.stop()
