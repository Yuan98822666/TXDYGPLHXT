-- 创建分析表
-- 执行方式: psql -d your_database -f scripts/migrations/create_analysis_tables.sql

-- ============================================
-- 表1: 板块-股票共振分析表 (分钟级)
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_block_stock_resonance (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    block_code VARCHAR(20) NOT NULL,
    raw_no VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- 原始数据
    stock_zl_inflow BIGINT,
    block_zl_inflow BIGINT,
    stock_ltsz BIGINT,
    
    -- 计算因子
    zt_potential_factor NUMERIC(10, 6),
    attention_factor NUMERIC(10, 6),
    block_importance_factor NUMERIC(10, 6),
    
    -- 共振标记
    is_leader BOOLEAN NOT NULL DEFAULT FALSE,
    is_money_leader BOOLEAN NOT NULL DEFAULT FALSE,
    is_resonance BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 创建时间
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_resonance_raw_stock_block 
    ON analysis_block_stock_resonance (raw_no, stock_code, block_code);

CREATE INDEX IF NOT EXISTS idx_resonance_raw_no 
    ON analysis_block_stock_resonance (raw_no);

CREATE INDEX IF NOT EXISTS idx_resonance_stock_code 
    ON analysis_block_stock_resonance (stock_code);

CREATE INDEX IF NOT EXISTS idx_resonance_block_code 
    ON analysis_block_stock_resonance (block_code);

CREATE INDEX IF NOT EXISTS idx_resonance_trade_date 
    ON analysis_block_stock_resonance (trade_date);

CREATE INDEX IF NOT EXISTS idx_resonance_zt_factor 
    ON analysis_block_stock_resonance (trade_date, zt_potential_factor DESC);

CREATE INDEX IF NOT EXISTS idx_resonance_attention 
    ON analysis_block_stock_resonance (trade_date, attention_factor DESC);

CREATE INDEX IF NOT EXISTS idx_resonance_resonance 
    ON analysis_block_stock_resonance (trade_date, is_resonance, zt_potential_factor DESC);

-- 添加表注释
COMMENT ON TABLE analysis_block_stock_resonance IS '板块-股票共振分析表（分钟级）';
COMMENT ON COLUMN analysis_block_stock_resonance.zt_potential_factor IS '涨停潜力因子 = 个股净流入/流通市值';
COMMENT ON COLUMN analysis_block_stock_resonance.attention_factor IS '受重视程度因子 = 个股净流入/板块净流入';
COMMENT ON COLUMN analysis_block_stock_resonance.block_importance_factor IS '板块受重视程度因子 = 板块净流入/所有板块总和';
COMMENT ON COLUMN analysis_block_stock_resonance.is_leader IS '是否为板块领涨股';
COMMENT ON COLUMN analysis_block_stock_resonance.is_money_leader IS '是否为板块资金流入最多股';
COMMENT ON COLUMN analysis_block_stock_resonance.is_resonance IS '是否共振（个股和板块同向流入）';

-- ============================================
-- 表2: 个股强度统计表 (日级汇总)
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_stock_strength (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    trade_date DATE NOT NULL,
    
    -- 统计次数
    leader_count INTEGER NOT NULL DEFAULT 0,
    money_leader_count INTEGER NOT NULL DEFAULT 0,
    total_blocks INTEGER NOT NULL DEFAULT 0,
    
    -- 强度因子
    strength_factor INTEGER NOT NULL DEFAULT 0,
    
    -- 涉及板块详情
    leader_blocks JSONB,
    money_leader_blocks JSONB,
    
    -- 创建时间
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 创建索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_strength_stock_date 
    ON analysis_stock_strength (stock_code, trade_date);

CREATE INDEX IF NOT EXISTS idx_strength_trade_date 
    ON analysis_stock_strength (trade_date);

CREATE INDEX IF NOT EXISTS idx_strength_factor 
    ON analysis_stock_strength (trade_date, strength_factor DESC);

-- 添加表注释
COMMENT ON TABLE analysis_stock_strength IS '个股强度统计表（日级汇总）';
COMMENT ON COLUMN analysis_stock_strength.leader_count IS '作为领涨股出现次数';
COMMENT ON COLUMN analysis_stock_strength.money_leader_count IS '作为资金流入最多股出现次数';
COMMENT ON COLUMN analysis_stock_strength.strength_factor IS '个股强度因子 = leader_count + money_leader_count';

-- ============================================
-- 完成
-- ============================================
SELECT '分析表创建完成' as status;
