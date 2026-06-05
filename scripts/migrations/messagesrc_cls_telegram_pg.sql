-- 财联社电报消息表 (PostgreSQL版本)
CREATE TABLE IF NOT EXISTS messagesrc_cls_telegram (
    id SERIAL PRIMARY KEY,
    msg_id VARCHAR(50) NOT NULL UNIQUE,
    publish_time TIMESTAMP NOT NULL,
    content TEXT NOT NULL,
    title VARCHAR(500) DEFAULT NULL,
    category VARCHAR(20) DEFAULT NULL,
    subjects JSONB DEFAULT NULL,
    is_important BOOLEAN DEFAULT FALSE,
    has_image BOOLEAN DEFAULT FALSE,
    image_urls TEXT DEFAULT NULL,
    image_ocr_text TEXT DEFAULT NULL,
    audio_urls TEXT DEFAULT NULL,
    source_url VARCHAR(500) DEFAULT NULL,
    reading_num BIGINT DEFAULT 0,
    share_num BIGINT DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cls_telegram_publish_time ON messagesrc_cls_telegram(publish_time);
CREATE INDEX IF NOT EXISTS idx_cls_telegram_category ON messagesrc_cls_telegram(category);
CREATE INDEX IF NOT EXISTS idx_cls_telegram_is_important ON messagesrc_cls_telegram(is_important);
CREATE INDEX IF NOT EXISTS idx_cls_telegram_msg_id ON messagesrc_cls_telegram(msg_id);

-- 添加更新时间触发器
CREATE OR REPLACE FUNCTION update_cls_telegram_update_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.update_time = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_cls_telegram_update_time ON messagesrc_cls_telegram;
CREATE TRIGGER trigger_cls_telegram_update_time
    BEFORE UPDATE ON messagesrc_cls_telegram
    FOR EACH ROW
    EXECUTE FUNCTION update_cls_telegram_update_time();

-- 添加表注释
COMMENT ON TABLE messagesrc_cls_telegram IS '财联社电报消息表';
COMMENT ON COLUMN messagesrc_cls_telegram.msg_id IS '财联社消息唯一ID';
COMMENT ON COLUMN messagesrc_cls_telegram.category IS '分类: zc政策/gs公司/hy行业/sc市场';
