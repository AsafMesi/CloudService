import os
import sys
from watchdog.observers import polling
from watchdog.events import PatternMatchingEventHandler

CHUNK = 10_000_000  # Reading & Sending the data in chunks, so we can handle large files.


def get_path(src_platform, src_path, src_sep='/'):
    if src_platform == 'win32':
        src_sep = '\\'
    if os.sep != src_sep:
        src_path = src_path.replace(src_sep, os.sep)
    return src_path


def send_file(sock, root, path):
    relpath = os.path.relpath(path, root)  # get relative file name base directory.
    file_size = os.path.getsize(path)
    with open(path, 'rb') as f:
        sock.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
        sock.sendall(str(file_size).encode() + b'\n')  # send file size.
        sock.sendall(sys.platform.encode() + b'\n')  # send os.
        # Send the file in chunks so large files can be handled.
        while True:
            data = f.read(CHUNK)
            if not data:
                break
            sock.sendall(data)


def get_file(read_socket, root):  # type - makefile('rb')
    path = read_socket.readline().strip().decode()
    length = int(read_socket.readline())
    sender_sys = read_socket.readline().strip().decode()
    path = get_path(sender_sys, path)
    path = os.path.join(root, path)
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)
    with open(path, 'wb') as f:
        while length:
            chunk = min(length, CHUNK)
            data = read_socket.read(chunk)
            if not data:
                break
            f.write(data)
            length -= len(data)


def send_files(sock, root):
    with sock:
        # Sending all files.
        for curr_root, _, files in os.walk(root):
            for file in files:
                sock.sendall("Sending file".encode() + b'\n')
                path = os.path.join(curr_root, file)
                send_file(sock, root, path)

        # All files have been sent.
        sock.sendall("Done sending files.".encode() + b'\n')

        # Sending all empty folders
        for curr_root, dirs, _ in os.walk(root):
            for directory in dirs:
                path = os.path.join(curr_root, directory)
                if not os.listdir(path):
                    sock.sendall("Sending empty folder".encode() + b'\n')
                    relpath = os.path.relpath(path, root)
                    sock.sendall(relpath.encode() + b'\n')
                    sock.sendall(sys.platform.encode() + b'\n')

        # All empty folders have been sent.
        sock.sendall("Done sending folders.".encode() + b'\n')


def get_files(read_socket, root):
    # Getting files.
    while True:
        line = read_socket.readline().strip().decode()
        if line == "Done sending files.":
            break
        else:
            get_file(read_socket, root)

    # Getting Empty folders.
    while True:
        line = read_socket.readline().strip().decode()
        if line == "Done sending folders.":
            break
        else:
            dirname = read_socket.readline().strip().decode()
            sender_sys = read_socket.readline().strip().decode()
            dirname = get_path(sender_sys, dirname)
            dirname = os.path.join(root, dirname)
            os.makedirs(dirname, exist_ok=True)


def handle_created(cmd, root, sender_os, read_socket):
    is_directory, path = cmd.split(',')
    path = os.path.join(root, get_path(sender_os, path))

    if os.path.exists(path):  # check if the "create" operation is already made- to avoid duplications.
        return None

    cmd = ','.join(["created", is_directory, path])
    if is_directory == "True":
        os.makedirs(path)  # create the dir
    elif is_directory == "False":
        get_file(read_socket, root)  # get the file we need to create from the client
    return cmd


# delete dir recursively
def delete_dir(path_to_del):
    if not os.path.exists(path_to_del):
        return
    for root, dirs, files in os.walk(path_to_del, topdown=False):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for d in dirs:
            dir_path = os.path.join(root, d)
            os.rmdir(dir_path)
    os.rmdir(path_to_del)


def handle_deleted(cmd, root, sender_os):
    is_directory, path = cmd.split(',')
    path = os.path.join(root, get_path(sender_os, path))

    if not os.path.exists(path):  # check if the "delete" operation is already made- to avoid duplications.
        return None

    cmd = ','.join(["deleted", is_directory, path])
    if is_directory == "True":
        delete_dir(path)
    else:
        os.remove(path)
    return cmd


def handle_moved(cmd, root, sender_os):
    is_directory, old_path, new_path = cmd.split(',')
    old_path = os.path.join(root, get_path(sender_os, old_path))
    new_path = os.path.join(root, get_path(sender_os, new_path))

    # check if the "moved" operation is already made to avoid duplications:
    if not os.path.exists(old_path) and os.path.exists(new_path):
        return None

    cmd = ','.join(["moved", is_directory, old_path, new_path])
    if is_directory == "False":
        # create the path we need to create the file
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.replace(old_path, new_path)
    else:
        # delete from source path and create the dir in destination path
        delete_dir(old_path)
        if not os.path.exists(new_path):
            os.makedirs(new_path)
    return cmd


def get_update(read_socket, root, sender_os):
    csv_command = read_socket.readline().strip().decode()
    cmd_type, cmd = csv_command.split(',', 1)
    applied_cmd = None
    match cmd_type:
        case "created":
            applied_cmd = handle_created(cmd, root, sender_os, read_socket)
        case "deleted":
            applied_cmd = handle_deleted(cmd, root, sender_os)
        case "moved":
            applied_cmd = handle_moved(cmd, root, sender_os)
        case _:
            print("Unknown command type")
    return applied_cmd


def send_update(send_sock, root, csv_command):
    cmd_type, is_dir, path = csv_command.split(',', 2)
    match cmd_type:
        case "created":
            relpath = os.path.relpath(path, root)
            csv_cmd = f"{cmd_type},{is_dir},{relpath}"
            send_sock.sendall(csv_cmd.encode() + b'\n')
            if is_dir == "False":
                send_file(send_sock, root, path)
            send_sock.close()

        case "deleted":
            relpath = os.path.relpath(path, root)
            csv_cmd = f"{cmd_type},{is_dir},{relpath}"
            send_sock.sendall(csv_cmd.encode() + b'\n')
            send_sock.close()

        case "moved":
            old_path, new_path = path.split(',')
            old_relpath = os.path.relpath(old_path, root)
            new_relpath = os.path.relpath(new_path, root)
            csv_cmd = f"{cmd_type},{is_dir},{old_relpath},{new_relpath}"
            send_sock.sendall(csv_cmd.encode() + b'\n')
            send_sock.close()

        case _:
            print("unknown event")


class FileEvent:
    def __init__(self, event_type, is_directory, src_path, dest_path=None):
        self.event_type = event_type.lower()
        self.is_directory = is_directory
        self.src_path = src_path
        self.dest_path = dest_path

    def __str__(self):
        rep = f"<FileEvent:" \
               f" event_type={self.event_type}," \
               f" is_directory={self.is_directory}" \
               f" src_path={self.src_path}>"
        if self.dest_path:
            rep = ', '.join([rep, self.dest_path])
        return rep


class ClientFileObserver:
    def __init__(self, root, on_any_event):
        patterns = ["*"]  # contains the file patterns we want to handle (in my scenario, I will handle all the files)
        ignore_patterns = None  # contains the patterns that we don’t want to handle.
        ignore_directories = False  # a boolean that we set to True if we want to be notified just for files.
        case_sensitive = False  # boolean that if set to “True”, made the patterns we introduced “case-sensitive”.

        # Create event handler:
        self._event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

        # Specify to the handler that we want this function to be called when an event is raised:
        self._event_handler.on_any_event = lambda event: on_any_event(event)
        self.root = root

        # Create an Observer:
        self._observer = polling.PollingObserver()  # better Observer

    def schedule(self):
        # 'recursive=True' allow me to catch events that occurs in subdirectories.
        self._observer.schedule(self._event_handler, self.root, recursive=True)

    def un_schedule(self):
        self._observer.unschedule_all()

    def start(self):
        self._observer.start()

    def stop(self):
        self._observer.stop()

    def join(self):
        self._observer.join()
