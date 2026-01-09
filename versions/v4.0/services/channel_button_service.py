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
from telegram.error import TelegramError, BadRequest, Forbidden

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
        
        Если пост создан другим пользователем/ботом и его нельзя отредактировать,
        отправляет новое сообщение с кнопкой под постом.
        
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
            
            # Пытаемся отредактировать пост, добавляя кнопку
            try:
                await bot.edit_message_reply_markup(
                    chat_id=channel_id,
                    message_id=message_id,
                    reply_markup=keyboard
                )
                logger.info(f"Button added to post {message_id} in channel {channel_id}, type: {lead_magnet_type}")
                return True
                
            except (BadRequest, Forbidden) as e:
                # Пост создан другим пользователем/ботом - нельзя редактировать
                # Отправляем новое сообщение с кнопкой под постом
                error_message = str(e).lower()
                if "message can't be edited" in error_message or "message is not modified" in error_message or "not enough rights" in error_message or "can't edit" in error_message:
                    logger.warning(f"Cannot edit post {message_id} (created by another user). Sending new message with button.")
                    
                    try:
                        # Отправляем новое сообщение с кнопкой, привязанное к исходному посту
                        sent_message = await bot.send_message(
                            chat_id=channel_id,
                            text=f"🔘 {button_text}",
                            reply_markup=keyboard,
                            reply_to_message_id=message_id
                        )
                        
                        logger.info(f"New message with button sent under post {message_id} in channel {channel_id}, new message_id: {sent_message.message_id}")
                        return True
                        
                    except Exception as send_error:
                        logger.error(f"Error sending new message with button: {send_error}")
                        # Если не получилось отправить с reply_to, пробуем без него
                        try:
                            sent_message = await bot.send_message(
                                chat_id=channel_id,
                                text=f"🔘 {button_text}",
                                reply_markup=keyboard
                            )
                            logger.info(f"New message with button sent in channel {channel_id}, new message_id: {sent_message.message_id}")
                            return True
                        except Exception as send_error2:
                            logger.error(f"Error sending message without reply: {send_error2}")
                            return False
                else:
                    # Другая ошибка - пробрасываем дальше
                    raise
                    
        except TelegramError as e:
            logger.error(f"Telegram error adding button: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding button: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    @staticmethod
    async def publish_post_with_button(
        bot,
        channel_id: str,
        post_content: str,
        button_text: str,
        link: str,
        photo: Optional[bytes] = None,
        photo_file_id: Optional[str] = None,
        lead_magnet_type: str = "bot"
    ) -> Optional[int]:
        """
        Публикует новый пост в канале с кнопкой.
        
        Args:
            bot: Экземпляр Telegram бота
            channel_id: ID канала (username или числовой ID)
            post_content: Текст поста
            button_text: Текст кнопки
            link: Ссылка для кнопки
            photo: Байты изображения (опционально)
            photo_file_id: File ID изображения (опционально)
            lead_magnet_type: Тип лид-магнита ("bot" или "external")
        
        Returns:
            message_id опубликованного поста или None если ошибка
        """
        try:
            # Создаем клавиатуру с кнопкой
            keyboard = ChannelButtonService.create_button_keyboard(link, button_text)
            
            # Публикуем пост
            if photo_file_id:
                # Используем file_id если есть
                sent_message = await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo_file_id,
                    caption=post_content,
                    reply_markup=keyboard
                )
            elif photo:
                # Используем байты изображения
                sent_message = await bot.send_photo(
                    chat_id=channel_id,
                    photo=photo,
                    caption=post_content,
                    reply_markup=keyboard
                )
            else:
                # Только текст
                sent_message = await bot.send_message(
                    chat_id=channel_id,
                    text=post_content,
                    reply_markup=keyboard
                )
            
            logger.info(f"Post published in channel {channel_id} with button, message_id: {sent_message.message_id}, type: {lead_magnet_type}")
            return sent_message.message_id
            
        except TelegramError as e:
            logger.error(f"Telegram error publishing post: {e}")
            return None
        except Exception as e:
            logger.error(f"Error publishing post: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
