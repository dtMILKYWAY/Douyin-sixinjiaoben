from .douyin.douyin import Douyin  # 使用点号表示相对导入，


dou_yin = Douyin("douyin.text", "match_video.text", "match_comment.text")


def select_platform():
    while True:
        print("平台:")
        print("1.抖音")
        print("2.快手")
        print("3.知乎")
        platform_num = input("请选择平台:")
        if platform_num == "1":
            dou_yin.login()
            select_douyin_function()
        elif platform_num == "2":
            print("建设中...")
        elif platform_num == "3":
            print("建设中...")
        else:
            print("输入有误")


# ... (main.py 的其余部分保持不变) ...
def select_douyin_function():
    while True:
        print("抖音功能:")
        print("1.账户链接")
        print("2.视频链接")
        print("3.私信自动回复")
        print("4.返回上一级")
        function_num = input("请选择抖音功能:")
        if function_num == "1" or function_num == "2":
            select_douyin_operation(function_num)
        elif function_num == "3":
            select_douyin_message_monitoring()
        elif function_num == "4":
            select_platform()  # 返回 select_platform
        else:
            print("输入有误")


def select_douyin_operation(function_num):
    while True:
        print("抖音操作:")
        print("1.简单评论模式")
        print("2.评论区评论模式")
        print("3.返回上一级")
        operation_num = input("请选择抖音操作:")
        if operation_num == "1" or operation_num == "2":
            # 移除了这个循环，因为登录检查在 select_douyin_message_monitoring 中也有
            # if not dou_yin.is_login:
            #     print("请先登录...")
            #     dou_yin.login() # 确保在操作前登录
            #     continue # 重新检查登录状态或直接继续

            if not dou_yin.is_login:  # 直接检查一次
                print("请先登录...")
                dou_yin.login()
                if not dou_yin.is_login:  # 如果登录失败则不继续
                    print("登录失败，无法继续操作。")
                    continue  # 回到操作选择

            if function_num == "1":
                dou_yin.search_account(operation_num)
            elif function_num == "2":
                dou_yin.search_video(operation_num)
        elif operation_num == "3":
            select_douyin_function()  # 返回 select_douyin_function
        else:
            print("输入有误")


def select_douyin_message_monitoring():
    while True:
        if not dou_yin.is_login:
            print("请先登录...")
            dou_yin.login()  # 尝试登录
            if not dou_yin.is_login:  # 如果登录仍然失败
                print("登录失败，无法进行私信回复设置。")
                return  # 或 select_douyin_function() 返回上一级
            # continue # 如果登录成功，不需要 continue，直接显示菜单

        print("\n私信自动回复功能:")  # 加个换行美观一些
        print("1.开始监控私信")
        print("2.停止监控私信")
        print("3.设置自定义回复消息")
        print("4.切换回复模式")
        print("5.切换调试模式")
        print("6.更新Coze凭证")
        print("7.设置AI回复风格")
        print("8.测试Coze API")
        print("9.返回上一级")
        monitoring_num = input("请选择操作:")

        if monitoring_num == "1":
            dou_yin.start_message_monitoring()
        elif monitoring_num == "2":
            dou_yin.stop_message_monitoring()
        elif monitoring_num == "3":
            custom_message = input("请输入自定义回复消息: ")
            dou_yin.set_custom_message(custom_message)
        elif monitoring_num == "4":
            print("回复模式:")
            print("1.AI智能回复")
            print("2.自定义消息回复")
            mode_num = input("请选择回复模式: ")
            if mode_num == "1":
                dou_yin.toggle_ai_reply(True)
            elif mode_num == "2":
                dou_yin.toggle_ai_reply(False)
            else:
                print("输入有误")
        elif monitoring_num == "5":
            print("调试模式:")
            print("1.开启调试")
            print("2.关闭调试")
            debug_num = input("请选择: ")
            if debug_num == "1":
                dou_yin.toggle_debug_mode(True)
            elif debug_num == "2":
                dou_yin.toggle_debug_mode(False)
            else:
                print("输入有误")
        elif monitoring_num == "6":
            print("更新Coze凭证:")
            token = input("请输入Coze令牌 (直接回车跳过): ")
            bot_id = input("请输入机器人ID (直接回车跳过): ")
            dou_yin.update_coze_credentials(token if token else None, bot_id if bot_id else None)
        elif monitoring_num == "7":
            print("AI回复风格:")
            print("1.高冷女主播")
            print("2.热情活泼")
            print("3.商务专业")
            print("4.自定义风格")
            style_num = input("请选择风格: ")
            if style_num == "1":
                dou_yin.set_system_prompt("你是高冷女主播，回复风格干脆简短，语气高冷但不失礼貌")
            elif style_num == "2":
                dou_yin.set_system_prompt("你是热情活泼的女主播，回复要充满感情，使用适当的表情符号，语气活泼亲切")
            elif style_num == "3":
                dou_yin.set_system_prompt("你是商务专业人士，回复要简洁专业，态度礼貌得体，语气沉稳可靠")
            elif style_num == "4":
                custom_prompt = input("请输入自定义风格提示词: ")
                dou_yin.set_system_prompt(custom_prompt)
            else:
                print("输入有误")
        elif monitoring_num == "8":
            try:
                # from utils.coze_client import CozeClient # CozeClient 实例已在 Douyin 类中
                print("测试Coze API连接...")
                # dou_yin.coze_token 和 dou_yin.coze_bot_id 是 Douyin 实例的属性
                # dou_yin.system_prompt 也是
                print(f"使用令牌: {dou_yin.coze_token[:5]}... Bot ID: {dou_yin.coze_bot_id}")
                test_message = "你好，请做个简单自我介绍"
                print(f"发送测试消息: {test_message} (使用当前系统提示词: {dou_yin.system_prompt[:30]}...)")
                # 直接使用 dou_yin 实例中的 coze_client
                if hasattr(dou_yin, 'coze_client') and dou_yin.coze_client is not None:
                    # 确保 coze_client 的 debug 模式与 dou_yin 一致
                    dou_yin.coze_client.debug_mode = dou_yin.debug_mode
                    response = dou_yin.coze_client.get_response(test_message, dou_yin.system_prompt)
                    print(f"收到回复: {response}")
                else:
                    print("错误: Douyin 实例中未找到 coze_client 或未初始化。")
                print("Coze API测试完成")
            except Exception as e:
                print(f"测试过程中出错: {e}")
                import traceback
                traceback.print_exc()
        elif monitoring_num == "9":
            select_douyin_function()  # 返回 select_douyin_function
            break  # 跳出当前while True循环
        else:
            print("输入有误")


select_platform()