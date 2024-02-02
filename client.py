import socket
from math import ceil

from server import ADDRESS, FORMAT, FRAME_MESSAGE, DISCONNECT_MESSAGE, RESPONSE_READY_TO_RECEIVE, RESPONSE_REJECTED, \
    GO_BACK_N, SELECTIVE_REJECT


def send(connection, batch_size, message, protocol=GO_BACK_N):
    if protocol not in {GO_BACK_N, SELECTIVE_REJECT}:
        raise ValueError(f'Unknown protocol {protocol}')

    windows_timed_out = []
    connection.settimeout(0.5)
    for index, frame_set in enumerate(partition(message, batch_size)):
        print(frame_set)

        is_last_frame = index == ceil(len(message) / batch_size) - 1

        try:
            if index == 2:
                response = send_frame_set_with_error(connection, index, frame_set, batch_size, is_last_frame)
            else:
                response = send_frame_set(connection, index, frame_set, is_last_frame)
        except socket.timeout:
            response = 'timeout'
            print(response)
            windows_timed_out.append(index)

        while RESPONSE_REJECTED in response:
            print(f'{response}')
            if protocol == GO_BACK_N:
                response = send_frame_set(connection, index, frame_set, is_last_frame)
            elif protocol == SELECTIVE_REJECT:
                frame_index = int(response[len(RESPONSE_REJECTED):])
                response = send_frame(connection, index, frame_index, frame_set[frame_index], is_last_frame)

        if response != 'timeout':
            if int(response[2:]) in windows_timed_out:
                windows_timed_out.remove(int(response[2:]))
                continue
        else:
            print(f'resending frames {index * window_size}:{(index + 1) * window_size}')
            while True:
                try:
                    response = send_frame_set(connection, index, frame_set, is_last_frame)
                    windows_timed_out.append(index)
                    break
                except socket.timeout:
                    continue
        print(f'{response}')


def send_frame_set(connection, window_index, frame_set, is_last_frame_set=False):
    for character in frame_set:
        connection.send(f'{FRAME_MESSAGE}{window_index}{character}'.encode(FORMAT))

    if is_last_frame_set:
        connection.send(f'{DISCONNECT_MESSAGE}{window_index} '.encode(FORMAT))

    return connection.recv(64).decode(FORMAT)


def send_frame_set_with_error(connection, window_index, frame_set, batch_size, is_last_frame_set=False):
    for index, character in enumerate(frame_set):
        connection.send(
            f'{FRAME_MESSAGE if index != max(batch_size - 2, 0) else "L"}{window_index}{character}'.encode(FORMAT)
        )

    if is_last_frame_set:
        connection.send(f'{DISCONNECT_MESSAGE}{window_index} '.encode(FORMAT))

    return connection.recv(64).decode(FORMAT)


def send_frame(connection, window_index, frame_index, frame, is_last_frame_set=False):
    print(f'resending frame {frame_index}')
    connection.send(f'{FRAME_MESSAGE}{window_index}{frame}'.encode(FORMAT))

    if is_last_frame_set:
        connection.send(f'{DISCONNECT_MESSAGE}{window_index} '.encode(FORMAT))

    return connection.recv(64).decode(FORMAT)


def set_window_size(connection):
    frames_per_window = int(input("Enter window size: "))
    connection.send(str(frames_per_window).encode(FORMAT))
    return frames_per_window


def partition(lst, size):
    for i in range(0, ceil(len(lst) / size)):
        yield lst[i * size:min(len(lst), (i + 1) * size)]


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
    client.connect(ADDRESS)
    client.send(SELECTIVE_REJECT.encode(FORMAT))
    window_size = set_window_size(client)
    send(client, window_size, 'hello this is the first message that i am sending.', SELECTIVE_REJECT)
    input("press enter to exit...")
