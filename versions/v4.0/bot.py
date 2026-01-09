"""
SPIN Training Bot - Рефакторенная версия v3.0
Содержит только обработчики команд Telegram и координацию сервисов.
"""

# Загрузка переменных окружения из .env файла ПЕРВОЙ СТРОКОЙ
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import time
import os
import sys
import signal
import atexit
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import Conflict, NetworkError

# Импорты сервисов
from config import Config
from services.llm_service import LLMService
from services.achievement_service import AchievementService
from services.spin_training_service import SpinTrainingService
from services.database_service import DatabaseService
from infrastructure.health_server import start_health_server
from database import init_db, close_db  # Инициализация БД

# Импорты движка
from engine.scenario_loader import ScenarioLoader, ScenarioValidationError
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator

# Импорты модулей
from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания состояния приложения
app_instance = None

# PID file configuration (optional, for Railway deployment)
WRITE_PID_FILE = os.getenv('WRITE_PID_FILE', '0') == '1'
if WRITE_PID_FILE:
    pid_file = Path("/tmp/bot.pid")  # Use /tmp in containers
else:
    pid_file = None

# Инициализация конфигурации
config = Config()

# Инициализация сервисов
llm_service = LLMService()
db_service = DatabaseService(bot_name="spin_bot")  # PostgreSQL БД хранилище
achievement_service = AchievementService()

# Инициализация движка
scenario_loader = ScenarioLoader()
question_analyzer = QuestionAnalyzer()
report_generator = ReportGenerator()

# Инициализация модуля активного слушания
active_listening_config = ActiveListeningConfig(
    enabled=True,
    use_llm=True,
    bonus_points=5,
    emoji="👂",
    language="ru"
)
active_listening_detector = ActiveListeningDetector(active_listening_config)

# Загрузка сценария
try:
    loaded_scenario = scenario_loader.load_scenario(config.SCENARIO_PATH)
    scenario_config = loaded_scenario.config
    case_generator = CaseGenerator(scenario_config['case_variants'])
    logger.info("Сценарий загружен успешно")
except (FileNotFoundError, ScenarioValidationError) as e:
    logger.error(f"Ошибка загрузки сценария: {e}")
    raise

# Инициализация SPIN Training Service
# Создаем адаптер UserServiceDB для обратной совместимости с training_service
from services.user_service_db import UserServiceDB
user_service_adapter = UserServiceDB(bot_name="spin_bot")

training_service = SpinTrainingService(
    user_service=user_service_adapter,  # Адаптер для обратной совместимости
    llm_service=llm_service,
    achievement_service=achievement_service,
    question_analyzer=question_analyzer,
    report_generator=report_generator,
    case_generator=case_generator,
    scenario_loader=scenario_loader,
    active_listening_detector=active_listening_detector
)


# ==================== УПРАВЛЕНИЕ ПРОЦЕССОМ ====================

def create_pid_file():
    """Создает PID файл для отслеживания процесса (опционально, только если WRITE_PID_FILE=1)."""
    if not WRITE_PID_FILE or pid_file is None:
        return
    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file created: {pid_file}")
    except Exception as e:
        logger.error(f"Error creating PID file: {e}")


def remove_pid_file():
    """Удаляет PID файл при завершении работы (опционально)."""
    if not WRITE_PID_FILE or pid_file is None:
        return
    try:
        if pid_file.exists():
            pid_file.unlink()
            logger.info("PID file removed")
    except Exception as e:
        logger.error(f"Error removing PID file: {e}")


def check_existing_process():
    """Проверяет, не запущен ли уже экземпляр бота (опционально, только если WRITE_PID_FILE=1)."""
    if not WRITE_PID_FILE or pid_file is None or not pid_file.exists():
        return False

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Проверяем, существует ли процесс с этим PID
        try:
            os.kill(pid, 0)  # Отправляем сигнал 0 для проверки существования
            logger.warning(f"Bot already running with PID {pid}")
            return True
        except OSError:
            # Процесс не существует, удаляем устаревший PID файл
            pid_file.unlink()
            logger.info("Removed stale PID file")
            return False
    except (ValueError, FileNotFoundError):
        # PID файл поврежден или удален
        return False


# Старый signal_handler закомментирован, так как конфликтует с asyncio.run()
# asyncio.run() сам правильно обрабатывает KeyboardInterrupt (Ctrl+C)
# def signal_handler(signum, frame):
#     """Обработчик сигналов для корректного завершения работы."""
#     logger.info(f"Получен сигнал {signum}, завершаю работу...")
#     user_service.save_now()
#     logger.info("✅ Данные пользователей сохранены")
#     remove_pid_file()
#     if app_instance:
#         app_instance.stop()

# def setup_signal_handlers():
#     """Настраивает обработчики сигналов."""
#     signal.signal(signal.SIGINT, signal_handler)
#     signal.signal(signal.SIGTERM, signal_handler)
#     atexit.register(remove_pid_file)

# Регистрируем только cleanup при выходе
atexit.register(remove_pid_file)


# ==================== ОБРАБОТЧИКИ КОМАНД ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start - отправляет приветствие и проверяет подписку"""
    t0 = time.perf_counter()
    user_id = update.effective_user.id
    telegram_id = update.effective_user.id
    
    # Обработка deep link параметров (для отслеживания нажатий на кнопку в канале)
    start_param = None
    if context.args and len(context.args) > 0:
        start_param = context.args[0]
        logger.info(f"🚀 Команда /start вызвана пользователем {telegram_id} с параметром: {start_param}")
        
        # Если параметр начинается с "channel_" - это нажатие на кнопку в канале
        if start_param.startswith("channel_"):
            try:
                from database import get_session, ChannelButtonClick, User
                async with get_session() as session:
                    # Получаем или создаем пользователя
                    from modules.payments.subscription import get_or_create_user
                    user = await get_or_create_user(
                        telegram_id,
                        session,
                        username=update.effective_user.username,
                        first_name=update.effective_user.first_name
                    )
                    
                    # Пытаемся найти button_id из параметра (формат: channel_button_123)
                    button_id = None
                    post_id = None
                    button_link = None
                    button_lead_magnet_type = None
                    if start_param.startswith("channel_button_"):
                        try:
                            post_id = int(start_param.replace("channel_button_", ""))
                            # Ищем кнопку по message_id
                            from database import ChannelButton
                            from sqlalchemy import select
                            button_result = await session.execute(
                                select(ChannelButton).where(ChannelButton.message_id == post_id)
                            )
                            found_button = button_result.scalar_one_or_none()
                            if found_button:
                                button_id = found_button.id
                                button_link = found_button.link
                                button_lead_magnet_type = found_button.lead_magnet_type
                                # Сохраняем информацию о кнопке в context для последующей выдачи ссылки
                                context.user_data['channel_button_id'] = button_id
                                context.user_data['channel_button_link'] = button_link
                                context.user_data['channel_button_type'] = button_lead_magnet_type
                                logger.info(f"✅ Сохранена информация о кнопке: button_id={button_id}, link={button_link}, type={button_lead_magnet_type}")
                        except (ValueError, Exception) as e:
                            logger.debug(f"Could not extract button_id from param: {e}")
                    
                    # Сохраняем нажатие на кнопку
                    click = ChannelButtonClick(
                        user_id=user.id,
                        telegram_id=telegram_id,
                        button_id=button_id,
                        source=start_param,
                        post_id=post_id if 'post_id' in locals() else None
                    )
                    session.add(click)
                    await session.commit()
                    logger.info(f"✅ Зафиксировано нажатие на кнопку канала: {start_param} от пользователя {telegram_id}, button_id: {button_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка при сохранении нажатия на кнопку: {e}")
    else:
        logger.info(f"🚀 Команда /start вызвана пользователем {telegram_id}")
    
    # Импорты для работы с БД и бесплатным доступом
    from modules.payments.messages import WELCOME_SALES
    from modules.payments.keyboards import get_start_menu_keyboard, get_start_training_keyboard
    from modules.payments.subscription import (
        get_or_create_user,
        check_access
    )
    from database import get_session

    # Проверка доступа через payment модуль (только бесплатный доступ через подписку)
    try:
        logger.info("🔵 Checking user access...")

        # Работаем с БД напрямую через async get_session()
        async with get_session() as session:
            # Создаём или получаем пользователя
            user = await get_or_create_user(
                telegram_id,
                session,
                username=update.effective_user.username,
                first_name=update.effective_user.first_name
            )
            logger.info(f"🔵 User {user_id} found/created: {user.id}")

            # Проверяем доступ (БЕЗ автоматической выдачи бонуса за подписку)
            # Бонус за подписку на канал выдается только когда пользователь явно нажимает кнопку "Я подписался"
            access_info = await check_access(telegram_id, session)

            # Детальное логирование для отладки
            logger.info(f"🔵 Access check result: {access_info}")
    except Exception as e:
        logger.error(f"❌ Error checking access: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        # В случае ошибки считаем, что доступа нет
        access_info = {'has_access': False, 'access_type': None, 'details': {}}

    try:
        # Сбрасываем сессию тренировки (начинаем заново)
        # Получаем текущую сессию
        user_data = await db_service.get_user_session(
            telegram_id=telegram_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name
        )

        # Сбрасываем сессию
        user_data['session'] = {
            'question_count': 0,
            'clarity_level': 0,
            'chat_state': 'waiting_start',
            'per_type_counts': {'situation': 0, 'problem': 0, 'implication': 0, 'need_payoff': 0},
            'case_data': None,
            'last_client_response': '',
            'active_listening_detected': False,
            'feedback_in_progress': False,
            'last_feedback_ts': 0
        }

        # Сохраняем сброшенную сессию
        await db_service.save_session(
            telegram_id=telegram_id,
            session_data=user_data['session'],
            stats_data=user_data['stats']
        )

        logger.info("🔵 Session reset successfully")

        # Формируем приветственное сообщение
        logger.info("🔵 Sending welcome message...")

        # Формируем стартовое сообщение
        # Базовое приветствие
        welcome_message = WELCOME_SALES

        # Добавляем информацию о статусе пользователя
        status_message = ""
        if access_info['has_access']:
            if access_info['access_type'] == 'free_trainings':
                trainings_left = access_info['details'].get('trainings_left', 0)
                source = access_info['details'].get('source', 'unknown')
                status_message = f"\n\n📊 **Ваш статус:**\n🎁 Бесплатных тренировок: {trainings_left} (источник: {source})"
            elif access_info['access_type'] == 'subscription':
                status_message = "\n\n🔑 У вас есть активная подписка."
        else:
            status_message = "\n\n🔑 У вас нет активной подписки."

        # Объединяем сообщения
        full_message = welcome_message + status_message

        # Проверяем, пришел ли пользователь через кнопку канала
        channel_button_link = context.user_data.get('channel_button_link')
        channel_button_type = context.user_data.get('channel_button_type')
        
        if channel_button_link:
            # Пользователь пришел через кнопку канала - проверяем подписку
            from modules.payments.subscription import check_channel_subscription
            from modules.payments.messages import FREE_ACCESS_CHANNEL
            from modules.payments.keyboards import get_free_access_keyboard
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            # Проверяем подписку сразу
            try:
                is_subscribed = await check_channel_subscription(context.bot, telegram_id)
                logger.info(f"🔵 User {telegram_id} subscription status: {is_subscribed}")
                
                if is_subscribed:
                    # Пользователь подписан - сразу выдаем ссылку
                    if channel_button_type == "external":
                        # Внешняя ссылка - показываем кнопку со ссылкой
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Получить доступ", url=channel_button_link)]
                        ])
                        message = f"""
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

Ваша ссылка готова! Нажмите на кнопку ниже, чтобы получить доступ.
"""
                    else:
                        # Доступ к боту - показываем стандартное меню
                        if access_info['has_access']:
                            keyboard = get_start_training_keyboard()
                            message = welcome_message + status_message + "\n\nНажмите кнопку ниже, чтобы начать тренировку:"
                        else:
                            keyboard = get_start_menu_keyboard()
                            message = welcome_message + status_message
                    
                    await update.message.reply_text(
                        message,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    # Очищаем данные о кнопке после выдачи ссылки
                    context.user_data.pop('channel_button_link', None)
                    context.user_data.pop('channel_button_type', None)
                    context.user_data.pop('channel_button_id', None)
                    logger.info(f"✅ Link issued immediately to subscribed user {telegram_id}: {channel_button_link}, type: {channel_button_type}")
                else:
                    # Пользователь не подписан - показываем диалог проверки подписки
                    await update.message.reply_text(
                        FREE_ACCESS_CHANNEL,
                        reply_markup=get_free_access_keyboard(),
                        parse_mode="Markdown"
                    )
                    logger.info(f"🔵 User came via channel button but not subscribed, showing subscription check. Link: {channel_button_link}, Type: {channel_button_type}")
            except Exception as e:
                logger.error(f"❌ Error checking subscription for channel button: {e}")
                # В случае ошибки показываем диалог проверки подписки
                await update.message.reply_text(
                    FREE_ACCESS_CHANNEL,
                    reply_markup=get_free_access_keyboard(),
                    parse_mode="Markdown"
                )
        else:
            # Обычный вход - показываем стандартное меню
            # Определяем клавиатуру
            if access_info['has_access']:
                # Если есть доступ - показываем кнопку "Начать тренировку"
                keyboard = get_start_training_keyboard()
            else:
                # Если доступа нет - показываем меню с "Бесплатный доступ" и "Как это работает"
                keyboard = get_start_menu_keyboard()

            await update.message.reply_text(
                full_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        logger.info("🔵 Message sent successfully")
        elapsed = int((time.perf_counter() - t0) * 1000)
        logger.info(f"⏱ /start handled in {elapsed} ms")
        logger.info("✅ /start завершён успешно")

    except Exception as e:
        logger.error(f"❌ Error in /start: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")

        # Отправляем сообщение об ошибке пользователю
        await update.message.reply_text(
            "❌ Произошла ошибка при запуске. Попробуйте позже или обратитесь в поддержку."
        )

    return None


async def start_training_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Начать тренировку' для пользователей с подпиской"""
    query = update.callback_query
    await query.answer("Запускаю новую тренировку...")

    user_id = query.from_user.id

    try:
        # Генерируем кейс и начинаем тренировку
        client_case = await training_service.start_training(user_id, scenario_config)

        # Если это сообщение с отчетом - отправляем новое сообщение с кейсом
        # Если это другое сообщение - редактируем его
        try:
            # Пытаемся отправить новое сообщение (лучше для UX)
            await query.message.reply_text(client_case)
            # Удаляем кнопку из старого сообщения (опционально)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass  # Игнорируем ошибку, если не удалось удалить кнопку
        except Exception:
            # Если не удалось отправить новое сообщение, редактируем старое
            await query.edit_message_text(client_case)

        logger.info(f"✅ Тренировка начата для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка генерации кейса: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await query.message.reply_text('Произошла ошибка при генерации кейса. Попробуйте ещё раз.')
        except Exception:
            await query.edit_message_text('Произошла ошибка при генерации кейса. Попробуйте ещё раз.')
    return None  # Явно возвращаем None для корректной работы event loop


async def scenario_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о текущем сценарии."""
    t0 = time.perf_counter()
    try:
        # Берём структурированный блок scenario_info из конфигурации и формируем текст сами
        s_info = scenario_config.get('scenario_info', {})
        name = s_info.get('name', 'Unknown')
        version = s_info.get('version', '')
        description = s_info.get('description', '')
        info_text = f"Сценарий: {name}\nВерсия: {version}\n\n{description}".strip()
        await update.message.reply_text(info_text)
    except Exception as e:
        logger.error(f"Ошибка получения информации о сценарии: {e}")
        await update.message.reply_text(scenario_loader.get_message('error_generic'))
    finally:
        logger.info(f"⏱ /scenario handled in {int((time.perf_counter()-t0)*1000)} ms")
    return None


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователя."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id

    user_data = await db_service.get_user_session(
        telegram_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    stats = user_data['stats']

    stats_text = f"""📊 ВАША СТАТИСТИКА:

🎯 Тренировок пройдено: {stats.get('total_trainings', 0)}
❓ Всего вопросов задано: {stats.get('total_questions', 0)}
🏆 Лучший результат: {stats.get('best_score', 0)} баллов
⭐ Текущий уровень: {stats.get('current_level', 1)}
💎 Опыт (XP): {stats.get('total_xp', 0)}

Используйте /rank для детальной информации о достижениях."""

    await update.message.reply_text(stats_text)
    logger.info(f"⏱ /stats handled in {int((time.perf_counter()-t0)*1000)} ms")
    return None


async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальную информацию о ранге и достижениях."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id

    user_data = await db_service.get_user_session(
        telegram_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    stats = user_data['stats']

    # Получаем информацию об уровне
    levels = scenario_config.get('ranking', {}).get('levels', [])
    current_level = stats.get('current_level', 1)
    level_data = next((l for l in levels if l.get('level') == current_level), levels[0] if levels else {})

    # Формируем сообщение о ранге
    rank_text = f"""⭐ ВАШ РАНГ:

{level_data.get('emoji', '')} Уровень {current_level}: {level_data.get('name', '')}
💎 Опыт (XP): {stats.get('total_xp', 0)}
📝 {level_data.get('description', '')}

🎖️ ДОСТИЖЕНИЯ:
"""

    # Добавляем информацию о достижениях
    achievements = scenario_config.get('achievements', {}).get('list', [])
    unlocked_achievements = stats.get('achievements_unlocked', [])

    for ach in achievements:
        if ach.get('id') in unlocked_achievements:
            rank_text += f"✅ {ach.get('emoji', '')} {ach.get('name', '')} - {ach.get('description', '')}\n"
        else:
            rank_text += f"🔒 {ach.get('emoji', '')} {ach.get('name', '')} - {ach.get('description', '')}\n"

    await update.message.reply_text(rank_text)
    logger.info(f"⏱ /rank handled in {int((time.perf_counter()-t0)*1000)} ms")
    return None


async def case_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о текущем кейсе."""
    t0 = time.perf_counter()
    user_id = update.effective_user.id

    user_data = await db_service.get_user_session(
        telegram_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    session = user_data['session']

    if not session.get('case_data'):
        await update.message.reply_text("Сначала начните тренировку командой /start")
        logger.info(f"⏱ /case handled in {int((time.perf_counter()-t0)*1000)} ms")
        return

    case_data = session['case_data']
    case_info = f"""📋 ИНФОРМАЦИЯ О КЕЙСЕ:

👤 Должность: {case_data['position']}
🏢 Компания: {case_data['company']['type']}
📦 Продукт: {case_data['product']['name']}
💰 Объём: {case_data['volume']}
🔄 Частота: {case_data.get('frequency', 'Не указано')}
📊 Поставщиков: {case_data.get('suppliers_count', 'Не указано')}
⚡ Срочность: {case_data.get('urgency', 'Не указано')}"""

    await update.message.reply_text(case_info)
    logger.info(f"⏱ /case handled in {int((time.perf_counter()-t0)*1000)} ms")


async def caseinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Алиас команды для информации о кейсе (/caseinfo)."""
    return await case_command(update, context)


# ===== ЗАКОММЕНТИРОВАНО: Админская команда для тестирования меню оплаты =====
# Раскомментировать когда нужно вернуть функционал оплаты:
# async def test_new_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Админская команда для показа стартового меню новых пользователей (не видна в /help)."""
#     from modules.payments.admin_handlers import is_admin
#     from modules.payments.messages import NEW_SPIN_WELCOME_TEXT, OFFER_NOTICE
#     from modules.payments.keyboards import get_payment_menu_keyboard
#
#     user_id = update.effective_user.id
#
#     # Проверка прав администратора
#     if not is_admin(user_id):
#         await update.message.reply_text("❌ Эта команда доступна только администраторам.")
#         return
#
#     logger.info(f"🔧 Админ {user_id} использует команду /test_new_user")
#
#     # Формируем приветственное сообщение как для нового пользователя
#     user_name = update.effective_user.first_name or ""
#     if user_name:
#         user_name = f", {user_name}"
#
#     message = NEW_SPIN_WELCOME_TEXT.format(
#         name=user_name,
#         offer_notice=OFFER_NOTICE
#     )
#
#     # Отправляем сообщение с меню оплаты (как для нового пользователя без доступа)
#     await update.message.reply_text(
#         message,
#         reply_markup=get_payment_menu_keyboard(),
#         parse_mode="Markdown"
#     )
#
#     logger.info(f"✅ Стартовое меню нового пользователя отправлено админу {user_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам бота."""
    t0 = time.perf_counter()
    help_text = """📖 ДОСТУПНЫЕ КОМАНДЫ:

🎯 Основные:
/start - Начать новую тренировку
/stats - Ваша общая статистика
/rank - Детальная информация о ранге и достижениях
/caseinfo - Информация о текущем кейсе

# 💳 Подписка и доступ: (ЗАКОММЕНТИРОВАНО)
# /payment - Купить подписку или получить бесплатный доступ
# /promo <код> - Активировать промокод

🔧 Дополнительные:
/author - Контакты автора и полезные ссылки
/help - Показать эту справку

💬 Команды в чате:
• "начать" или "старт" - начать тренировку
• "ДА" - получить обратную связь по последнему вопросу
• "завершить" - завершить тренировку и получить отчёт

🎯 Цель: Задавайте SPIN-вопросы клиенту, чтобы выявить его потребности и достичь целевой ясности!"""

    await update.message.reply_text(help_text)
    logger.info(f"⏱ /help handled in {int((time.perf_counter()-t0)*1000)} ms")
    return None


async def author_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Контакты автора и полезные ссылки."""
    t0 = time.perf_counter()
    text = (
        "Автор бота - Готальский Александр\n\n"
        "🚀 ПОЛЕЗНЫЙ КОНТЕНТ ПО ПРОДЖАМ И ИИ:\n"
        "вы сможете найти на канале Тактика Кутузова @TaktikaKutuzova  \n\n"
        "Хотите научиться работать с ИИ или вам нужна ИИ автоматизация для ускорения работы, пишите на @gotaleks"
    )
    await update.message.reply_text(text)
    logger.info(f"⏱ /author handled in {int((time.perf_counter()-t0)*1000)} ms")
    return None


async def validate_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка конфигурации на логические ошибки."""
    t0 = time.perf_counter()
    # Разрешаем только админам
    user_id = update.effective_user.id
    if config.ADMIN_USER_IDS and user_id not in config.ADMIN_USER_IDS:
        logger.warning(f"Пользователь {user_id} попытался вызвать /validate без прав")
        return
    await update.message.reply_text("🔍 Проверяю конфигурацию...")

    errors = []
    warnings = []

    # Проверка 1: У каждого типа компании есть совместимые продукты
    for company in case_generator.variants['companies']:
        compatible_products = [
            p for p in case_generator.variants['products']
            if company['type'] in p.get('compatible_companies', [])
        ]
        if not compatible_products:
            errors.append(f"❌ {company['type']}: нет совместимых продуктов!")

    # Проверка 2: У каждого размера есть должности (если задан positions_by_size)
    positions_by_size = case_generator.variants.get('positions_by_size', {})
    for size in case_generator.variants['company_sizes']:
        if positions_by_size and not positions_by_size.get(size):
            errors.append(f"❌ {size}: нет должностей!")

    # Формируем ответ
    if errors:
        response = "❌ ОШИБКИ КОНФИГУРАЦИИ:\n" + "\n".join(errors)
    elif warnings:
        response = "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n" + "\n".join(warnings) + "\n\n✅ Критических ошибок не найдено."
    else:
        response = "✅ Конфигурация корректна!"

    await update.message.reply_text(response)
    logger.info(f"⏱ /validate handled in {int((time.perf_counter()-t0)*1000)} ms")


# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    logger.info("=" * 80)
    logger.info("📝 handle_message ВЫЗВАН")
    logger.info(f"Message text: {update.message.text if update.message else 'NO MESSAGE'}")
    logger.info("=" * 80)

    t_msg = time.perf_counter()
    user_id = update.effective_user.id
    message_text = update.message.text
    rules = scenario_config['game_rules']

    # Проверка: если пользователь в ConversationHandler (создание промокода и т.д.)
    # то не обрабатываем сообщение здесь, пусть его обрабатывает ConversationHandler
    if 'promo_data' in context.user_data:
        logger.info(f"User {user_id} is in promocode creation flow, skipping handle_message")
        return

    # Проверка: если пользователь только что вводил промокод (даже если ConversationHandler завершился)
    # не показываем сообщение "Напишите начать для старта тренировки"
    if context.user_data.get('promocode_just_entered'):
        logger.info(f"User {user_id} just entered promocode, skipping handle_message")
        # Очищаем флаг после обработки
        context.user_data.pop('promocode_just_entered', None)
        return

    # ВАЖНО: ConversationHandler должен автоматически перехватывать сообщения
    # Если handle_message вызывается, значит ConversationHandler не перехватил сообщение
    # Это может означать, что:
    # 1. Пользователь не в состоянии conversation
    # 2. ConversationHandler не правильно настроен
    # 3. Порядок регистрации handlers неправильный
    #
    # Мы не можем проверить состояние conversation напрямую через context.user_data,
    # так как ConversationHandler управляет состоянием через свой внутренний механизм.
    # Поэтому мы полагаемся на то, что ConversationHandler перехватит сообщение автоматически.
    # Если handle_message вызывается, значит пользователь НЕ в состоянии conversation.
    logger.debug(f"handle_message вызван для пользователя {user_id} - ConversationHandler не перехватил сообщение")

    # Всегда показываем индикатор набора при получении вопроса пользователя
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Получаем данные пользователя
    user_data = await db_service.get_user_session(
        telegram_id=user_id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name
    )
    session = user_data['session']

    # Обработка запуска тренировки из состояния ожидания
    if session.get('chat_state') == 'waiting_start':
        if message_text.lower() in ['начать', 'старт']:
            try:
                t_op = time.perf_counter()
                client_case = await training_service.start_training(user_id, scenario_config)
                await update.message.reply_text(client_case)
                logger.info(f"⏱ start_training handled in {int((time.perf_counter()-t_op)*1000)} ms")
            except Exception as e:
                logger.error(f"Ошибка генерации кейса: {e}")
                await update.message.reply_text('Произошла ошибка при генерации кейса. Попробуйте ещё раз написать "начать".')
        else:
            await update.message.reply_text('Напишите "начать" для старта тренировки')
        logger.info(f"⏱ message (waiting_start) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return

    # Обработка запроса обратной связи
    if message_text.upper() == 'ДА':
        try:
            # Показываем пользователю, что идёт набор текста
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            # Антидублирование: если недавно запрашивали фидбек или он в процессе — отвечаем сразу
            cooldown_sec = 5
            now_ts = time.time()
            last_ts = float(session.get('last_feedback_ts') or 0)
            in_progress = bool(session.get('feedback_in_progress'))
            if in_progress or (now_ts - last_ts) < cooldown_sec:
                await update.message.reply_text('Фидбек уже генерируется, подождите пару секунд...')
                logger.info(f"Антидублирование фидбека: in_progress={in_progress} delta={now_ts - last_ts:.2f}s")
                return
            session['feedback_in_progress'] = True
            session['last_feedback_ts'] = now_ts
            t_op = time.perf_counter()
            # Попытка стриминга через GPT-5; при ошибке — синхронный путь
            sent = await update.message.reply_text('⏳ Пишу фидбек…')
            try:
                feedback_prompt = await training_service.build_feedback_prompt(user_id, scenario_config)
                chunks = []
                async for delta in llm_service.stream_feedback(feedback_prompt, 'Проанализируй ситуацию'):
                    chunks.append(delta)
                    # Обновляем сообщение батчами, чтобы не спамить Telegram API
                    if len(chunks) % 10 == 0:
                        await context.bot.edit_message_text(
                            chat_id=sent.chat_id,
                            message_id=sent.message_id,
                            text=''.join(chunks) or '…'
                        )
                # Если из стрима ничего не пришло — считаем это неуспехом и уходим в нестрим
                if not ''.join(chunks).strip():
                    raise RuntimeError('empty stream output')
                # Финальный апдейт
                final_text = ''.join(chunks).strip()
                await context.bot.edit_message_text(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    text=final_text
                )
            except Exception:
                # Резервный нестриминговый путь
                feedback = await training_service.get_feedback(user_id, scenario_config)
                await context.bot.edit_message_text(
                    chat_id=sent.chat_id,
                    message_id=sent.message_id,
                    text=feedback
                )
            logger.info(f"⏱ feedback handled in {int((time.perf_counter()-t_op)*1000)} ms")
        except Exception as e:
            logger.error(f"Ошибка получения обратной связи: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        finally:
            session['feedback_in_progress'] = False
            session['last_feedback_ts'] = time.time()
            # ВАЖНО: Сохраняем изменения в сессии
            await db_service.save_session(
                telegram_id=user_id,
                session_data=session,
                stats_data=user_data['stats']
            )
            logger.info(f"⏱ message (feedback) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return

    # Обработка завершения тренировки
    if message_text.lower() == 'завершить':
        try:
            t_op = time.perf_counter()
            report = await training_service.complete_training(user_id, scenario_config)
            # ===== ЗАКОММЕНТИРОВАНО: Кнопка "Начать новую тренировку" =====
            # Раскомментировать когда нужно вернуть функционал оплаты:
            # from modules.payments.keyboards import get_new_training_keyboard
            await update.message.reply_text(
                report,
                parse_mode=ParseMode.MARKDOWN
                # reply_markup=get_new_training_keyboard()
            )
            logger.info(f"⏱ complete_training handled in {int((time.perf_counter()-t_op)*1000)} ms")
        except Exception as e:
            logger.error(f"Ошибка завершения тренировки: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        finally:
            logger.info(f"⏱ message (finish) handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return

    # Проверка на короткие вопросы
    if len(message_text) <= rules.get('short_question_threshold', 5):
        await update.message.reply_text('Задайте более развернутый вопрос клиенту или напишите "начать" для новой тренировки.')
        return

    # Проверка максимального количества вопросов
    if session['question_count'] >= rules['max_questions']:
        try:
            report = await training_service.complete_training(user_id, scenario_config)
            # ===== ЗАКОММЕНТИРОВАНО: Кнопка "Начать новую тренировку" =====
            # Раскомментировать когда нужно вернуть функционал оплаты:
            # from modules.payments.keyboards import get_new_training_keyboard
            await update.message.reply_text(
                report,
                parse_mode=ParseMode.MARKDOWN
                # reply_markup=get_new_training_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка завершения тренировки: {e}")
            await update.message.reply_text(scenario_loader.get_message('error_generic'))
        return

    # Обработка вопроса пользователя
    try:
        # Покажем индикатор набора перед генерацией первого ответа клиента
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        t_op = time.perf_counter()
        response_message = await training_service.process_question(user_id, message_text, scenario_config)
        logger.info(f"⏱ process_question handled in {int((time.perf_counter()-t_op)*1000)} ms")

        # Проверяем условия завершения после обработки вопроса
        is_complete, completion_reason = training_service.check_training_completion(user_id, scenario_config)

        if is_complete:
            if completion_reason == "clarity_reached":
                await update.message.reply_text(response_message)
                await update.message.reply_text(
                    scenario_loader.get_message('clarity_reached', clarity=session['clarity_level'])
                )
                # После достижения целевой ясности также показываем отчет с кнопкой
                try:
                    report = await training_service.complete_training(user_id, scenario_config)
                    # ===== ЗАКОММЕНТИРОВАНО: Кнопка "Начать новую тренировку" =====
                    # Раскомментировать когда нужно вернуть функционал оплаты:
                    # from modules.payments.keyboards import get_new_training_keyboard
                    await update.message.reply_text(
                        report,
                        parse_mode=ParseMode.MARKDOWN
                        # reply_markup=get_new_training_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Ошибка завершения тренировки: {e}")
                    await update.message.reply_text(scenario_loader.get_message('error_generic'))
            elif completion_reason == "max_questions":
                try:
                    report = await training_service.complete_training(user_id, scenario_config)
                    # ===== ЗАКОММЕНТИРОВАНО: Кнопка "Начать новую тренировку" =====
                    # Раскомментировать когда нужно вернуть функционал оплаты:
                    # from modules.payments.keyboards import get_new_training_keyboard
                    await update.message.reply_text(
                        report,
                        parse_mode=ParseMode.MARKDOWN
                        # reply_markup=get_new_training_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Ошибка завершения тренировки: {e}")
                    await update.message.reply_text(scenario_loader.get_message('error_generic'))
        else:
            await update.message.reply_text(response_message)

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text(scenario_loader.get_message('error_generic'))
    finally:
        logger.info(f"⏱ message handled in {int((time.perf_counter()-t_msg)*1000)} ms")
        return None  # Явно возвращаем None


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

async def initialize_database():
    """Initialize database asynchronously."""
    logger.info("🔄 Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")


async def cleanup_resources():
    """Cleanup resources on shutdown."""
    # Грейсфул закрытие HTTP клиентов LLMService
    try:
        await llm_service.aclose()
        logger.info("✅ LLM service closed")
    except Exception as e:
        logger.error(f"Error closing LLM service: {e}")

    # Закрытие базы данных
    try:
        logger.info("🔄 Closing database...")
        await close_db()
        logger.info("✅ Database closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def main():
    """Главная функция приложения."""
    logger.info("=" * 80)
    logger.info("🚀 MAIN() STARTED")
    logger.info("=" * 80)

    global app_instance

    # Проверка на дублирование процессов (опционально)
    if check_existing_process():
        print("ERROR: Bot already running! Stop previous instance before starting new one.")
        if WRITE_PID_FILE and pid_file:
            print(f"Use command: kill $(cat {pid_file})")
        return

    # Создание PID файла
    create_pid_file()

    # Проверка обязательных переменных окружения
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in environment variables!")
        print("ERROR: BOT_TOKEN is required")
        print("Set BOT_TOKEN in environment variables or .env file")
        sys.exit(1)

    # Проверка DATABASE_URL (уже проверяется в database.py при импорте)
    # Если DATABASE_URL не установлен и DEV_MODE=0, database.py выбросит ValueError
    # Проверка происходит автоматически при импорте модуля database
    try:
        from database.database import DATABASE_URL
        if not DATABASE_URL:
            logger.critical("DATABASE_URL is not set!")
            print("ERROR: DATABASE_URL is required")
            print("Set DATABASE_URL in environment variables or enable DEV_MODE=1 for local SQLite")
            sys.exit(1)
    except ValueError as e:
        # DATABASE_URL не установлен и DEV_MODE=0 - ошибка уже залогирована в database.py
        logger.critical(f"DATABASE_URL validation failed: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)

    logger.info("Required environment variables: BOT_TOKEN, DATABASE_URL")

    # Валидация конфигурации
    try:
        config.validate()
        config.print_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"ERROR: Configuration error: {e}")
        print("Make sure BOT_TOKEN and at least one API key are set in environment variables")
        remove_pid_file()
        return

    # Создание event loop для инициализации БД и запуска бота
    # Используем один loop для всего, чтобы избежать конфликтов
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # Если loop не существует, создаём новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Инициализация базы данных в существующем loop
    try:
        loop.run_until_complete(initialize_database())
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")
        print(f"❌ Не удалось инициализировать базу данных: {e}")
        import traceback
        traceback.print_exc()
        remove_pid_file()
        return

    # Создание приложения Telegram с настройками таймаутов
    try:
        # Настройка таймаутов для Telegram API
        # connect_timeout - время на установку соединения
        # read_timeout - время на чтение ответа
        # write_timeout - время на отправку запроса
        from telegram.request import HTTPXRequest

        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=20.0,  # 20 секунд на подключение
            read_timeout=30.0,     # 30 секунд на чтение
            write_timeout=20.0,    # 20 секунд на запись
        )

        application = Application.builder().token(config.BOT_TOKEN).request(request).build()
        app_instance = application
        logger.info("✅ Telegram Application создан с настроенными таймаутами")

        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("scenario", scenario_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("rank", rank_command))
        application.add_handler(CommandHandler("case", case_command))
        application.add_handler(CommandHandler("caseinfo", caseinfo_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("validate", validate_config_command))
        application.add_handler(CommandHandler("author", author_command))
        # ===== ЗАКОММЕНТИРОВАНО: Админская команда для тестирования меню оплаты =====
        # Раскомментировать когда нужно вернуть функционал оплаты:
        # application.add_handler(CommandHandler("test_new_user", test_new_user_command))

        # ===== РЕГИСТРАЦИЯ CALLBACK HANDLERS =====
        # ВАЖНО: Порядок имеет значение! Более специфичные handlers должны быть выше.

        # Специфичный handler для "Начать тренировку"
        application.add_handler(CallbackQueryHandler(
            start_training_callback,
            pattern="^start:training$"
        ))  # group=0 по умолчанию
        logger.info("✅ Handler start:training зарегистрирован")

        # ===== Handlers для бесплатного доступа и "Как это работает" =====
        # 3. Специфичный handler для "Как это работает?" (ВЫСОКИЙ ПРИОРИТЕТ)
        from modules.payments.handlers import how_it_works_callback
        application.add_handler(CallbackQueryHandler(
            how_it_works_callback,
            pattern="^payment:how_it_works$"
        ))  # group=0 по умолчанию
        logger.info("✅ Handler payment:how_it_works зарегистрирован (высокий приоритет)")

        # 4. Остальные handlers (только бесплатный доступ и возражения, без оплаты)
        from modules.payments.handlers import register_free_access_handlers
        register_free_access_handlers(application)
        logger.info("✅ Free access handlers зарегистрированы")

        # 5. Админ-панель и управление кнопками
        from modules.payments.admin_handlers import register_admin_handlers
        register_admin_handlers(application)
        logger.info("✅ Admin handlers зарегистрированы")

        # Добавление обработчика текстовых сообщений ПОСЛЕ специализированных handlers
        # ВАЖНО: Регистрируем в group=0 (по умолчанию), чтобы ConversationHandler (group=-1) обрабатывался первым
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message), group=0)

        # Глобальный обработчик ошибок для callback queries
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик ошибок для предотвращения падения бота."""
            error = context.error

            # Conflict - логируем, но не останавливаем бот (обрабатывается в основном коде polling)
            if isinstance(error, Conflict):
                logger.warning("=" * 80)
                logger.warning("⚠️ CONFLICT ERROR в обработчике (не критично, polling обработает)")
                logger.warning(f"Conflict: {error}")
                logger.warning("=" * 80)
                # Не останавливаем бот - пусть polling обработает это
                return

            logger.error("=" * 80)
            logger.error("❌ ERROR HANDLER TRIGGERED!")
            logger.error(f"Exception: {error}")
            logger.error(f"Exception type: {type(error)}")
            logger.error(f"Update type: {type(update)}")
            logger.error("=" * 80)

            if update:
                logger.error(f"Update content: {update}")

            import traceback
            logger.error("Full traceback:")
            logger.error(traceback.format_exc())

            # Если это callback query, пытаемся ответить на него
            if update and hasattr(update, 'callback_query') and update.callback_query:
                try:
                    callback_data = update.callback_query.data if hasattr(update.callback_query, 'data') else 'unknown'
                    logger.info(f"Trying to answer callback query: {callback_data}")
                    await update.callback_query.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=False)
                except Exception as e:
                    logger.error(f"Error answering callback: {e}")
                    import traceback
                    logger.error(f"Traceback for callback answer error:\n{traceback.format_exc()}")

            # НЕ ОСТАНАВЛИВАЕМ БОТ для других ошибок!
            # Но логируем детальную информацию для отладки
            logger.error("⚠️ Error handled, bot continues running")
            logger.error(f"Error details: {type(error).__name__}: {str(error)}")
            # НЕ ВЫЗЫВАЕМ application.stop()!

        application.add_error_handler(error_handler)

        # Запуск health check сервера
        try:
            start_health_server(config.PORT)
            logger.info(f"📊 Health check доступен на порту {config.PORT}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось запустить health check server: {e}")

        # Запуск бота
        logger.info("🚀 Бот запущен")
        print("✅ Бот успешно запущен!")
        print(f"📊 Health check доступен на порту {config.PORT}")
        print("🛑 Для остановки используйте Ctrl+C")

        # Запуск polling (блокирующий вызов, run_polling создаст и будет управлять event loop)
        # Используем close_loop=False, так как мы управляем loop вручную
        # Добавляем retry логику для сетевых ошибок и Conflict
        max_retries = 10  # Увеличиваем количество попыток для Conflict
        retry_delay = 10  # секунд - ждем дольше при Conflict
        conflict_retry_delay = 30  # секунд - специальная задержка для Conflict

        try:
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 Starting polling... (попытка {attempt + 1}/{max_retries})")
                    logger.info("⚙️ Polling settings: timeout=10s, poll_interval=1.0s")
                    application.run_polling(
                        allowed_updates=Update.ALL_TYPES,
                        drop_pending_updates=True,
                        close_loop=False,  # Не закрываем loop, так как он может быть использован для cleanup
                        timeout=10,  # Long polling timeout (секунды) - Telegram будет держать соединение до 10 сек
                        poll_interval=1.0  # Интервал между запросами (секунды) - минимальная задержка между getUpdates
                    )
                    # Если дошли сюда, значит polling завершился нормально
                    break
                except Conflict as e:
                    # Conflict - другой экземпляр бота работает, ждем и повторяем попытку
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Conflict при запуске polling (попытка {attempt + 1}/{max_retries}): {e}")
                        logger.warning("Другой экземпляр бота работает. Ждем и повторяем попытку...")
                        logger.info(f"⏳ Повторная попытка через {conflict_retry_delay} секунд...")
                        import time
                        time.sleep(conflict_retry_delay)
                        # Не увеличиваем задержку экспоненциально для Conflict - используем фиксированную
                    else:
                        logger.error(f"❌ Не удалось запустить polling после {max_retries} попыток из-за Conflict")
                        logger.error("Возможно, другой экземпляр бота все еще работает.")
                        logger.error("Проверьте Railway Dashboard и остановите старый сервис.")
                        raise
                except NetworkError as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Сетевая ошибка при запуске polling (попытка {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"⏳ Повторная попытка через {retry_delay} секунд...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Увеличиваем задержку экспоненциально
                    else:
                        logger.error(f"❌ Не удалось запустить polling после {max_retries} попыток")
                        raise
        except KeyboardInterrupt:
            logger.info("⌨️ KeyboardInterrupt received, stopping...")
        except Conflict as e:
            # Conflict уже обработан выше, просто пробрасываем дальше
            raise
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ EXCEPTION IN RUN_POLLING: {e}")
            logger.error("=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            raise

    except Conflict as e:
        # Conflict уже обработан в цикле retry выше, но если дошли сюда - все попытки исчерпаны
        logger.error(f"Конфликт с Telegram API после всех попыток: {e}")
        logger.error("Бот будет перезапущен Railway автоматически. Проверьте, не запущен ли старый сервис.")
        print("⚠️ Внимание: Бот не смог запуститься из-за конфликта с другим экземпляром.")
        print("Railway автоматически перезапустит бот. Если проблема сохраняется,")
        print("проверьте Railway Dashboard и удалите старый сервис 'prolific-reflection'.")
    except NetworkError as e:
        logger.error(f"Ошибка сети: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        print("❌ Ошибка сети. Проверьте подключение к интернету.")
        print(f"Детали: {e}")
        print("\n💡 Попробуйте:")
        print("  1. Проверить подключение к интернету")
        print("  2. Проверить, не блокирует ли файрвол/прокси доступ к api.telegram.org")
        print("  3. Попробовать запустить бота позже")
    except KeyboardInterrupt:
        logger.warning("=" * 80)
        logger.warning("🛑 KEYBOARD INTERRUPT (Ctrl+C) RECEIVED!")
        logger.warning("=" * 80)
        import traceback
        logger.warning("KeyboardInterrupt traceback:")
        traceback.print_exc()
        logger.info("Получен сигнал прерывания (Ctrl+C)")
        print("\n🛑 Остановка бота...")
    except (IndexError, RuntimeError) as e:
        # Игнорируем ошибки закрытия event loop при остановке
        if "pop from an empty deque" in str(e) or "Event loop is closed" in str(e):
            logger.info("Бот остановлен (event loop закрыт)")
        else:
            logger.error(f"Ошибка: {e}")
            print(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("🛑 run_polling() завершён")

        # Очистка ресурсов
        logger.info("🧹 Starting cleanup...")

        try:
            # Проверяем, есть ли открытый event loop
            try:
                # Пытаемся получить работающий loop
                loop = asyncio.get_running_loop()
                logger.info("Event loop ещё работает, пропускаем cleanup (будет выполнено автоматически)")
                # НЕ вызываем cleanup здесь, так как loop ещё работает
            except RuntimeError:
                # Нет работающего loop, пытаемся получить существующий
                logger.info("Нет работающего event loop, пытаемся получить существующий")
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        logger.info("Event loop уже закрыт, пропускаем cleanup")
                    else:
                        logger.info("Event loop открыт, выполняем cleanup")
                        loop.run_until_complete(cleanup_resources())
                except Exception as e:
                    logger.error(f"Не удалось получить event loop: {e}")
                    logger.info("Пропускаем cleanup")
        except Exception as e:
            logger.error(f"Ошибка при очистке ресурсов: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # Удаление PID файла
        remove_pid_file()
        logger.info("Бот остановлен")


if __name__ == '__main__':
    main()
