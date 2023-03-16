import datetime
import os


class ConnectionLogger:
    def __init__(self, log_file_path, description):
        if os.path.exists(log_file_path):
            raise ValueError(f"Log file {log_file_path} already exists")

        self.log_file_path = log_file_path
        with open(self.log_file_path, 'w') as log_file:
            log_file.write(f"{description}:\n")

    def _log(self, message):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S.%f]")
        log_message = f"{timestamp} {message}\n"
        with open(self.log_file_path, "a") as log_file:
            log_file.write(log_message)

    def connection_accepted(self, client_ip_port):
        message = f"Server accepted connection from: (IP, port) = {client_ip_port}"
        self._log(message)

    def user_created(self, user_id):
        message = f"New user has been created!\n" \
                  f"User ID: {user_id}\n" \
                  f"Client ID: 1"
        self._log(message)

    def client_created(self, user_id, client_id):
        message = f"New client has been created!\n" \
                  f"User ID: {user_id}\n" \
                  f"Client ID: {client_id}"
        self._log(message)

    def push_requested(self, user_id, client_id, req):
        message = f"PUSH\n" \
                  f"User ID: {user_id}, Client ID: {client_id}\n" \
                  f"Request: {req}."
        self._log(message)

    def pull_requested(self, user_id, client_id, req):
        message = f"PULL\n" \
                  f"User ID: {user_id}, Client ID: {client_id}\n" \
                  f"Request: {req}."
        self._log(message)

    def connection_error(self, err_msg):
        self._log(err_msg)

    def connection_ended(self):
        message = f"Connection ended!\n"
        self._log(message)
