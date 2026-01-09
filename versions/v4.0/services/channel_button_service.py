"""
Channel Button Service - управление кнопками в постах канала.

Сервис для добавления кнопок к постам в Telegram каналах.
Генерирует ссылки на бота с отслеживанием нажатий.
"""

import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class ChannelButtonService:
    """Сервис для работы с кнопками в постах канала."""

    @staticmethod
    def parse_post_url(url: str) -> Optional[Tuple[str, int]]:
        """
        Парсит URL поста Telegram и извлекает channel и message_id.
        
        Поддерживаемые форматы:
        - https://t.me/channel_username/123
        - https://t.me/c/channel_id/123
        - https://t.me/channel_username/123?thread=456
        
        Args:
            url: URL поста Telegram
            
        Returns:
            Tuple (channel_id, message_id) или None если не удалось распарсить
        """
        try:
            # Убираем пробелы
            url = url.strip()
            
            # Проверяем базовый формат
            if not url.startswith('https://t.me/'):
                return None
            
            # Парсим URL
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return None
            
            # Формат: t.me/channel_username/123
            if path_parts[0] != 'c':
                channel = path_parts[0]
                try:
                    message_id = int(path_parts[1])
                except (ValueError, IndexError):
                    return None
                
                return (f"@{channel}", message_id)
            
            # Формат: t.me/c/channel_id/123
            if len(path_parts) < 3:
                return None
            
            try:
                channel_id = int(path_parts[1])
                message_id = int(path_parts[2])
            except (ValueError, IndexError):
                return None
            
            return (channel_id, message_id)
            
        except Exception as e:
            logger.error(f"Error parsing post URL: {e}")
            return None

    @staticmethod
    def generate_bot_link(bot_username: str, post_id: int = None) -> str:
        """
        Генерирует ссылку на бота с параметром для отслеживания нажатий.
        
        Args:
            bot_username: Имя бота (без @)
            post_id: ID поста (опционально, для аналитики)
        
        Returns:
            Ссылка на бота вида: https://t.me/bot_username?start=channel_button_123
        """
        # Убираем @ если есть
        if bot_username.startswith('@'):
            bot_username = bot_username[1:]
        
        # Формируем параметр
        if post_id:
            param = f"channel_button_{post_id}"
        else:
            param = "channel_button"
        
        return f"https://t.me/{bot_username}?start={param}"

    @staticmethod
    def create_button_keyboard(link: str, button_text: str) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с одной кнопкой.
        
        Args:
            link: Ссылка (на бота, файл, опрос и т.д.)
            button_text: Текст кнопки
        
        Returns:
            InlineKeyboardMarkup с кнопкой
        """
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, url=link)]
        ])
        return keyboard

    @staticmethod
    async def add_button_to_post(
        bot,
        channel_id: str,
        message_id: int,
        button_text: str,
        link: str,
        lead_magnet_type: str = "bot"
    ) -> bool:
        """
        Добавляет кнопку к существующему посту в канале.
        
        Args:
            bot: Экземпляр Telegram бота
            channel_id: ID канала (username или числовой ID)
            message_id: ID сообщения
            button_text: Текст кнопки
            link: Ссылка для кнопки (на бота или внешняя ссылка)
            lead_magnet_type: Тип лид-магнита ("bot" или "external")
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Создаем клавиатуру с кнопкой
            keyboard = ChannelButtonService.create_button_keyboard(link, button_text)
            
            # Редактируем пост, добавляя кнопку
            await bot.edit_message_reply_markup(
                chat_id=channel_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            
            logger.info(f"Button added to post {message_id} in channel {channel_id}, type: {lead_magnet_type}")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error adding button: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding button: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
