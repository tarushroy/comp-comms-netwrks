# CSC 361
# Assignment P1
# Tarush Roy, V00883469

# Simple Web Server (SWS)

# imports
from socket import *
import select
import sys
import queue
import time
import re

# create TCP/IP socket
server = socket(AF_INET, SOCK_STREAM)
# set to non-blocking mode
server.setblocking(0)

# check for correct number of arguments passed through command line
if len(sys.argv) != 3:
    print("Please enter an IP address and port number.")
    exit()

# get server address from input
ip_address = sys.argv[1]
port_number = int(sys.argv[2])
server_address = (ip_address, port_number)

# bind the socket to the port
# bind address and server_address
server.bind(server_address)

# listen for incoming connections
server.listen(5)

# sockets from which we expend to read
# sockets to watch for readability
inputs = [server]

# sockets to which we expect to write
# sockets to watch for writability
outputs = []

# outgoing message queues (socket:Queue)
response_messages = {}
response_message_log = ""

# request message
request_message = {}
request_message_log = ""

# persistence variables
persistent = {} #False
keep_alive = {} #None
close_connection = {} #None

# log printed
log_printed = False

# client address
client_address = {}

# functions

def connection_header(s):
    global keep_alive
    global persistent
    global response_messages

    if keep_alive[s] == True:
        response_messages[s].put("Connection: Keep-alive\n")
    elif keep_alive[s] == False:
        response_messages[s].put("Connection: Close\n")
    elif keep_alive[s] == None and persistent[s] == True:
        response_messages[s].put("Connection: Close\n")
        keep_alive[s] = False
    elif keep_alive[s] == None:
        keep_alive[s] = False
        
    response_messages[s].put("\n")

#functions - end

# handle sockets
while True:
    # wait for at least one of the sockets to be ready for processing
    readable, writable, exceptional = select.select(inputs, outputs, inputs)

    # handle inputs
    for s in readable:
        if s == server:
            # a readable server socket is ready to accept a connection
            connection, client_addr = s.accept()
            client_address[connection] = client_addr
            connection.setblocking(0)
            s.settimeout(60)
            inputs.append(connection)
            # give the connection a queue for data we want to send
            response_messages[connection] = queue.Queue()
            request_message[connection] = queue.Queue()
            keep_alive[connection] = None
            persistent[connection] = False
            close_connection[connection] = None

        else:
            # receive message from receiving buffer
            message = s.recv(1024).decode()
            if message:
                outputs.append(s)
                
                if re.search("^(\r\n|\n)$", message):
                    request = request_message[s].get_nowait()
                    filename = re.split(r"[/ ]", request)[2]
                    
                    # try to open file
                    try:
                        f = open(filename, "r")
                    except FileNotFoundError:
                        # file doesnt exist
                        response_messages[s].put("HTTP/1.0 404 Not Found\n")
                        response_message_log = "HTTP/1.0 404 Not Found"
                        # handle connection header line
                        connection_header(s)
                    else:
                        # file exists, return contents
                        response_messages[s].put("HTTP/1.0 200 OK\n")
                        response_message_log = "HTTP/1.0 200 OK"
                        # response header, if any --- here
                        connection_header(s)
                        response_messages[s].put(f.read())
                        response_messages[s].put("\n")
                    
                    if keep_alive[s] == False:
                        close_connection[s] = True

                    # reset keep_alive
                    keep_alive[s] = None
                    log_printed = False
               
                # persistent connection handling
                elif re.search("connection:( *)keep-alive( *)", message, re.IGNORECASE):
                    keep_alive[s] = True
                    persistent[s] = True
                elif re.search("connection:( *)close( *)", message, re.IGNORECASE):
                    keep_alive[s] = False

                elif not re.search("^GET /(.+) HTTP/1.0(\r\n|\n)", message):
                    response_messages[s].put("HTTP/1.0 400 Bad Request\n")
                    response_message_log = "HTTP/1.0 400 Bad Request"
                    connection_header(s)
                    close_connection[s] = True
                
                else:
                    request_message[s].put(message)
                    request_message_log = message.strip()
            
            else:
                # simply interpret empty result as closed connection
                # stop listening for input on the connection if s in outputs
                persistent[s] = False
                outputs.remove(s)
                inputs.remove(s)
                s.close()
    
    # handle outputs
    for s in outputs:
        try:
            # get message from response_messages
            next_msg = response_messages[s].get_nowait()
        except queue.Empty:
            # no messages waiting so stop checking for writability
            outputs.remove(s) # check for persistence first
            # check if timeout or connection is persistent or not, and close socket accordingly
            # handle closing
            if close_connection[s] == True:
                inputs.remove(s)
                del response_messages[s]
                del request_message[s]
                s.close()
                persistent[s] = False
                close_connection[s] = None

        else:
            # send messages and print logs if finish responding to request
            s.send(next_msg.encode())
            # print logs
            if log_printed == False:
                localtime = time.localtime(time.time())
                cur_client_adrr = client_address[s]
                print(time.asctime(localtime) + ": " + client_addr[0] + ":" + str(client_addr[1]) + " " + request_message_log + "; " + response_message_log)
                log_printed = True
                request_message_log = ""
                response_message_log = ""

    # handle exceptional conditions
    for s in exceptional:
        print("exceptional")
        # stop listening for input on the connection inputs.remove(s)
        if s in outputs:
            persistent[s] = False
            outputs.remove(s)
            s.close()
