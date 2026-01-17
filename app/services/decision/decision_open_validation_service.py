# app/services/decision/decision_open_validation_service.py
"""
次日竞价验证服务
核心任务：在 T+1 日 9:25，对昨日标记为 ALLOW 的股票进行验证
注意：此服务不重新选股，只做“否决”或“确认”
"""

from datetime import date
from sqlalchemy.orm import Session
from app.models.decision.decision_stock_daily import DecisionStockDaily
from app.models.decision.decision_open_validation import DecisionOpenValidation
from app.models.raw.raw_stock_huoyue import RawStockHuoyue


class DecisionOpenValidationService:
    def __init__(self, db: Session):
        self.db = db

    def validate_open(self, trade_date: date) -> int:
        """
        执行竞价验证主流程
        :param trade_date: 验证日期（T+1 日）
        :return: 验证的股票数量
        """
        # 只查询昨日（trade_date）被标记为 ALLOW 的股票
        allow_decisions = self.db.query(DecisionStockDaily).filter(
            DecisionStockDaily.trade_date == trade_date,
            DecisionStockDaily.decision_status == "ALLOW"
        ).all()

        validated_count = 0
        for dec in allow_decisions:
            # 判断开盘状态
            open_status, reason, gap_pct, volume = self._determine_open_status(
                trade_date, dec.stock_code
            )

            # 写入验证结果
            validation = DecisionOpenValidation(
                trade_date=trade_date,
                stock_code=dec.stock_code,
                open_status=open_status,
                open_gap_pct=gap_pct,
                open_volume=volume,
                reason=reason
            )
            self.db.merge(validation)
            validated_count += 1

        self.db.commit()
        return validated_count

    def _determine_open_status(self, trade_date: date, stock_code: str) -> tuple:
        """
        根据 9:25 快照判断开盘状态
        返回：(状态, 原因, 涨跌幅, 成交量)
        """
        # 查询 9:25 的快照行（假设采集器已存入）
        snapshot = self.db.query(RawStockHuoyue).filter(
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.market_time == f"{trade_date} 09:25:00"
        ).first()

        if not snapshot:
            return "NEUTRAL", "无9:25数据，无法验证", 0.0, 0

        gap = snapshot.change_pct
        volume = snapshot.volume or 0

        # 三种状态判定逻辑
        if gap >= 0:
            return "CONFIRMED", "高开或平开，市场态度积极", gap, volume
        elif gap >= -2.0:
            return "NEUTRAL", "小幅低开（-2%以内），需盘中观察", gap, volume
        else:
            # 大幅低开（<-2%）
            if volume == 0:
                return "REJECTED", "一字跌停，流动性枯竭", gap, 0
            else:
                return "REJECTED", "大幅低开，共识已被打破", gap, volume