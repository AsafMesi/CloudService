import random
import string


# return random string with 128 characters compared of letters and numbers.
def get_random_id(id_set):
    new_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
    while new_id in id_set:
        new_id = ''.join(random.choices(string.ascii_letters + string.digits, k=128))
    return new_id


# Check if the id is in the database, if so return the computer number of this user.
# Otherwise, give him a new computer number.
def get_comp_num(db, c_id):
    if db.keys().__contains__(c_id):  # check if the ID exists in data_base dictionary
        c_comp = str(len(db[c_id]) + 1)
        db[c_id][c_comp] = list()  # new computer has joined the data_base for this id.
    else:  # new computer for this id
        c_comp = "1"
        db[c_id] = {}
        db[c_id][c_comp] = list()
    return c_comp


# Update the data_base dictionary with the updates we get from client in push activity
def update_computers(db, c_id, c_comp, cmd):
    for k in db[c_id].keys():
        if k != c_comp:
            db[c_id][k].append(cmd)
