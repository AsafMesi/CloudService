import os
import sys
from utils import get_path, create_dirs, delete_dir


CHUNKSIZE = 10_000_000  # Reading the data in chunks, so we can handle large files.


# c_type = NewClient / NewUser / Push / Pull
def send_identifications(server_sock, u_id, c_id, c_type):
    server_sock.sendall(u_id.encode() + b'\n')          # send user id
    server_sock.sendall(c_id.encode() + b'\n')          # send user's client id
    server_sock.sendall(sys.platform.encode() + b'\n')  # send client's operating system.
    server_sock.sendall(c_type.encode() + b'\n')        # send client connection type.
    with server_sock.makefile(mode='rb') as get_synced_sock:
        if not (int(get_synced_sock.readline()) == 1):
            print("Server did not recognized client")


def get_files(sock, dir_path, sender_os):
    with sock.makefile(mode='rb') as get_files_sock:
        line = " "
        while True:
            if not line:
                # no more files, sender closed connection.
                break

            line = get_files_sock.readline()
            if line.strip().decode() == "empty dirs:":
                while True:
                    line = get_files_sock.readline()
                    if line.strip().decode() == 'Done.':
                        line = ''
                        break

                    dir_name = get_path(sender_os, line.strip().decode())
                    abs_dir_path = os.path.join(dir_path, dir_name)
                    os.makedirs(abs_dir_path, exist_ok=True)
            else:
                filename = get_path(sender_os, line.strip().decode())
                length = int(get_files_sock.readline())

                file_path = os.path.join(dir_path, filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, 'wb') as f:
                    while length != 0:
                        chunk = min(length, CHUNKSIZE)
                        data = get_files_sock.read(chunk)
                        if not data:
                            break
                        f.write(data)
                        length -= len(data)


def send_files(sock, src_path):
    for root, dirs, files in os.walk(src_path):
        for file in files:
            filename = os.path.join(root, file)
            send_file(sock, filename, src_path)

    send_empty_directories(sock, src_path)
    sock.sendall('Done.'.encode() + b'\n')


def send_empty_directories(sock, src_path):
    sock.sendall("empty dirs:".encode('utf-8') + b'\n')
    for root, dirs, files in os.walk(src_path):
        for directory in dirs:
            d = os.path.join(root, directory)
            if not os.listdir(d):
                d = os.path.relpath(d, src_path)
                sock.sendall(d.encode() + b'\n')


def send_file(sock, filename, root):
    relpath = os.path.relpath(filename, root)  # get relative file name base directory.
    file_size = os.path.getsize(filename)

    with open(filename, 'rb') as f:
        sock.sendall(relpath.encode() + b'\n')  # send file name + subdirectory and '\n'.
        sock.sendall(str(file_size).encode() + b'\n')  # send file size.

        # Send the file in chunks so large files can be handled.
        while True:
            data = f.read(CHUNKSIZE)
            if not data:
                break
            sock.sendall(data)


# get a file from client and create it and it path in server path for this client
def get_file(sock, file_path):  # type - makefile('rb')
    with sock.makefile(mode='rb') as get_file_sock:
        _ = get_file_sock.readline()  # _ = filename, we don't need it.
        length = int(get_file_sock.readline())
        create_dirs(os.path.dirname(file_path))
        with open(file_path, 'wb') as f:
            while length:
                chunk = min(length, CHUNKSIZE)
                data = get_file_sock.read(chunk)
                if not data:
                    break
                f.write(data)
                length -= len(data)


class FileEvent:
    def __init__(self, event_type, src_path, is_directory):
        self.event_type = event_type.lower()
        self.src_path = src_path
        self.is_directory = is_directory

    def __str__(self):
        return f"<FileEvent:" \
               f" event_type={self.event_type}," \
               f" src_path={self.src_path}," \
               f" is_directory={self.is_directory}>"


class FileSyncer:
    def __init__(self, main_dir, get_server_socket):
        self.main_dir = main_dir
        self.get_server_socket = get_server_socket

    def notify_server(self, event):

        if event.event_type == "modified":
            # directory renaming cause move and modified event, so we will ignore the modified event for directories.
            if not event.is_directory:
                self.notify_server(FileEvent("deleted", event.src_path, False))
                self.notify_server(FileEvent("created", event.src_path, False))
            return

        print(event)
        server_socket = self.get_server_socket()

        src_path = os.path.relpath(event.src_path, self.main_dir)

        if event.event_type == "created":
            self.notify_created(server_socket, event.is_directory, src_path)
        elif event.event_type == "deleted":
            self.notify_deleted(server_socket, event.is_directory, src_path)
        elif event.event_type == "moved":
            dest_path = os.path.relpath(event.dest_path, self.main_dir)  # get relative path
            self.notify_moved(server_socket, event.is_directory, src_path, dest_path)

        # We don't want to close the socket and continue with the code until we know that the server got the update.
        with server_socket.makefile(mode='rb') as get_synced_sock:
            if not (int(get_synced_sock.readline()) == 1):
                print("Server did not got update from the client")

        server_socket.close()

    def notify_created(self, server_socket, is_dir, new_path):
        if os.path.splitext(new_path)[1] == ".swp":
            return
        curr_update = f"created,{str(is_dir)},{new_path}"

        # sending file/dir name.
        server_socket.sendall(curr_update.encode() + b'\n')

        # if we created a file send the file content
        if not is_dir:
            new_path = os.path.join(self.main_dir, new_path)
            send_file(server_socket, new_path, self.main_dir)

    def notify_deleted(self, server_socket, is_dir, old_path):
        if os.path.splitext(old_path)[1] == ".swp":
            self.notify_file_modified(server_socket, old_path)
        else:
            curr_update = f"deleted,{str(is_dir)},{old_path}"
            server_socket.sendall(curr_update.encode() + b'\n')

    def notify_moved(self, server_socket, is_dir, old_path, new_path):
        print(f"old: {old_path}, new: {new_path}")
        curr_update = f"moved,{str(is_dir)},{old_path},{new_path}"
        server_socket.sendall(curr_update.encode() + b'\n')

    def notify_file_modified(self, server_socket, file_path):
        dir_name = os.path.dirname(file_path)
        swp_name = os.path.basename(file_path)
        file_name = swp_name[1:-4]  # slice the first "." and the last ".swp"
        file_path = os.path.join(dir_name, file_name)
        self.notify_deleted(server_socket, False, file_path)
        self.notify_created(server_socket, False, file_path)


def handle_created(is_dir, path, sock, main_dir, sender_os):
    src_path = os.path.join(main_dir, path)
    src_path = get_path(sender_os, src_path)
    if os.path.exists(src_path):  # check if the "create" operation is already made- to avoid duplications.
        return False
    if is_dir == "True":
        os.makedirs(src_path)  # create the dir
    elif is_dir == "False":
        get_file(sock, src_path)  # get the file we need to create from the client
    return True


def handle_deleted(is_dir, path, main_dir):
    del_path = path
    del_path = os.path.join(main_dir, del_path)
    if not os.path.exists(del_path):  # check if the "delete" operation is already made- to avoid duplications.
        return False
    if is_dir == "True":
        delete_dir(del_path)  # delete dir and all it's recursive dirs too
    else:
        if os.path.exists(del_path):
            os.remove(del_path)
    return True


def handle_moved(is_dir, path, main_dir, sender_os):
    old_path, new_path = path.split(',')
    old_path = get_path(sender_os, old_path)
    new_path = get_path(sender_os, new_path)

    old_path = os.path.join(main_dir, old_path)
    new_path = os.path.join(main_dir, new_path)
    # check if the "moved" operation is already made to avoid duplications:
    if not os.path.exists(old_path) and os.path.exists(new_path):
        return False
    if is_dir == "False":
        os.makedirs(os.path.dirname(new_path), exist_ok=True)  # create the path we need to create the file
        os.replace(old_path, new_path)
    else:  # delete from source path and create the dir in destination path
        delete_dir(old_path)
        if not os.path.exists(new_path):
            os.makedirs(new_path)
    return True


def get_update(cmd_type, is_dir, path, sock, main_dir, sender_os):
    if cmd_type == "created":
        return handle_created(is_dir, path, sock, main_dir, sender_os)

    elif cmd_type == "deleted":
        return handle_deleted(is_dir, path, main_dir)

    elif cmd_type == "moved":
        return handle_moved(is_dir, path, main_dir, sender_os)

    return False
