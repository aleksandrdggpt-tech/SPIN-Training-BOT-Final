"""
HTTP сервер для health check.
Предоставляет эндпоинт /health для мониторинга состояния приложения.
"""

import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для health check."""

    def do_GET(self):
        """Обработка GET запросов."""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Отключаем логирование HTTP запросов."""
        pass


def find_free_port() -> int:
    """Находит свободный порт для запуска сервера."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_health_server(port: int) -> None:
    """Запускает health check сервер в отдельном потоке."""
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Health check server запущен на порту {port}")
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.warning(f"Порт {port} уже занят, пытаемся найти свободный порт...")
            try:
                free_port = find_free_port()
                server = HTTPServer(('0.0.0.0', free_port), HealthCheckHandler)
                logger.info(f"Health check server запущен на свободном порту {free_port}")
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
            except Exception as e2:
                logger.error(f"Не удалось запустить health check сервер: {e2}")
                # Не прерываем работу бота из-за health check
        else:
            logger.error(f"Ошибка запуска health check сервера: {e}")
            # Не прерываем работу бота из-за health check
    except Exception as e:
        logger.error(f"Ошибка запуска health check сервера: {e}")
        # Не прерываем работу бота из-за health check
