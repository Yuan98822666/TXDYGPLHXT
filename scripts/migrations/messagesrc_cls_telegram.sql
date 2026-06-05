-- 财联社电报消息表
CREATE TABLE IF NOT EXISTS messagesrc_cls_telegram (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    msg_id VARCHAR(50) NOT NULL UNIQUE COMMENT '财联社消息唯一ID',
    publish_time DATETIME NOT NULL COMMENT '发布时间',
    content TEXT NOT NULL COMMENT '正文内容',
    title VARCHAR(500) DEFAULT NULL COMMENT '标题（可选）',
    category VARCHAR(20) DEFAULT NULL COMMENT '分类: zc政策/gs公司/hy行业/sc市场',
    subjects JSON DEFAULT NULL COMMENT '原始分类标签列表',
    is_important BOOLEAN DEFAULT FALSE COMMENT '是否重要（置顶或高等级）',
    has_image BOOLEAN DEFAULT FALSE COMMENT '是否含图片',
    image_urls TEXT DEFAULT NULL COMMENT '图片URL，多个用分号隔开',
    image_ocr_text TEXT DEFAULT NULL COMMENT '图片OCR识别内容，多个用分号隔开',
    audio_urls TEXT DEFAULT NULL COMMENT '音频URL，多个用分号隔开',
    source_url VARCHAR(500) DEFAULT NULL COMMENT '原文链接',
    reading_num BIGINT DEFAULT 0 COMMENT '阅读数',
    share_num BIGINT DEFAULT 0 COMMENT '分享数',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_publish_time (publish_time),
    INDEX idx_category (category),
    INDEX idx_is_important (is_important),
    INDEX idx_msg_id (msg_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='财联社电报消息表';
