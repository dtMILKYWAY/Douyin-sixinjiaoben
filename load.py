# 在 load.py 的顶部添加
import sys
import os

def resource_path(relative_path):
    """ 获取资源的绝对路径，适用于开发环境和 PyInstaller 打包环境 """
    try:
        # PyInstaller 创建一个临时文件夹并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        # 不在 PyInstaller 打包环境中，使用常规路径
        # 假设 load.py 与 main.py 在同一级别或其子模块可访问的父级
        # 为了简单，这里我们假设 main.py 所在的目录是项目根目录
        # 如果 load.py 在 douyin/load/ 目录下，而 main.py 在 tauren_scritpt_main/
        # 并且数据文件在 tauren_scritpt_main/，那么 base_path 需要正确指向 tauren_scritpt_main/
        # 一个更简单的方式是假设脚本执行时，当前工作目录已设置为包含数据文件的目录，
        # 或者数据文件与 load.py 的相对路径是固定的。
        # 但使用 sys.executable 的目录通常对打包更稳健。

        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # PyInstaller one-file bundle
             base_path = os.path.dirname(sys.executable)
        else:
            # Development or PyInstaller one-dir bundle
            # 假设 load.py 在 tauren_scritpt_main/douyin/load/load.py
            # 而 main.py 在 tauren_scritpt_main/main.py
            # 数据文件在 tauren_scritpt_main/
            # 我们需要找到 main.py 所在的目录
            # 这是基于 main.py 是入口脚本且数据文件相对于它存放的假设
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0])) # 获取主脚本 main.py 的目录
            base_path = script_dir # 数据文件相对于 main.py 存放

    return os.path.join(base_path, relative_path)

class Load:

    @staticmethod
    def load(file_name):
        dir = os.getcwd()
        file_path = dir + "\\" + file_name
        print("读取文件信息: " + file_path)
        link_items = []
        with open(file_path, 'r', encoding="utf-8") as file:
            for line in file:
                link_items.append(line.strip())
        return link_items

    @staticmethod
    def load_map(file_name):
        dir = os.getcwd()
        file_path = dir + "\\" + file_name
        print("读取文件信息: " + file_path)
        link_item_map = {}
        with open(file_path, 'r', encoding="utf-8") as file:
            for line in file:
                line_items = line.strip().split(">")
                link_item_map[line_items[0]] = line_items[1]
        return link_item_map