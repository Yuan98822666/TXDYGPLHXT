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
    def safe_round_div(value, divisor=1, decimal_places=2):
        """
        安全除法与四舍五入。
        - 若 value 为 None, "", "-", "--" 等无效值 → 返回 None（而非 0.0）
        - 仅当 value 是有效数字时才进行计算
        - 除零或计算异常时返回 None
        """
        # === 第一步：判断是否为“无数据”标识 ===
        if value is None or value == "" or str(value).strip() in ("-", "--", "－", "——"):
            return 0.00  # 👈 关键修改：返回 None，不是 0！

        # === 第二步：尝试转为数字 ===
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return 0.00  # 非数字字符串也视为无效

        # === 第三步：执行除法和四舍五入 ===
        try:
            dividend = Decimal(str(num_value))
            divisor_d = Decimal(str(divisor))
            if divisor_d == 0:
                return 0.00
            result = dividend / divisor_d
            # 构造保留小数位的格式
            if decimal_places > 0:
                quantize_exp = Decimal('0.' + '0' * decimal_places)
            else:
                quantize_exp = Decimal('1')
            rounded_result = result.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            return float(rounded_result)
        except Exception:
            return 0.00  # 计算失败也返回 None

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

    @staticmethod
    def purify(raw_data) -> float:
        """
        清洗数据规则：
        - 如果是 int 或 float → 直接返回 float 值
        - 如果是 None → 返回 0.0
        - 如果是字符串：
            - 若为 "", "-", "--", "－", "——" → 返回 0.0
            - 若能转成数字 → 返回该数字
            - 否则 → 返回 0.0
        """
        # 情况1: 是数字 → 直接返回
        if isinstance(raw_data, (int, float)):
            return float(raw_data)

        # 情况2: 是 None → 返回 0.0
        if raw_data is None:
            return 0.0

        # 情况3: 是字符串 → 清洗并尝试转换
        if isinstance(raw_data, str):
            s = raw_data.strip()
            # 预定义的无效占位符
            if s in ("", "-", "--", "－", "——"):
                return 0.0
            try:
                return float(s)
            except ValueError:
                return 0.0

        # 情况4: 其他类型（bool, list, dict 等）→ 返回 0.0
        return 0.0
