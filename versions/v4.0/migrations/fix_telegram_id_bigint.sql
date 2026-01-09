-- =====================================================
-- Миграция: Исправление типа данных telegram_id
-- Дата: 2026-01-09
-- Проблема: telegram_id определен как INTEGER (int32)
--           но некоторые Telegram ID превышают диапазон int32
-- Решение: Изменить тип на BIGINT (int64)
-- =====================================================

-- Изменить тип колонки telegram_id в таблице users
ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT;

-- Изменить тип колонки telegram_id в таблице training_history (если существует)
-- Проверьте сначала, существует ли таблица:
-- SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'training_history');
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'training_history') THEN
        ALTER TABLE training_history ALTER COLUMN telegram_id TYPE BIGINT;
        RAISE NOTICE 'Table training_history updated';
    ELSE
        RAISE NOTICE 'Table training_history does not exist, skipping';
    END IF;
END $$;

-- Изменить тип колонки telegram_id в таблице training_users (если существует)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'training_users') THEN
        ALTER TABLE training_users ALTER COLUMN telegram_id TYPE BIGINT;
        RAISE NOTICE 'Table training_users updated';
    ELSE
        RAISE NOTICE 'Table training_users does not exist, skipping';
    END IF;
END $$;

-- Проверка результата
-- Выполните после миграции:
-- \d users
-- \d training_history
-- \d training_users

-- Ожидаемый результат:
-- telegram_id | bigint | not null
