import socket
import threading
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from gui_config import *

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


def start_server(connection, server_messages_textbox):
    connection.bind(ADDRESS)
    try:
        start(connection, server_messages_textbox)
    except OSError:
        pass


def handle_client(connection, address, protocol, server_messages_textbox):
    set_text(server_messages_textbox, f'Connected by {address} with protocol {protocol}')

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

        set_text(server_messages_textbox, f'[Received Frame] {message_type}-{window_index}-{message_data}')

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
                        transfer_from_buffer_to_memory(
                            connection, window_index, buffer, result, server_messages_textbox)
            elif message_type == DISCONNECT_MESSAGE:
                if len(buffer) != 0:
                    if rejected:
                        rejected = False
                        buffer.clear()
                        connection.send(f'{RESPONSE_REJECTED}{window_index}'.encode(FORMAT))
                    else:
                        windows_received.add(window_index)
                        transfer_from_buffer_to_memory(
                            connection, window_index, buffer, result, server_messages_textbox)
                connected = False
                connection.close()
                set_text(server_messages_textbox, f'Disconnected from {address}')
                break
            else:
                set_text(server_messages_textbox, f'Unknown message type: {message_type}')
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
                    transfer_from_buffer_to_memory(connection, window_index, buffer, result, server_messages_textbox)
            elif message_type == DISCONNECT_MESSAGE:
                if rejected_index != -1:
                    buffer[rejected_index] = message_data
                    rejected_index = -1
                if len(buffer) != 0:
                    windows_received.add(window_index)
                    transfer_from_buffer_to_memory(connection, window_index, buffer, result, server_messages_textbox)
                connected = False
                connection.close()
                set_text(server_messages_textbox, f'Disconnected from {address}')
                break
            else:
                set_text(server_messages_textbox, f'Unknown message type: {message_type}')
                rejected_index = len(buffer)
                connection.send(f'{RESPONSE_REJECTED}{rejected_index}'.encode(FORMAT))
                buffer.append(message_data)
                if len(buffer) == window_size:
                    buffer.clear()
        else:
            set_text(server_messages_textbox, f'Unknown protocol: {protocol}')
            connected = False
            connection.close()


def transfer_from_buffer_to_memory(connection, window_index, buffer, memory, server_messages_textbox):
    memory.extend(buffer)
    buffer.clear()
    set_text(server_messages_textbox, f'[Received] "{"".join(memory)}"')
    connection.send(f'{RESPONSE_READY_TO_RECEIVE}{window_index}'.encode(FORMAT))


def start(host, server_messages_textbox):
    host.listen()
    set_text(server_messages_textbox, 'Server started')
    while True:
        connection, address = host.accept()
        protocol = connection.recv(len(GO_BACK_N)).decode(FORMAT)
        thread = threading.Thread(target=handle_client, args=(connection, address, protocol, server_messages_textbox))
        thread.start()


def init_messages_textbox(root_window):
    tk.Label(
        root_window, text="Sever Messages:", font=LABEL_FONT, bg=BACKGROUND
    ).grid(row=5, column=0, pady=10, padx=10, sticky='w')
    sender_messages_text = ScrolledText(root_window, state='disabled', wrap=tk.WORD, width=40, height=15,
                                        bg=TEXT_BACKGROUND)
    sender_messages_text.grid(row=5, column=1, columnspan=2, pady=10, padx=10, sticky='w')
    return sender_messages_text


def set_text(textbox, text):
    textbox.config(state='normal')
    textbox.insert(tk.END, f'{text}\n')
    textbox.config(state='disabled')


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    root = tk.Tk()

    root.title("Protocol Simulator Server")
    root.configure(bg=BACKGROUND)

    server_messages = init_messages_textbox(root)

    start_server_thread = threading.Thread(target=start_server, args=(server, server_messages))
    start_server_thread.start()

    root.mainloop()
    try:
        server.close()
    finally:
        pass
