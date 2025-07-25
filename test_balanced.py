#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试文件名规则处理函数"""

import sys
import os

# 添加当前目录到路径，以便导入主程序
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入主程序的函数
try:
    from quark_auto_save import apply_filename_rules
    print("✅ 成功导入 apply_filename_rules 函数")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("⚠️  由于依赖问题，使用简化版本测试...")
    
    # 简化版本用于测试
    import re
    from datetime import datetime
    
    def apply_filename_rules(filename):
        """简化版文件名规则应用（仅用于测试）"""
        result = filename
        current_year = datetime.now().year
        
        rules = [
            (re.compile(r'（([上下])）'), r'\1'),
            (re.compile(r'^第((\d{8})([\s\S]*)*)'), r'\1'),
            (re.compile(r'(\d{4})\.(\d{1,2})\.(\d{1,2})'), 'lambda'),
            (re.compile(r'(\d{4})\.(\d{2})\.(\d{2})'), r'\1\2\3'),
            (re.compile(r'^(20(?:2[6-9]|[3-9]\d))(\d{4})(?=\D|$)'), 'current_year'),
            (re.compile(r'^(\d{4})(?=\D)'), 'add_current_year'),
        ]
        
        for pattern, replace_type in rules:
            if pattern.search(result):
                if replace_type == 'lambda':
                    result = pattern.sub(lambda m: f"{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}", result)
                elif replace_type == 'current_year':
                    result = pattern.sub(fr'{current_year}\2', result)
                elif replace_type == 'add_current_year':
                    result = pattern.sub(fr'{current_year}\1', result)
                else:
                    result = pattern.sub(replace_type, result)
        
        return result

if __name__ == "__main__":
    print("=== 测试文件名规则处理函数 ===\n")
    
    test_files = [
        '（上）测试文件.mp4',
        '（下）测试文件.mp4', 
        '2026.4.5-第11期下.mp4', 
        '2023.4.5-第11期下.mp4',
        '第20240728期喜人奇妙夜.mp4',
        '2024.06.08-第4期.mp4',
        '0422春日焕新特辑.mp4'
    ]

    for i, filename in enumerate(test_files, 1):
        print(f"[{i}] 原文件名: {filename}")
        result = apply_filename_rules(filename)
        print(f"    处理结果: {result}")
        print("-" * 50)

    print("\n✅ 测试完成！")