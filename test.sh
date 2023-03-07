#!/bin/bash

mkdir user1client1/
mkdir user1client2/

root=$1

# Copy resources to user1client1
cp -R resources/* user1client1/

# Start the server in the background and redirect output to server.log
echo "Start server"
touch server.log
python3 "$root/server.py" 33333 > server.log 2>&1 &

# Wait for the server to start up
sleep 3

# Run the first client
echo "Start first client"
touch client1.log
python3 "$root/client.py" 10.0.2.15 33333 "$(pwd)/user1client1" 1 > client1.log 2>&1 &

# Wait for the first client to finish setting up
sleep 2

# Run the second client with the ID printed by the server
CLIENT_ID=$(head -n 1 server.log)
echo "Start second client (ID = $CLIENT_ID)"
touch client2.log
python3 "$root/client.py" 127.0.0.1 33333 "$(pwd)/user1client2" 1 $CLIENT_ID > client2.log 2>&1 &

# Wait for the clients to finish setting up
sleep 2

# Make some changes in user1client1

echo "Make some changes in user1client1"
mkdir user1client1/new_dir

sleep 1

touch user1client1/new_file

sleep 1

mv user1client1/file1.txt user1client1/renamed_file.txt

sleep 1



# Make some changes in user1client2

echo "Make some changes in user1client2"
echo "Hello World" > user1client2/file2.txt

sleep 1

rm user1client2/file3.txt

sleep 2


# Copy NewContent1 to user1client1
echo "Copy NewContent1 to user1client1"
cp -R NewContent1/* user1client1/
sleep 3

# Copy NewContent2 to user1client2
echo "Copy NewContent1 to user1client2"
cp -R NewContent2/* user1client2/
sleep 3

# Make some changes to the directories
echo "Make some changes to the directories"
rm -r user1client1/dir1/file1.txt
mv user1client1/dir2/file2.txt user1client1/dir3/
echo "new content" > user1client1/dir4/newfile.txt
mkdir user1client2/newdir/
mv user1client1/dir4/newfile.txt user1client2/newdir/renamedfile.txt

echo "Finishing test.."


# Wait for the clients to finish running

sleep 5



# Kill the server and clients

pkill -f server.py

pkill -f client.py

