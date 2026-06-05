-- 璐㈣仈绀剧數鎶ユ秷鎭〃
CREATE TABLE IF NOT EXISTS messagesrc_cls_telegram (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '鑷涓婚敭',
    msg_id VARCHAR(50) NOT NULL UNIQUE COMMENT '璐㈣仈绀炬秷鎭敮涓€ID',
    publish_time DATETIME NOT NULL COMMENT '鍙戝竷鏃堕棿',
    content TEXT NOT NULL COMMENT '姝ｆ枃鍐呭',
    title VARCHAR(500) DEFAULT NULL COMMENT '鏍囬锛堝彲閫夛級',
    category VARCHAR(20) DEFAULT NULL COMMENT '鍒嗙被: zc鏀跨瓥/gs鍏徃/hy琛屼笟/sc甯傚満',
    subjects JSON DEFAULT NULL COMMENT '鍘熷鍒嗙被鏍囩鍒楄〃',
    is_important BOOLEAN DEFAULT FALSE COMMENT '鏄惁閲嶈锛堢疆椤舵垨楂樼瓑绾э級',
    has_image BOOLEAN DEFAULT FALSE COMMENT '鏄惁鍚浘鐗?,
    image_urls TEXT DEFAULT NULL COMMENT '鍥剧墖URL锛屽涓敤鍒嗗彿闅斿紑',
    image_ocr_text TEXT DEFAULT NULL COMMENT '鍥剧墖OCR璇嗗埆鍐呭锛屽涓敤鍒嗗彿闅斿紑',
    audio_urls TEXT DEFAULT NULL COMMENT '闊抽URL锛屽涓敤鍒嗗彿闅斿紑',
    source_url VARCHAR(500) DEFAULT NULL COMMENT '鍘熸枃閾炬帴',
    reading_num BIGINT DEFAULT 0 COMMENT '闃呰鏁?,
    share_num BIGINT DEFAULT 0 COMMENT '鍒嗕韩鏁?,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '鍏ュ簱鏃堕棿',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '鏇存柊鏃堕棿',
    
    INDEX idx_publish_time (publish_time),
    INDEX idx_category (category),
    INDEX idx_is_important (is_important),
    INDEX idx_msg_id (msg_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='璐㈣仈绀剧數鎶ユ秷鎭〃';
