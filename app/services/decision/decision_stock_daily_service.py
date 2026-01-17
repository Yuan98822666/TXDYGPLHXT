# app/services/decision/decision_stock_daily_service.py
"""
盘尾决策服务
核心任务：在每日 14:30 后，基于当日盘中事件，判断每只股票是否“允许隔夜持仓”

设计原则：
1. 只处理当日被板块点名过的股票（避免全市场扫描）
2. 严格执行硬性 FORBIDDEN 规则（排除高风险标的）
3. ALLOW 必须同时满足：共识 + 资金 + 控盘（结构完整）
"""

from datetime import date, datetime, time
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.event.event_block_start import EventBlockStart
from app.models.event.event_capital_persistence import EventCapitalPersistence
from app.models.event.event_stock_dominance import EventStockDominance
from app.models.event.event_stock_consensus import EventStockConsensus
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from app.models.decision.decision_stock_daily import DecisionStockDaily


class DecisionStockDailyService:
    def __init__(self, db: Session):
        self.db = db

    def run_daily_decision(self, trade_date: date) -> dict:
        """
        执行盘尾决策主流程
        :param trade_date: 交易日期（如 date(2026, 1, 17)）
        :return: 统计结果 {'allow': 5, 'observe': 12, ...}
        """
        # 第一步：获取当日所有被板块点名的股票（去重）
        mentioned_stocks = self._get_mentioned_stocks(trade_date)

        # 初始化计数器
        allow_count = observe_count = forbidden_count = 0

        # 遍历每只被点名的股票，进行评估
        for stock_code, stock_name in mentioned_stocks:
            # 调用评估函数，返回状态、原因、指标
            status, reason, metrics = self._evaluate_stock(trade_date, stock_code, stock_name)

            # 构建数据库对象（使用 merge 支持幂等更新）
            decision = DecisionStockDaily(
                trade_date=trade_date,
                stock_code=stock_code,
                stock_name=stock_name,
                decision_status=status,
                decision_reason=reason,
                **metrics  # 展开指标字典
            )
            self.db.merge(decision)

            # 更新计数
            if status == "ALLOW":
                allow_count += 1
            elif status == "OBSERVE":
                observe_count += 1
            else:  # FORBIDDEN
                forbidden_count += 1

        # 提交事务
        self.db.commit()

        return {
            "trade_date": trade_date.isoformat(),
            "allow": allow_count,
            "observe": observe_count,
            "forbidden": forbidden_count
        }

    def _get_mentioned_stocks(self, trade_date: date) -> List[Tuple[str, str]]:
        """
        获取当日被活跃板块点名的所有股票（去重）
        依据：event_stock_consensus 表中的 is_final=False 记录（盘中事件）
        """
        stocks = self.db.query(
            EventStockConsensus.stock_code,
            EventStockConsensus.stock_name
        ).filter(
            EventStockConsensus.trade_date == trade_date,EventStockConsensus.is_final == False  # 只取盘中快照
        ).distinct().all()
        return [(r[0], r[1]) for r in stocks]

    def _evaluate_stock(self, trade_date: date, stock_code: str, stock_name: str) -> tuple:
        """
        对单只股票进行盘尾评估
        返回：(状态, 原因, 指标字典)
        """
        # 从事件表中查询四类事件（盘中版本）
        consensus = self.db.query(EventStockConsensus).filter_by(
            trade_date=trade_date, stock_code=stock_code, is_final=False
        ).first()

        capital = self.db.query(EventCapitalPersistence).filter_by(
            trade_date=trade_date, stock_code=stock_code, is_final=False
        ).first()

        dominance = self.db.query(EventStockDominance).filter_by(
            trade_date=trade_date, stock_code=stock_code, is_final=False
        ).first()

        # ========== 硬性 FORBIDDEN 规则（命中任一条即禁止）==========

        # 规则1: 尾盘资金撤退（14:30–14:55 主力净流入 ≤ 0）
        if self._is_tail_capital_withdrawn(trade_date, stock_code):
            return "FORBIDDEN", "尾盘资金撤退：游资不愿带仓过夜", {}

        # 规则2: 尾盘冲高回落 > 1.5%
        if self._is_tail_price_retraced(trade_date, stock_code, threshold=1.5):
            return "FORBIDDEN", "尾盘冲高回落：疑似主力出货", {}

        # 规则3: 只有共识，无资金/控盘支撑
        if consensus and not (capital or dominance):
            return "FORBIDDEN", "仅有群体共识，无真实资金介入", {}

        # 规则4: 非主线板块的“独苗股”
        if consensus and consensus.consensus_strength < 3:
            # 检查这些板块是否本身活跃（有 BlockStart 事件）
            source_block_names = [b['name'] for b in consensus.source_blocks]
            block_start_exists = self.db.query(EventBlockStart).filter(
                EventBlockStart.trade_date == trade_date,
                EventBlockStart.is_final == False,
                EventBlockStart.block_name.in_(source_block_names)
            ).count() > 0

            if not block_start_exists:
                return "FORBIDDEN", "所属板块非主线，易一日游", {}

        # ========== 判断是否满足 ALLOW 条件 ==========
        has_consensus = bool(consensus and consensus.consensus_strength >= 3)
        has_capital = bool(capital and capital.duration_minutes >= 60)
        has_dominance = bool(dominance and dominance.dominance_ratio >= 0.6)

        if has_consensus and has_capital and has_dominance:
            # 构建指标字典（用于写入数据库）
            metrics = {
                "block_hit_count": consensus.consensus_strength,
                "capital_minutes": capital.duration_minutes,
                "dominance_minutes": dominance.duration_minutes,
                "consensus_strength": consensus.consensus_strength,
                "confidence_score": min(100.0,
                                        (consensus.consensus_strength * 10 +
                                         capital.duration_minutes * 0.5 +
                                         dominance.dominance_ratio * 100) / 3
                                        )
            }
            return "ALLOW", "结构完整：共识+资金+控盘", metrics

        # 默认：部分条件满足 → OBSERVE
        return "OBSERVE", "部分信号满足，但结构不完整", {}

    def _is_tail_capital_withdrawn(self, trade_date: date, stock_code: str) -> bool:
        """
        检查尾盘（14:30-14:55）是否出现主力资金撤退
        判断标准：该时段主力净流入总和 ≤ 0
        """
        start_time = datetime.combine(trade_date, time(14, 30))
        end_time = datetime.combine(trade_date, time(14, 55))

        snapshots = self.db.query(RawStockHuoyue).filter(
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.market_time >= start_time,
            RawStockHuoyue.market_time <= end_time
        ).all()

        if not snapshots:
            return True  # 无数据视为异常

        total_inflow = sum(s.zl_net_inflow or 0 for s in snapshots)
        return total_inflow <= 0

    def _is_tail_price_retraced(self, trade_date: date, stock_code: str, threshold: float) -> bool:
        """
        检查尾盘是否冲高回落
        判断标准：14:30 后最高涨幅 与 收盘涨幅之差 > threshold%
        """
        start_time = datetime.combine(trade_date, time(14, 30))
        snapshots = self.db.query(RawStockHuoyue).filter(RawStockHuoyue.stock_code == stock_code,RawStockHuoyue.market_time >= start_time).order_by(RawStockHuoyue.market_time).all()

        if len(snapshots) < 2:
            return False  # 数据不足

        # 找出14:30后的最高涨幅
        high_after_1430 = max(s.change_pct for s in snapshots)
        # 最后一个快照即视为“收盘前”状态
        last_change = snapshots[-1].change_pct
        retracement = high_after_1430 - last_change
        return retracement > threshold