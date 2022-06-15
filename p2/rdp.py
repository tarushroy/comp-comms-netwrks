# Reliable Datagram Protocol (RDP)

# CSC 361 A01 Fall 2021
# Programming Assignment 2 (P2)

# Student Information
# NAME: Tarush Roy
# NUMBER: V00883469

import sys
import os
import socket
import select
import time
import datetime
import queue
import re

import pdb

# INPUTS HANDLING AND SERVER

# command line error and usage
if len(sys.argv) != 5:
    sys.exit("USAGE:\n    python3 rdp.py [ip_address] [port_number] [read_file_name] [write_file_name]")

# get cmdline inputs
ip_address = sys.argv[1]
port_number = int(sys.argv[2])
read_file_name = sys.argv[3]
write_file_name = sys.argv[4]

# host and port number of server for rdp to bind
server_address = (ip_address, port_number)

# NOTE
# Change host to h2
h2_address = ('localhost', 8888)

# create DATAGRAM socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setblocking(0)

# bind server address
s.bind(server_address)


# FILE HANDLING

# open read file
readfile = open(read_file_name, 'rb')

# open write file
writefile = open(write_file_name, 'wb')


# GLOBAL CONSTANTS AND VARIABLES

# local timezone
local_tmzone = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

# lists for select readable, writable, exceptional
reader = [s]
writer = [s]
exp = [s]


# Queues for processing packets

# write queue
write_queue = queue.Queue()

# read queue
read_queue = queue.Queue()


# Packet Information

# command of the packet
command = ''

# headers of the packet, seperated by ;
headers = ''

# payload of the packet
payload = ''


# SENDER

# SENDER CONSTANTS AND VARIABLES

# file size
read_file_size = os.path.getsize(read_file_name)

# packet timers
packet_timers = []

# current packet
packet = ''

# list of payload blocks to get payload per packet from
payload_blocks = []

# fin sent
fin_sent = False

# Packets information

# sequence number
send_seq_num = 0

# acknowledgment number
send_ack_num = 0

# number of packets to send
num_packets_sent = 0


# RECEIVER

# RECEIVER CONSTANTS AND VARIABLES

# window size
window_size = 2048

# default window size
default_window_size = window_size

# buffer size
recv_buffer_size = 2048

# Packet Information

# command of the packet
recv_command = ''

# list of headers of the received packet
recv_headers = []

# recevied headers in string form
recv_headers_str = ''

# payload of the packet
recv_payload = ''

# receive payload buffer
payload_buffer = ''


# 'FIN' packet received variable
# boolean
fin_recvd = False


# current latest ack number
cur_latest_ack = 0

# Packets Information

# sequence number
recv_seq_num = 0

# acknowledgment number
recv_ack_num = 0

# received length
recv_length = 0

# number of packets received
num_packets_recvd = 0


# FUNCTIONS

# Global Functions

# function to print logs
def print_log(event, command, headers):
    localtime = time.asctime(time.localtime(time.time()))
    localtime_split = localtime.split()
    localtime_split.insert(4, str(local_tmzone))
    localtime = ' '.join(localtime_split)
    print(localtime + ': ' + event + '; ' + command + '; ' + headers)


# Sender Functions

# function to build a packet given command, headers and payload
def build_packet(command, headers, payload = None):
    global packet

    packet = ''
    packet = command + '\n'
    packet += '\n'.join(headers.split('; '))
    if payload:
        packet += ('\n\n' + payload)

    return packet

# splits read file into 1024 byte blocks to be used in payload by sender
def split_file():
    global payload_blocks

    while True:
        block = readfile.read(1024)
        if block == b'':
            break
        payload_blocks.append(block)
    
# function to reset variables of a packet
def reset_packet_info():
    global command
    global headers
    global payload

    command, headers, payload = '', '', ''


# Receiver Functions

# build acknowledgement packet
def build_ack_packet(seq_num, length = None):
    global command
    global headers
    global recv_ack_num
    global cur_latest_ack

    if length:
        recv_ack_num = seq_num + length
    else:
        recv_ack_num = seq_num + 1
    
    if(recv_ack_num > cur_latest_ack):
        cur_latest_ack = recv_ack_num

    command = 'ACK'
    headers = 'Acknowledgement: ' + str(recv_ack_num) + '; Window: ' + str(window_size)
    packet = build_packet(command, headers)
    write_queue.put(packet.encode())
    writer.append(s)

def build_rst_packet(seq_num):
    command = 'RST'
    headers = 'Sequence: ' + str(seq_num) + '; Length: 0'
    packet = build_packet(command, headers)
    write_queue.put(packet.encode())
    writer.append(s)


# MAIN CODE

# SENDER
# break readfile into blocks
split_file()

# build and send first packet
# SYN packet
command = 'SYN'
headers = 'Sequence: ' + str(send_seq_num) + '; Length: 0'
packet = build_packet(command, headers)
write_queue.put(packet.encode())

# main server loop
while True:
    # select
    readable, writable, exceptional = select.select(reader, writer, exp, 1)

    # handle writable sockets
    if s in writable:
        # get packet to send and send it
        write_packet = write_queue.get()
        s.sendto(write_packet, h2_address)

        # reset packet
        packet = ''

        # remove socket from writer
        writer.remove(s)

        # parse for log info
        split_data = write_packet.decode().split('\n\n', 1)
        packet_lines = split_data[0].splitlines()
        recv_command = packet_lines[0]

        # print log
        print_log('Send', recv_command, '; '.join(packet_lines[1:]))
    
    # handle readable sockets
    if s in readable:
        # get packet
        data, server = s.recvfrom(recv_buffer_size)

        # add to buffer? based on some information

        # parse data packet
        split_data = data.decode().split('\n\n', 1)
        packet_lines = split_data[0].splitlines()
        recv_command = packet_lines[0]
        recv_headers = packet_lines[1:]
        recv_headers_str = '; '.join(recv_headers)
        
        # print log
        print_log('Receive', recv_command, recv_headers_str)

        # reset packet info
        packet = ''
        reset_packet_info()

        # MAIN IF_ELSE_IF_ELSE
        # check the command of the packet
        # handle it correctly
        
        # if command is SYN
        if(recv_command == 'SYN'):
            # RECEIVER HERE
            if(re.match('^Sequence: \d+; Length: \d+$', recv_headers_str)):
                # get seq num
                recv_seq_num = int(recv_headers[0].split(': ')[1])
            else:
                # send rst
                build_rst_packet(recv_ack_num)

            # send acknowledgement packet
            build_ack_packet(recv_seq_num)
        
        # if command is FIN
        elif(recv_command == 'FIN'):
            # RECEIVER HERE
            fin_recvd = True

            if(re.match('^Sequence: \d+; Length: \d+$', recv_headers_str)):
                # get seq num
                recv_seq_num = int(recv_headers[0].split(': ')[1])
            else:
                # send rst
                build_rst_packet(recv_ack_num)
        
            # send acknowledgement packet
            build_ack_packet(recv_seq_num)
        
        # if command is DAT
        elif(recv_command == 'DAT'):
            # RECEIVER HERE

            # get payload
            recv_payload = split_data[1]

            # check for unrecognizable or incompatible packet
            if(re.match('^Sequence: \d+; Length: \d+$', recv_headers_str)):
                # get seq num
                recv_seq_num = int(recv_headers[0].split(': ')[1])
                recv_length = int(recv_headers[1].split(': ')[1])
            else:
                # send rst
                build_rst_packet(recv_ack_num)

            # increment packet num
            num_packets_recvd += 1

            # below acked?
            if(recv_seq_num < recv_ack_num):
                # drop packet
                continue

            # beyond acked + window?
            elif(recv_seq_num > (recv_ack_num + window_size)):
                # send rst
                build_rst_packet(recv_seq_num)
            
            # out of order?
            elif(recv_seq_num != recv_ack_num):
                # drop
                continue

            # in order?
            elif(recv_seq_num == recv_ack_num):
                # buffer data
                payload_buffer += recv_payload
                # update ackno
                recv_ack_num = recv_seq_num
                # also update window?
                # window_size = window_size - len(recv_payload)

            # enough in-order data?
            if((len(payload_buffer) == window_size) or (recv_length < 1024) or (len(payload_buffer) < (recv_length + 1))): # or (len(payload_buffer) < (recv_length + 1))
                # write buffer to file
                writefile.write(payload_buffer.encode())
                payload_buffer = ''
            
            # update window size
            window_size = default_window_size

            # send ack
            build_ack_packet(recv_seq_num, recv_length)
        
        # if command is ACK
        elif(recv_command == 'ACK'):
            # SENDER HERE

            # pdb.set_trace()

            if(re.match('^Acknowledgement: \d+; Window: \d+$', recv_headers_str)):
                recv_ack_num = int(recv_headers[0].split(': ')[1])

                if(recv_ack_num > cur_latest_ack):
                    cur_latest_ack = recv_ack_num

                window_size = int(recv_headers[1].split(': ')[1])
            else:
                # rst
                build_rst_packet(recv_ack_num)
            
            if(recv_ack_num < cur_latest_ack):
                continue

            # get number of packets to send
            num_packets_send = window_size // 1024

            if(len(payload_blocks) < num_packets_send):
                num_packets_send = len(payload_blocks)

            if fin_sent:
                break

            # update ack and seq num
            send_ack_num = int(re.findall(r'\d+', recv_headers[0])[0])
            send_seq_num = send_ack_num

            # if sent all packets, send fin
            if(num_packets_sent == len(payload_blocks)):
                command = 'FIN'
                headers = 'Sequence: ' + str(send_seq_num) + '; Length: 0'
                packet = build_packet(command, headers)
                write_queue.put(packet.encode())
                writer.append(s)
                fin_sent = True

            else:
                # send DAT packet
                # set up timer
                for i in range(num_packets_send):
                    packet_timers.append(time.perf_counter())
                    command = 'DAT'
                    payload = payload_blocks[num_packets_sent]
                    headers = 'Sequence: ' + str(send_seq_num) + '; Length: ' + str(len(payload))
                    packet = build_packet(command, headers, payload.decode())
                    write_queue.put(packet.encode())
                    writer.append(s)
                    num_packets_sent += 1
                    send_seq_num += len(payload)
        
        # if command is RST
        elif(recv_command == 'RST'):
            break

        else:
            # wrong command, send RST
            build_rst_packet(recv_ack_num)
    
    # check for timeouts
    if not (readable or writable or exceptional):
        # send packet again
        # add socket back to writer
        writer.append(s)

s.close()
