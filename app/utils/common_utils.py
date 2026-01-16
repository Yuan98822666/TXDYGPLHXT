class CommonUtils:
    # 辅助函数：安全地进行除法和四舍五入
    def safe_round_div(value, divisor, decimal_places=2):
        """
            安全的除法与四舍五入函数。
            - 如果 value 为 None 或非数字字符串，返回 0.00。
            - 如果计算出错，返回 0.00。
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

