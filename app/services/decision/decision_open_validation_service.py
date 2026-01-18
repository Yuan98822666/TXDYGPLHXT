"""
次日竞价验证服务（DecisionOpenValidationService）

功能：
- 对前一交易日被批准“隔夜下注”（decision_status='ALLOW'）的股票
- 验证其在次日竞价阶段的表现（9:15-9:25）
- 判断是否值得继续持有（基于开盘溢价和量能）

验证规则：
1. 只处理前一天状态为 ALLOW 的股票
2. 若次日无竞价数据（如停牌）→ 标记为 "NO_DATA"
3. 计算：开盘价 vs 前日收盘价 的涨跌幅
4. 输出：验证状态（SUCCESS / FAILURE / NO_DATA）+ 关键指标

作者：系统 v1.0 验证引擎
"""

from datetime import date, datetime
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.models.decision.decision_stock_daily import DecisionStockDaily
from app.models.decision.decision_open_validation import DecisionOpenValidation
from app.models.raw.raw_stock_huoyue import RawStockHuoyue
from app.services.decision.decision_stock_daily_service import DecisionStockDailyService

class DecisionOpenValidationService:
    """
    隔夜策略裁判员

    输入：验证日期（即决策日的下一个交易日）
    逻辑：
        - 自动找到前一个交易日（prev_date）
        - 加载 prev_date 中所有 ALLOW 股票
        - 检查这些股票在验证日的竞价表现
    """

    VALIDATION_SUCCESS = "SUCCESS"  # 开盘上涨 ≥1%
    VALIDATION_FAILURE = "FAILURE"  # 开盘下跌或涨幅 <1%
    VALIDATION_NO_DATA = "NO_DATA"  # 无竞价数据（停牌等）

    @staticmethod
    def validate_open_for_date(db: Session, validate_date: date) -> List[DecisionOpenValidation]:
        """
        执行次日竞价验证主流程

        :param db: 数据库会话
        :param validate_date: 验证日期（例如 2026-01-18）
        :return: 验证结果列表
        """
        # === 第一步：确定前一交易日 ===
        from app.utils.trading_day import TradingDayUtils
        if not TradingDayUtils.is_trading_day(validate_date):
            raise ValueError(f"{validate_date} 不是交易日，无法验证")

        prev_date = TradingDayUtils.get_previous_trading_day(validate_date)
        print(f"🔍 验证 {validate_date}：基于 {prev_date} 的 ALLOW 决策")

        # === 第二步：清理当日旧验证记录 ===
        deleted = db.query(DecisionOpenValidation).filter(
            DecisionOpenValidation.validate_date == validate_date
        ).delete()
        print(f"🧹 清理 {validate_date} 旧验证记录 {deleted} 条")

        # === 第三步：获取前一天所有 ALLOW 股票 ===
        allow_decisions = db.query(DecisionStockDaily).filter(
            DecisionStockDaily.trade_date == prev_date,
            DecisionStockDaily.decision_status == DecisionStockDailyService.STATUS_ALLOW  # 👈 只验 ALLOW
        ).all()

        if not allow_decisions:
            print(f"⚠️  {prev_date} 无 ALLOW 股票，跳过验证")
            return []

        print(f"🎯 共 {len(allow_decisions)} 只 ALLOW 股票待验证")

        # === 第四步：逐只验证 ===
        new_validations = []
        for decision in allow_decisions:
            validation = DecisionOpenValidationService._validate_single_stock(
                db, decision, validate_date
            )
            db.add(validation)
            new_validations.append(validation)

        db.commit()

        # === 第五步：输出统计摘要 ===
        stats = DecisionOpenValidationService._generate_summary(new_validations)
        print(f"✅ 验证完成：{stats}")

        return new_validations

    @staticmethod
    def _validate_single_stock(
            db: Session,
            decision: DecisionStockDaily,
            validate_date: date
    ) -> DecisionOpenValidation:
        """
        验证单只股票的次日竞价表现
        """
        stock_code = decision.stock_code

        # 尝试获取次日竞价最后一条记录（9:25）
        open_record = db.query(RawStockHuoyue).filter(
            RawStockHuoyue.trade_date == validate_date,
            RawStockHuoyue.stock_code == stock_code,
            RawStockHuoyue.time == "09:25"
        ).first()

        # 默认值
        validation_status = DecisionOpenValidationService.VALIDATION_NO_DATA
        open_change_pct = None
        volume_ratio = None
        remarks = "无竞价数据（可能停牌）"

        if open_record and open_record.close_price and decision.metrics_json.get("close_price"):
            try:
                prev_close = float(decision.metrics_json["close_price"])
                today_open = float(open_record.stock_zxj)
                open_change_pct = round((today_open - prev_close) / prev_close * 100, 2)

                # 判断成功条件：开盘涨幅 ≥1%
                if open_change_pct >= 1.0:
                    validation_status = DecisionOpenValidationService.VALIDATION_SUCCESS
                    remarks = f"开盘上涨 {open_change_pct}%"
                else:
                    validation_status = DecisionOpenValidationService.VALIDATION_FAILURE
                    remarks = f"开盘涨幅不足（{open_change_pct}%）"

                # 计算量比（如果原始数据有昨日成交量）
                if hasattr(open_record, 'volume') and 'prev_volume' in decision.metrics_json:
                    today_vol = open_record.volume
                    prev_vol = decision.metrics_json['prev_volume']
                    if prev_vol > 0:
                        volume_ratio = round(today_vol / prev_vol, 2)

            except (ValueError, TypeError, ZeroDivisionError):
                remarks = "价格数据异常"

        return DecisionOpenValidation(
            validate_date=validate_date,
            stock_code=stock_code,
            decision_date=decision.trade_date,
            validation_status=validation_status,
            open_change_pct=open_change_pct,
            volume_ratio=volume_ratio,
            remarks=remarks,
            created_at=datetime.now()
        )

    @staticmethod
    def _generate_summary(validations: List[DecisionOpenValidation]) -> str:
        """
        生成验证统计摘要
        """
        total = len(validations)
        success = sum(1 for v in validations if v.validation_status == DecisionOpenValidationService.VALIDATION_SUCCESS)
        failure = sum(1 for v in validations if v.validation_status == DecisionOpenValidationService.VALIDATION_FAILURE)
        no_data = total - success - failure

        win_rate = round(success / (success + failure) * 100, 1) if (success + failure) > 0 else 0.0

        return (
            f"总验证{total}只 | 成功{success} | 失败{failure} | 无数据{no_data} | "
            f"胜率{win_rate}%"
        )