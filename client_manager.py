import os
from utils import get_random_id


class ClientManager:

    def __init__(self, path=None):
        if not path:
            path = os.getcwd()
        self.server_dir = os.path.join(path, 'AllClients')
        os.mkdir(self.server_dir)

        # set consisting of userId for all users. (Potentially can hold more data than just id).
        self.users = set()
        # Dictionary: userId -> (clientId -> updates)
        self.clients_updates = {}

    def get_user_dir(self, user_id):
        if user_id not in self.users:
            return None
        return os.path.join(self.server_dir, user_id)

    def add_user(self):
        """
        Create new user id (make sure it is unique).
        Create client id (Since it is the first client of this user, the client id will be "1").
        Add to database.
        Create folder to the new user.
        :return: userId, clientId
        """
        user_id = get_random_id(self.users)
        client_id = "1"
        self.users.add(user_id)
        self.clients_updates[user_id] = {}
        self.clients_updates[user_id][client_id] = []
        os.mkdir(os.path.join(self.server_dir, user_id))

        return user_id, client_id

    def add_client(self, user_id):
        """
        Create client id (if the user have x clients than this client id will be (x+1)).
        Add to database.
        :return: userId, clientId
        """
        # check if user exists
        if user_id not in self.users:
            return "Invalid user id"

        client_id = str(len(self.clients_updates[user_id]) + 1)
        self.clients_updates[user_id][client_id] = []

        return client_id

    def update_clients(self, client_data, cmd):
        # check if client_id and user_id exist in the dictionary
        if client_data.u_id not in self.users:
            print("Invalid user_id")
            return

        if client_data.c_id not in self.clients_updates[client_data.u_id]:
            print("Invalid client_id")
            return

        # update user's clients lists
        for c_id in self.clients_updates[client_data.u_id].keys():
            if c_id != client_data.c_id:
                self.clients_updates[client_data.u_id][c_id].append(cmd)

    def get_updates(self, user_id, client_id):
        return self.clients_updates[user_id][client_id]


class ClientData:
    def __init__(self):
        self._u_id = None
        self._c_id = None
        self._os = None
        self._conn_type = None  # c_type = "NewClient" / "NewUser" / "Push" / "Pull"

    @property
    def u_id(self):
        return self._u_id

    @u_id.setter
    def u_id(self, value):
        self._u_id = value

    @property
    def c_id(self):
        return self._c_id

    @c_id.setter
    def c_id(self, value):
        self._c_id = value

    @property
    def os(self):
        return self._os

    @os.setter
    def os(self, value):
        self._os = value

    @property
    def conn_type(self):
        return self._conn_type

    @conn_type.setter
    def conn_type(self, value):
        self._conn_type = value

    def clear(self):
        self._u_id = None
        self._c_id = None
        self._os = None
        self._conn_type = None
