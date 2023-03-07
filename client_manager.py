import os
import random
import string


class ClientManager:
    def __init__(self, path=None):
        self.id_length = 10
        self.users = set()  # set consisting of userId for all users. (Potentially can hold more data than just id).
        self.clients_updates = {}  # Dictionary: userId -> (clientId -> updates)
        self.server_root = os.path.join(path, 'AllClients')
        os.mkdir(self.server_root)

    def get_user_root(self, user_id):
        if user_id not in self.users:
            raise ValueError(f"In get_user_root - got non existing id")
        return os.path.join(self.server_root, user_id)

    def add_user(self, new_id=None):    # new_id param is mainly for testing
        """
        Create new user id (make sure it is unique).
        Create client id (Since it is the first client of this user, the client id will be "1").
        Add to database.
        Create folder to the new user.
        :return: userId, clientId
        """
        new_user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=self.id_length))
        while new_user_id in self.users:
            new_user_id = ''.join(random.choices(string.ascii_letters + string.digits, k=self.id_length))
        if new_id:
            new_user_id = new_id
        new_client_id = "1"
        self.users.add(new_user_id)
        self.clients_updates[new_user_id] = {}
        self.clients_updates[new_user_id][new_client_id] = []
        os.mkdir(os.path.join(self.server_root, new_user_id))
        return new_user_id, new_client_id

    def add_client(self, user_id):
        """
        Create client id (if the user have x clients than this client id will be (x+1)).
        Add to database.
        :return: userId, clientId
        """
        if user_id not in self.users:
            raise ValueError(f"In add_client - got non existing id")
        new_client_id = str(len(self.clients_updates[user_id]) + 1)
        self.clients_updates[user_id][new_client_id] = []
        return new_client_id

    def update_clients(self, user_id, client_id, cmd):
        if user_id not in self.users:
            raise ValueError(f"In update_clients - got non existing user id")
        if client_id not in self.clients_updates[user_id]:
            raise ValueError(f"In update_clients - got non existing client id")
        for c_id in self.clients_updates[user_id].keys():  # update user's other clients lists
            if c_id != client_id:
                self.clients_updates[user_id][c_id].append(cmd)

    def get_updates(self, user_id, client_id):
        return self.clients_updates[user_id][client_id]

    def __str__(self):
        return f"Server root: {self.server_root}\n" \
               f"Users: {self.users}\n" \
               f"updates: {self.clients_updates}"
