"""
盘尾决策服务（状态机版）

📌 核心原则：
- 严格四层规则：否决 → 核心条件 → 辅助条件 → 默认
- 仅依赖三类最终事件（is_final=True）：资金持续、控盘稳定、群体共识
- 输出三种状态：ALLOW / OBSERVE / FORBIDDEN
- 存储收盘价到 metrics_json，供次日开盘验证使用
"""

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.decision.decision_stock_daily import DecisionStockDaily
from app.models.event.event_capital_persistence import EventCapitalPersistence
from app.models.event.event_stock_dominance import EventStockDominance
from app.models.event.event_stock_consensus import EventStockConsensus
from app.models.raw.raw_stock_huoyue import RawStockHuoyue


class DecisionStockDailyService:

    @staticmethod
    def _evaluate_stock(db: Session, trade_date: date, stock_code: str) -> str:
        """
        对单只股票执行决策状态机
        返回: "ALLOW" | "OBSERVE" | "FORBIDDEN"
        """
        # === 检查尾盘撤退（最高优先级否决项）===
        retreat_count = db.query(RawStockHuoyue).filter(
            RawStockHuoyue.trade_date == trade_date,
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.time >= "14:30",
            RawStockHuoyue.time <= "15:00",
            RawStockHuoyue.is_retreat == True
        ).count()

        if retreat_count > 0:
            return "FORBIDDEN"

        # === 加载三类最终事件 ===
        capital_event = db.query(EventCapitalPersistence).filter(
            EventCapitalPersistence.trade_date == trade_date,
            EventCapitalPersistence.stock_code == stock_code,
            EventCapitalPersistence.is_final == True
        ).first()

        dominance_event = db.query(EventStockDominance).filter(
            EventStockDominance.trade_date == trade_date,
            EventStockDominance.stock_code == stock_code,
            EventStockDominance.is_final == True
        ).first()

        consensus_event = db.query(EventStockConsensus).filter(
            EventStockConsensus.trade_date == trade_date,
            EventStockConsensus.stock_code == stock_code,
            EventStockConsensus.is_final == True
        ).first()

        # === 获取收盘价（用于次日验证）===
        last_close_record = db.query(RawStockHuoyue.stock_zxj).filter(
            RawStockHuoyue.trade_date == trade_date,
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.time >= "15:00"
        ).first()
        close_price = float(last_close_record[0]) if last_close_record and last_close_record[0] is not None else None

        # === 构建指标字典（包含收盘价，供 validate-open 使用）===
        metrics = {
            "close_price": close_price,
            "has_capital": bool(capital_event),
            "capital_duration": capital_event.duration_minutes if capital_event else 0,
            "has_dominance": bool(dominance_event),
            "dominance_duration": dominance_event.duration_minutes if dominance_event else 0,
            "has_consensus": bool(consensus_event),
        }

        # === 决策状态机 ===
        # 核心条件：资金持续 + 控盘稳定
        core_met = (capital_event is not None) and (dominance_event is not None)

        # 辅助条件：群体共识
        has_consensus = consensus_event is not None

        if core_met and has_consensus:
            return "ALLOW"
        elif core_met:
            return "OBSERVE"
        else:
            return "FORBIDDEN"

    @staticmethod
    def run_daily_decision(db: Session, trade_date: date) -> List[DecisionStockDaily]:
        """
        为指定交易日所有有事件的股票生成决策
        """
        # 获取所有在当日有任一事件的股票代码（去重）
        stock_codes = set()
        for model in [EventCapitalPersistence, EventStockDominance, EventStockConsensus]:
            codes = db.query(model.stock_code).filter(
                model.trade_date == trade_date,
                model.is_final == True
            ).distinct()
            stock_codes.update([code[0] for code in codes])

        decisions = []
        for stock_code in stock_codes:
            status = DecisionStockDailyService._evaluate_stock(db, trade_date, stock_code)
            # 重新查询指标（或复用，此处简化）
            capital_event = db.query(EventCapitalPersistence).filter(
                EventCapitalPersistence.trade_date == trade_date,
                EventCapitalPersistence.stock_code == stock_code,
                EventCapitalPersistence.is_final == True
            ).first()
            dominance_event = db.query(EventStockDominance).filter(...).first()
            consensus_event = db.query(EventStockConsensus).filter(...).first()

            # 重新构建 metrics（含 close_price）
            last_close_record = db.query(RawStockHuoyue.stock_zxj).filter(
                RawStockHuoyue.trade_date == trade_date,
                RawStockHuoyue.stock_code == stock_code,
                RawStockHuoyue.time >= "15:00"
            ).first()
            close_price = float(last_close_record[0]) if last_close_record and last_close_record[0] is not None else None

            metrics = {
                "close_price": close_price,
                "has_capital": bool(capital_event),
                "capital_duration": capital_event.duration_minutes if capital_event else 0,
                "has_dominance": bool(dominance_event),
                "dominance_duration": dominance_event.duration_minutes if dominance_event else 0,
                "has_consensus": bool(consensus_event),
            }

            decision = DecisionStockDaily(
                trade_date=trade_date,
                stock_code=stock_code,
                decision_status=status,
                metrics_json=metrics
            )
            decisions.append(decision)

        # 批量保存
        db.add_all(decisions)
        db.commit()
        return decisions