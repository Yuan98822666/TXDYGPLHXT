"""
决策信心分服务

📌 文件说明：
本服务是系统决策层的核心，将事件事实翻译为可行动状态。
- 输入：4 类 is_final=True 的事件
- 输出：decision_confidence_score_daily 表
- 核心逻辑：严格四态判定（FORBIDDEN / OBSERVE / PREPARE / ALLOW_NEXT_DAY）

🎯 原则：
- 只读 is_final = True 的事件
- 不做任何预测，只做事实裁决
- 信心分仅用于排序，不用于直接决策
"""

from datetime import date, datetime
from typing import Dict, List, Set, Optional
from sqlalchemy.orm import Session

from app.models.event.event_capital_persistence import EventCapitalPersistence
from app.models.event.event_stock_dominance import EventStockDominance
from app.models.event.event_stock_consensus import EventStockConsensus
from app.models.event.event_block_start import EventBlockStart
from app.models.decision.decision_confidence_score_daily import DecisionConfidenceScoreDaily


class DecisionConfidenceScoreService:

    @staticmethod
    def run_for_date(db: Session, trade_date: date) -> List[DecisionConfidenceScoreDaily]:
        """
        在收盘后（15:10+）运行，生成当日最终决策。

        ▶ 输入：4 类 is_final = True 的事件
        ▶ 输出：decision_confidence_score_daily 表记录
        ▶ 规则：严格四态判定（见文档）

        ▶ 执行时机：
            每日 15:10 后，仅运行一次
        """
        # Step 1: 加载所有 is_final = True 的事件（决策唯一合法输入）
        capital_map = {
            e.stock_code: e for e in db.query(EventCapitalPersistence).filter(
                EventCapitalPersistence.trade_date == trade_date,
                EventCapitalPersistence.is_final == True
            ).all()
        }

        dominance_map = {
            e.stock_code: e for e in db.query(EventStockDominance).filter(
                EventStockDominance.trade_date == trade_date,
                EventStockDominance.is_final == True
            ).all()
        }

        consensus_map = {
            e.stock_code: e for e in db.query(EventStockConsensus).filter(
                EventStockConsensus.trade_date == trade_date,
                EventStockConsensus.is_final == True
            ).all()
        }

        # Block events: 用于加分，不参与状态判定
        block_events = db.query(EventBlockStart).filter(
            EventBlockStart.trade_date == trade_date,
            EventBlockStart.is_final == True
        ).all()

        # Step 2: 获取所有涉及的股票代码（去重）
        all_stock_codes: Set[str] = set()
        all_stock_codes.update(capital_map.keys())
        all_stock_codes.update(dominance_map.keys())
        all_stock_codes.update(consensus_map.keys())

        if not all_stock_codes:
            return []  # 无事件，无决策

        # Step 3: 遍历每只股票，判定状态（核心四行）
        decisions = []
        for stock_code in all_stock_codes:
            capital = capital_map.get(stock_code)
            dominance = dominance_map.get(stock_code)
            consensus = consensus_map.get(stock_code)

            # 默认值
            stock_name = ""
            event_ids = []
            block_score = len(block_events) * 10  # 每个启动板块 +10 分

            # === 四态判定逻辑（系统交易哲学）===
            if not capital:
                state = "FORBIDDEN"          # 无资金，直接禁止
            elif capital and not dominance:
                state = "OBSERVE"            # 有资金，无控盘 → 观察
            elif capital and dominance and not consensus:
                state = "PREPARE"            # 有资金+控盘，无共识 → 准备
            else:
                state = "ALLOW_NEXT_DAY"     # 全满足 → 允许次日入场

            # 提取股票名称 & 引用的事件ID（用于追踪）
            if capital:
                stock_name = capital.stock_name
                event_ids.append(capital.id)
            if dominance:
                stock_name = dominance.stock_name
                event_ids.append(dominance.id)
            if consensus:
                stock_name = consensus.stock_name
                event_ids.append(consensus.id)

            # 计算子项分数（按规范）
            capital_score = min(int(capital.duration_minutes / 120 * 100), 100) if capital else 0
            dominance_score = int(dominance.zl_control_ratio * 100) if dominance else 0
            consensus_score = min(consensus.mentioned_block_count * 20, 100) if consensus else 0

            # 总信心分（仅用于排序）
            confidence_score = int(
                capital_score * 0.35 +
                dominance_score * 0.25 +
                consensus_score * 0.25 +
                block_score * 0.15
            )

            decision = DecisionConfidenceScoreDaily(
                trade_date=trade_date,
                stock_code=stock_code,
                stock_name=stock_name,
                decision_state=state,
                confidence_score=confidence_score,
                block_strength_score=block_score,
                capital_score=capital_score,
                dominance_score=dominance_score,
                consensus_score=consensus_score,
                used_event_ids=event_ids,
                generated_at=datetime.now()
            )
            decisions.append(decision)

        # Step 4: 幂等写入（先删后插）
        db.query(DecisionConfidenceScoreDaily).filter(
            DecisionConfidenceScoreDaily.trade_date == trade_date
        ).delete()
        db.add_all(decisions)
        db.commit()

        return decisions