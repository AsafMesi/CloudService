import files_utils as fu
import os

CHUNKSIZE = 10_000_000


def send_file(on_sock, src_path):
    with on_sock:
        filename = src_path
        relpath = os.path.basename(filename)  # get file name from my_dir (file path)
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


# get a file from client and create it and it path in server path for this client
def get_file(on_socket, file_path):  # type - makefile('rb')
    _ = on_socket.readline()  # _ = filename, we don't need it.
    length = int(on_socket.readline())
    fu.create_dirs(os.path.dirname(file_path))
    with open(file_path, 'wb') as f:
        while length:
            chunk = min(length, CHUNKSIZE)
            data = on_socket.read(chunk)
            if not data:
                break
            f.write(data)
            length -= len(data)
