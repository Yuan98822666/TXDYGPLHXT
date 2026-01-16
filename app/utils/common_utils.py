"""
通用工具类集合

当前包含：
- safe_round_div: 安全的除法与四舍五入函数

设计原则：
- 防御性编程：处理各种异常输入（None、空字符串、非数字等）
- 类型安全：使用 Decimal 进行精确计算，避免浮点精度问题
- 默认友好：异常情况下返回 0.00，保证程序不中断
"""

from decimal import Decimal, InvalidOperation


class CommonUtils:
    """通用辅助工具类"""

    @staticmethod
    def safe_round_div(value, divisor, decimal_places=2):
        """
        安全的除法与四舍五-rounding 函数

        功能说明：
        - 处理各种异常输入（None、空字符串、"--"、非数字字符串等）
        - 使用 Decimal 进行高精度计算，避免浮点误差
        - 四舍五入到指定小数位数
        - 异常情况下统一返回 0.00

        参数:
            value: 被除数，可以是数字、字符串或 None
            divisor: 除数，通常是固定的转换因子（如 100、10000）
            decimal_places (int): 保留的小数位数，默认为 2

        返回:
            float: 计算结果，异常时返回 0.00

        处理逻辑:
            第一步：数据清洗
            - None、空字符串、"--" → 转换为 0
            - 尝试转换为 float 验证是否为有效数字
            - 转换失败 → 强制设为 0

            第二步：精确计算
            - 使用 Decimal 进行除法运算（避免浮点精度问题）
            - 四舍五入到指定小数位
            - 转换为 float 返回（兼容数据库存储）

            第三步：异常兜底
            - 除零错误、类型错误等 → 返回 0.00
        """
        # 第一步：清洗数据。如果值为空，或者非数字字符，转为 0
        try:
            if value is None or value == "" or value == "--":
                clean_value = 0
            else:
                # 尝试将输入转换为浮点数，测试是否为有效数字
                # 这里使用 float 先做一次校验，兼容字符串数字如 "123.45"
                clean_value = float(value)
        except (ValueError, TypeError):
            # 如果转换失败（例如传入了 "abc"），则强制设为 0
            clean_value = 0

        # 第二步：进行除法和四舍五入
        try:
            # 将清洗后的数字转为 Decimal 进行精确计算
            result = Decimal(str(clean_value)) / Decimal(str(divisor))
            # 四舍五入并转为 float 返回
            return float(round(result, decimal_places))
        except (InvalidOperation, TypeError, ZeroDivisionError):
            # 理论上 divisor 是固定的（100/10000），不会除零，这里做双重保险
            return 0.0