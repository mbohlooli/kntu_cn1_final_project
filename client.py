import socket
import threading
from math import ceil
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from server import ADDRESS, FORMAT, FRAME_MESSAGE, DISCONNECT_MESSAGE, RESPONSE_REJECTED, GO_BACK_N, SELECTIVE_REJECT
from gui_config import *


def start_client(connection, sender_messages_text, window_size_ref, timeout_ref, protocol_ref):
    selected_protocol = GO_BACK_N if protocol_ref.get() == 1 else SELECTIVE_REJECT

    connection.connect(ADDRESS)
    connection.send(selected_protocol.encode(FORMAT))
    connection.send(str(window_size_ref.get()).encode(FORMAT))
    send_thread = threading.Thread(
        target=send,
        args=(
            connection,
            window_size_ref.get(),
            'hello this is the first message that i am sending.',
            sender_messages_text,
            timeout_ref.get(),
            selected_protocol
        )
    )
    send_thread.start()


def send(connection, batch_size, message, text_box, timeout, protocol=GO_BACK_N):
    if batch_size <= 0:
        set_text(text_box, "**ERROR** window size must be greater than or equal to zero.")
        return

    if protocol not in {GO_BACK_N, SELECTIVE_REJECT}:
        raise ValueError(f'Unknown protocol {protocol}')

    windows_timed_out = []
    connection.settimeout(timeout)
    for index, frame_set in enumerate(partition(message, batch_size)):
        set_text(text_box, f'[Sending] {frame_set}')

        is_last_frame = index == ceil(len(message) / batch_size) - 1

        try:
            if index == 2:
                response = send_frame_set_with_error(connection, index, frame_set, batch_size, is_last_frame)
            else:
                response = send_frame_set(connection, index, frame_set, is_last_frame)
        except socket.timeout:
            response = 'timeout'
            set_text(text_box, f'[TimeOut] {response}')
            windows_timed_out.append(index)

        while RESPONSE_REJECTED in response:
            set_text(text_box, f'[ACK] {response}')
            if protocol == GO_BACK_N:
                response = send_frame_set(connection, index, frame_set, is_last_frame)
                set_text(text_box, f'[Resending] {index * batch_size}:{(index + 1) * batch_size}')
            elif protocol == SELECTIVE_REJECT:
                frame_index = int(response[len(RESPONSE_REJECTED):])
                set_text(text_box, f'[Resending] {frame_index}')
                response = send_frame(connection, index, frame_set[frame_index], is_last_frame)

        if response != 'timeout':
            if int(response[2:]) in windows_timed_out:
                windows_timed_out.remove(int(response[2:]))
                continue
        else:
            set_text(text_box, f'[Resending] {index * batch_size}:{(index + 1) * batch_size}')
            while True:
                try:
                    response = send_frame_set(connection, index, frame_set, is_last_frame)
                    windows_timed_out.append(index)
                    break
                except socket.timeout:
                    continue

        set_text(text_box, f'[ACK] {response}')


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


def send_frame(connection, window_index, frame, is_last_frame_set=False):
    connection.send(f'{FRAME_MESSAGE}{window_index}{frame}'.encode(FORMAT))

    if is_last_frame_set:
        connection.send(f'{DISCONNECT_MESSAGE}{window_index} '.encode(FORMAT))

    return connection.recv(64).decode(FORMAT)


def partition(lst, size):
    for i in range(0, ceil(len(lst) / size)):
        yield lst[i * size:min(len(lst), (i + 1) * size)]


def set_text(textbox, text):
    textbox.config(state='normal')
    textbox.insert(tk.END, f'{text}\n')
    textbox.config(state='disabled')


def init_messages_textbox(root_window):
    tk.Label(
        root_window, text="Sender Messages:", font=LABEL_FONT, bg=BACKGROUND
    ).grid(row=5, column=0, pady=10, padx=10, sticky='w')
    sender_messages_text = ScrolledText(root_window, state='disabled', wrap=tk.WORD, width=40, height=15,
                                        bg=TEXT_BACKGROUND)
    sender_messages_text.grid(row=5, column=1, columnspan=2, pady=10, padx=10, sticky='w')
    return sender_messages_text


def init_window_size_input(root_window, window_size_ref):
    (tk.Label(root_window, text="Enter the window size:", font=LABEL_FONT, bg=BACKGROUND)
     .grid(row=0, column=0, pady=10, padx=10, sticky='e'))
    window_size_entry = tk.Entry(root_window, textvariable=window_size_ref, width=50, justify='center', font=TEXT_FONT)
    window_size_entry.grid(row=0, column=1, pady=10, padx=10)
    window_size_entry.config({"background": '#FCCA6E'})
    window_size_entry.delete(0, tk.END)
    window_size_entry.insert(0, '6')
    return window_size_entry


def init_protocol_buttons(root_window, protocol_ref):
    go_back_n_radio = tk.Radiobutton(
        root_window, text="Go-Back-N", variable=protocol_ref, value=1, font=TEXT_FONT_BOLD, bg='#EFA00B'
    )
    go_back_n_radio.grid(row=3, column=1, pady=10, padx=10, sticky='w')
    go_back_n_radio.select()

    selective_reject_radio = tk.Radiobutton(
        root_window, text="Selective-Reject", variable=protocol_ref, value=2, font=TEXT_FONT_BOLD, bg='#EFA00B'
    )
    selective_reject_radio.grid(row=3, column=1, pady=10, padx=10, sticky='e')

    return go_back_n_radio, selective_reject_radio


def init_timeout_input(root_window, timeout_ref):
    (tk.Label(root_window, text="Enter the timeout in seconds:", font=LABEL_FONT, bg=BACKGROUND)
     .grid(row=1, column=0, pady=10, padx=10, sticky='e'))
    timeout_entry = tk.Entry(root_window, textvariable=timeout_ref, width=50, justify='center', font=TEXT_FONT)
    timeout_entry.grid(row=1, column=1, pady=10, padx=10)
    timeout_entry.config({"background": '#FCCA6E'})
    timeout_entry.delete(0, tk.END)
    timeout_entry.insert(0, '0.5')
    return timeout_entry


def init_start_button(root_window, sender_messages_text, window_size_ref, timeout_ref, protocol_ref, connection,
                      go_back_n_radio, selective_reject_radio, window_size_input, timeout_input):
    start_sender_button = tk.Button(
        root_window,
        text="Start Sending",
        command=lambda: [
            start_client(connection, sender_messages_text, window_size_ref, timeout_ref, protocol_ref),
            start_sender_button.configure(state=tk.DISABLED),
            go_back_n_radio.configure(state=tk.DISABLED),
            selective_reject_radio.configure(state=tk.DISABLED),
            window_size_input.configure(state=tk.DISABLED),
            timeout_input.configure(state=tk.DISABLED)
        ],
        bg=BACKGROUND,
        font=LABEL_FONT
    )
    start_sender_button.grid(row=4, column=1, columnspan=3, pady=10, padx=10)
    return start_sender_button


if __name__ == '__main__':
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    root = tk.Tk()
    window_size_var = tk.IntVar()
    timeout_var = tk.DoubleVar()
    message_var = tk.StringVar()
    protocol_var = tk.IntVar()

    root.title("Protocol Simulator Client")
    root.configure(bg=BACKGROUND)

    sender_messages = init_messages_textbox(root)
    window_size = init_window_size_input(root, window_size_var)
    go_back_n, selective_reject = init_protocol_buttons(root, protocol_var)
    timeout_field = init_timeout_input(root, timeout_var)
    init_start_button(root, sender_messages, window_size_var, timeout_var, protocol_var, client, go_back_n,
                      selective_reject, window_size, timeout_field)

    root.mainloop()
    client.close()
