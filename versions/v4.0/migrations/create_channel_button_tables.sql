-- Migration: Create channel_button and channel_button_clicks tables
-- Date: 2026-01-09
-- Description: Adds tables for tracking channel button clicks

-- Create channel_buttons table
CREATE TABLE IF NOT EXISTS channel_buttons (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(255) NOT NULL,
    message_id INTEGER NOT NULL,
    post_title VARCHAR(500) NOT NULL,
    button_text VARCHAR(255) NOT NULL,
    lead_magnet_type VARCHAR(50) NOT NULL,
    link VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT NOT NULL
);

-- Create indexes for channel_buttons
CREATE INDEX IF NOT EXISTS idx_channel_buttons_channel_id ON channel_buttons(channel_id);
CREATE INDEX IF NOT EXISTS idx_channel_buttons_message_id ON channel_buttons(message_id);

-- Create channel_button_clicks table
CREATE TABLE IF NOT EXISTS channel_button_clicks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    telegram_id BIGINT NOT NULL,
    button_id INTEGER,
    clicked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    post_id INTEGER,
    source VARCHAR(100),
    CONSTRAINT fk_channel_button_clicks_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_channel_button_clicks_button FOREIGN KEY (button_id) REFERENCES channel_buttons(id) ON DELETE SET NULL
);

-- Create indexes for channel_button_clicks
CREATE INDEX IF NOT EXISTS idx_channel_button_clicks_telegram_id ON channel_button_clicks(telegram_id);
CREATE INDEX IF NOT EXISTS idx_channel_button_clicks_button_id ON channel_button_clicks(button_id);
CREATE INDEX IF NOT EXISTS idx_channel_button_clicks_clicked_at ON channel_button_clicks(clicked_at);
CREATE INDEX IF NOT EXISTS idx_channel_button_clicks_post_id ON channel_button_clicks(post_id);
