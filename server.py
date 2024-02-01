import socket
import threading
from math import ceil

PORT = 5050
HOST = socket.gethostbyname(socket.gethostname())
ADDRESS = (HOST, PORT)
FORMAT = 'utf-8'
FRAME_MESSAGE = 'F'
DISCONNECT_MESSAGE = 'D'
RESPONSE_READY_TO_RECEIVE = 'RR'
RESPONSE_REJECTED = 'REJ'


def handle_client_go_back_n(connection, address):
    print('Connected by', address)

    window_size = int(connection.recv(1).decode(FORMAT))

    result = []
    buffer = []
    connected = True
    rejected = False
    while connected:
        message = connection.recv(2).decode(FORMAT)

        if not message:
            continue

        message_type = message[0]
        message_data = message[1]

        if message_type == FRAME_MESSAGE:
            buffer.append(message_data)
            if len(buffer) == window_size:
                if rejected:
                    rejected = False
                    buffer.clear()
                    connection.send(f'{RESPONSE_REJECTED}'.encode(FORMAT))
                else:
                    transfer_from_buffer_to_memory(connection, window_size, buffer, result)
        elif message_type == DISCONNECT_MESSAGE:
            if len(buffer) != 0:
                if rejected:
                    rejected = False
                    buffer.clear()
                    connection.send(f'{RESPONSE_REJECTED}'.encode(FORMAT))
                else:
                    transfer_from_buffer_to_memory(connection, window_size, buffer, result)
            connected = False
            connection.close()
            print(f'Disconnected from {address}')
            break
        else:
            print(f'Unknown message type: {message_type}')
            rejected = True
            buffer.append(message_data)
            if len(buffer) == window_size:
                buffer.clear()


def transfer_from_buffer_to_memory(connection, window_size, buffer, memory):
    memory.extend(buffer)
    buffer.clear()
    print(f'Received {"".join(memory)}')
    connection.send(f'{RESPONSE_READY_TO_RECEIVE}{ceil(len(memory) / window_size)}'.encode(FORMAT))


def start(host):
    host.listen()
    print('Server started')
    while True:
        connection, address = host.accept()
        thread = threading.Thread(target=handle_client_go_back_n, args=(connection, address))
        thread.start()


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(ADDRESS)
        start(server)
