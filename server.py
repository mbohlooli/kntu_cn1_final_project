import socket
import threading
import time

PORT = 5050
HOST = socket.gethostbyname(socket.gethostname())
ADDRESS = (HOST, PORT)
FORMAT = 'utf-8'
FRAME_MESSAGE = 'F'
DISCONNECT_MESSAGE = 'D'
RESPONSE_READY_TO_RECEIVE = 'RR'
RESPONSE_REJECTED = 'REJ'
GO_BACK_N = 'GO_BACK_N_______'
SELECTIVE_REJECT = 'SELECTIVE_REJECT'


def handle_client(connection, address, protocol):
    print('Connected by', address)

    window_size = int(connection.recv(1).decode(FORMAT))

    result = []
    buffer = []
    windows_received = set()
    connected = True
    rejected = False
    rejected_index = -1
    while connected:
        message = connection.recv(3).decode(FORMAT)

        if not message:
            continue

        message_type = message[0]
        window_index = int(message[1])
        message_data = message[2]

        if protocol == GO_BACK_N:
            if window_index in windows_received:
                continue

            if message_type == FRAME_MESSAGE:
                buffer.append(message_data)
                if len(buffer) == window_size:
                    if window_index == 4:
                        time.sleep(1)
                    if rejected:
                        rejected = False
                        buffer.clear()
                        connection.send(f'{RESPONSE_REJECTED}{window_index}'.encode(FORMAT))
                    else:
                        windows_received.add(window_index)
                        transfer_from_buffer_to_memory(connection, window_index, buffer, result)
            elif message_type == DISCONNECT_MESSAGE:
                if len(buffer) != 0:
                    if rejected:
                        rejected = False
                        buffer.clear()
                        connection.send(f'{RESPONSE_REJECTED}{window_index}'.encode(FORMAT))
                    else:
                        windows_received.add(window_index)
                        transfer_from_buffer_to_memory(connection, window_index, buffer, result)
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
        elif protocol == SELECTIVE_REJECT:
            if window_index in windows_received and rejected_index == -1:
                continue

            if message_type == FRAME_MESSAGE:
                if len(buffer) == window_size and rejected_index != -1:
                    buffer[rejected_index] = message_data
                    rejected_index = -1
                else:
                    buffer.append(message_data)
                if len(buffer) == window_size and rejected_index == -1:
                    if window_index == 4:
                        time.sleep(1)
                    windows_received.add(window_index)
                    transfer_from_buffer_to_memory(connection, window_index, buffer, result)
            elif message_type == DISCONNECT_MESSAGE:
                if rejected_index != -1:
                    buffer[rejected_index] = message_data
                    rejected_index = -1
                if len(buffer) != 0:
                    windows_received.add(window_index)
                    transfer_from_buffer_to_memory(connection, window_index, buffer, result)
                connected = False
                connection.close()
                print(f'Disconnected from {address}')
                break
            else:
                print(f'Unknown message type: {message_type}')
                rejected_index = len(buffer)
                connection.send(f'{RESPONSE_REJECTED}{rejected_index}'.encode(FORMAT))
                buffer.append(message_data)
                if len(buffer) == window_size:
                    buffer.clear()
        else:
            print(f'Unknown protocol: {protocol}')
            connected = False
            connection.close()


def transfer_from_buffer_to_memory(connection, window_index, buffer, memory):
    memory.extend(buffer)
    buffer.clear()
    print(f'Received {"".join(memory)}')
    connection.send(f'{RESPONSE_READY_TO_RECEIVE}{window_index}'.encode(FORMAT))


def start(host):
    host.listen()
    print('Server started')
    while True:
        connection, address = host.accept()
        protocol = connection.recv(len(GO_BACK_N)).decode(FORMAT)
        thread = threading.Thread(target=handle_client, args=(connection, address, protocol))
        thread.start()


if __name__ == '__main__':
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(ADDRESS)
        start(server)
