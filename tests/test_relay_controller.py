import socket
from unittest import mock

from relay_controller import send_tcp_command

def test_send_tcp_command():
    sock_mock = mock.MagicMock()
    conn_mock = mock.MagicMock()
    conn_mock.__enter__.return_value = sock_mock

    with mock.patch('socket.create_connection', return_value=conn_mock) as create_conn:
        send_tcp_command('10.0.0.1', 3, True)

    create_conn.assert_called_with(('10.0.0.1', 17123), timeout=2)
    sock_mock.sendall.assert_called_once_with(b'SR 3 on\n')