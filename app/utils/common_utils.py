"""
通用工具类集合

当前包含：
- safe_round_div: 安全的除法与四舍五入函数

设计原则：
- 防御性编程：处理各种异常输入（None、空字符串、非数字等）
- 类型安全：使用 Decimal 进行精确计算，避免浮点精度问题
- 默认友好：异常情况下返回 0.00，保证程序不中断
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class CommonUtils:
    """通用辅助工具类"""

    @staticmethod
    def safe_round_div(value, divisor, decimal_places=2):
        """
        安全的除法与四舍五入函数（真正四舍五入，非银行家舍入）

        功能说明：
        - 处理 None、空字符串、"--" 等无效输入
        - 使用 Decimal 高精度计算
        - 严格四舍五入（ROUND_HALF_UP）
        - 异常时返回 0.00（float 类型）
        """
        # 第一步：清洗被除数
        try:
            if value is None or value == "" or value == "-"or value == "_":
                clean_value = 0
            else:
                clean_value = float(value)
        except (ValueError, TypeError):
            clean_value = 0

        # 第二步：安全除法 + 四舍五入
        try:
            dividend = Decimal(str(clean_value))
            divisor_d = Decimal(str(divisor))

            if divisor_d == 0:
                return 0.0

            result = dividend / divisor_d

            # 构造 quantize 的目标格式，如 '0.01' 表示保留两位小数
            quantize_exp = Decimal('0.' + '0' * decimal_places) if decimal_places > 0 else Decimal('1')
            rounded_result = result.quantize(quantize_exp, rounding=ROUND_HALF_UP)

            return float(rounded_result)

        except Exception:
            return 0.0

    @staticmethod
    def is_main_board(stock_code: str) -> bool:
        """
        判断给定的A股股票代码是否为主板上市。

        参数:
            stock_code (str): 6位数字字符串，如 '600000' 或 '000001'

        返回:
            bool: True 表示主板，False 表示非主板（如创业板、科创板、北交所等）
        """
        # 清理输入：去除可能的前后空格，并确保是字符串
        code = stock_code.strip()

        # 必须是6位纯数字
        if not (isinstance(code, str) and len(code) == 6 and code.isdigit()):
            return False

        # 沪市主板：60开头
        if code.startswith('60'):
            return True

        # 深市主板：00、01、02、03 开头（000-004 范围内基本都算主板）
        if code.startswith(('00', '01', '02', '03')):
            # 排除一些特殊情况（如0035xx以后可能不是股票？但目前003基本未用）
            # 保守起见，只要00/01/02/03开头就认为是主板
            return True

        # 其他情况（30=创业板，688=科创板，8=北交所等）都不是主板
        return False
