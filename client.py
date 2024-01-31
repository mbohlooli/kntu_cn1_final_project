import socket
from math import ceil

from server import ADDRESS, FORMAT, FRAME_MESSAGE, DISCONNECT_MESSAGE


def send(connection, batch_size, message):
    for index, frame_set in enumerate(partition(message, batch_size)):
        print(frame_set)

        for character in frame_set:
            connection.send(f'{FRAME_MESSAGE}{character}'.encode(FORMAT))

        if index == ceil(len(message) / batch_size) - 1:
            connection.send(f'{DISCONNECT_MESSAGE} '.encode(FORMAT))

        print(connection.recv(64).decode(FORMAT))


def set_window_size(connection):
    frames_per_window = int(input("Enter window size: "))
    connection.send(str(frames_per_window).encode(FORMAT))
    return frames_per_window


def partition(lst, size):
    for i in range(0, ceil(len(lst) / size)):
        yield lst[i * size:min(len(lst), (i + 1) * size)]


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
    client.connect(ADDRESS)
    window_size = set_window_size(client)
    send(client, window_size, 'hello this is the first message that i am sending.')
