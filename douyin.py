# FILE: douyin.py
import time
import requests
import json
import threading
import random
from queue import Queue
import re
import keyboard

from helium import (
    start_chrome, S, Text, wait_until, go_to, press, DOWN, RIGHT, UP, LEFT,
    ALT, CONTROL, DELETE, ENTER, ESCAPE, TAB, hover, click, write, find_all,
    get_driver, scroll_down, scroll_up
)
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException, \
    StaleElementReferenceException, WebDriverException

from ..load.load import Load as file_load
from ..operation.operation_douyin import Operation
from ..utils.coze_client import CozeClient


def execute_js(script, *args):
    driver = get_driver()
    if driver:
        try:
            return driver.execute_script(script, *args)
        except WebDriverException as e:
            print(f"  JS执行错误: {e}")
            return None
    print("错误：execute_js 无法获取 WebDriver 实例。")
    return None


VERSION = "3.0.4-coze-original-input"  # 版本号更新


class Douyin:

    def __init__(self, target_file_name, match_video_file_name, match_comment_file_name):
        print(f"初始化Douyin类 (版本 {VERSION})")
        self.is_login = False
        self.operate = Operation()
        self.link_items = file_load.load(target_file_name)
        self.match_video_items = file_load.load(match_video_file_name)
        self.match_comment_item_map = file_load.load_map(match_comment_file_name)

        self.coze_token = "pat_nYVxmCVmondwYo5pNhUHptda90JTBSNgVZyoKhtzon0hvQoZBaHg5KUl9juhd77k"
        self.coze_bot_id = "7488528105347448844"
        self.system_prompt = "你是智能助手，请根据我发送的抖音评论内容，回复一个简短、友好的回应。对于表情，请回复合适的表情；对于表情包，请回复合适的表情；对于文字评论，请回复相关且积极的回应。"

        self.coze_client = CozeClient(self.coze_token, self.coze_bot_id, False)
        self.debug_mode = False

        self.is_replying_running = False
        self.reply_thread = None
        self.max_videos_to_reply = 10
        self.max_replies_per_video_per_run = 3

        self.message_monitoring = False
        self.message_thread = None
        self.message_queue = Queue()
        self.custom_message = "你好，这是自动回复消息。"
        self.use_ai_reply = True
        print(f"Douyin类初始化完成 (版本 {VERSION})")
        self.predefined_replies = [
            "有事么",
            "谢谢，很可爱的表情",
            "谢谢你啦，我很高兴",
            "哈哈哈哈",
            "不错耶",
            "陪我聊聊可以么",
            "我们来聊天吧",
            "一起唠嗑吧~"
            "🌹🌹🌹"
            "😝😝"
        ]
        self.available_predefined_replies = list(self.predefined_replies)  # 创建一个可修改的副本
    def _browser_back(self):
        driver = get_driver()
        if not driver:
            print("  错误：无法获取 driver 实例来执行后退操作。")
            return
        ui_back_button_video_detail_xpath = "//div[@id='douyin-right-container']//span[./svg[path[contains(@d, 'M15.0703 4.92896L8.3528 11.6465')]]]"
        try:
            back_button_s_obj = S(ui_back_button_video_detail_xpath)
            if back_button_s_obj.exists() and back_button_s_obj.web_element.is_displayed():
                if self.debug_mode: print("  尝试点击UI返回按钮 (video detail to profile)...")
                click(back_button_s_obj)
                time.sleep(1.5)
                return
            if self.debug_mode: print("  UI返回按钮未找到或不适用，执行 Selenium driver.back()")
            driver.back()
            time.sleep(1.5)
        except Exception as e_sel_back:
            print(f"  执行返回操作时出错: {e_sel_back}")
            try:
                if self.debug_mode: print("  UI返回按钮点击失败或不适用，尝试执行 Selenium driver.back()作为后备。")
                driver.back()
                time.sleep(1.5)
            except Exception as e_driver_back_fallback:
                print(f"  执行 Selenium driver.back() 后备操作也失败: {e_driver_back_fallback}")

    def _navigate_to_url(self, url):
        try:
            driver = get_driver()
            if driver:
                driver.get(url)
                if self.debug_mode: print(f"  导航到: {url}")
                time.sleep(2.5)
            else:
                print(f"  错误：无法获取 driver 实例导航到 {url}。")
        except Exception as e_nav:
            print(f"  导航到 {url} 时出错: {e_nav}")

    def login(self):
        print("正在打开抖音网站...")
        try:
            start_chrome('https://www.douyin.com', headless=False)
            time.sleep(3)
            current_driver = get_driver()
            if not current_driver:
                print("错误：无法初始化浏览器驱动。")
                self.is_login = False
                return
            if S("//div[@data-e2e='feed-active-video']").exists() or S("//img[@alt='用户头像']").exists():
                print("检测到已登录或首页状态。")
                self._navigate_to_url("https://www.douyin.com/user/self")
                time.sleep(3)
                if S("//button[contains(text(),'编辑资料')]").exists() or S("//span[text()='作品']").exists():
                    self.is_login = True
                    print("已通过Cookie或之前会话登录。")
                    return
                else:
                    self._navigate_to_url("https://www.douyin.com")
                    time.sleep(2)
            print("等待用户手动扫码登录...")
            timeout_seconds = 120
            start_time = time.time()
            logged_in_indicator_found = False
            while time.time() - start_time < timeout_seconds:
                if S("//header//img[@alt='用户头像']").exists() or \
                        S("//div[@data-e2e='im-entry']").exists() or \
                        S("//a[contains(@href,'creator') and contains(text(),'投稿')]").exists() or \
                        (current_driver and current_driver.current_url.startswith("https://www.douyin.com/user/self")):
                    logged_in_indicator_found = True
                    break
                if Text('登录后免费畅享高清视频').exists() or Text('验证码登录').exists() or Text('扫码登录').exists():
                    if (time.time() - start_time) % 15 < 1:
                        print("请扫码登录...")
                time.sleep(2)
            if logged_in_indicator_found:
                self.is_login = True
                print("登录成功!")
                time.sleep(3)
                if not (current_driver and current_driver.current_url.startswith("https://www.douyin.com/user/self")):
                    self._navigate_to_url("https://www.douyin.com/user/self")
                    time.sleep(3)
            else:
                self.is_login = False
                print(f"登录超时或失败 ({timeout_seconds}秒).")
        except Exception as e:
            print(f"登录过程中发生错误: {e}")
            self.is_login = False

    def start_automated_comment_reply(self):
        if not self.is_login: print("错误：请先登录抖音。"); return
        if self.is_replying_running: print("自动评论回复已经在运行中。"); return
        self.is_replying_running = True
        self.reply_thread = threading.Thread(target=self._core_comment_reply_loop, daemon=True)
        self.reply_thread.start()
        print("自动评论回复流程已启动（后台线程）。按Q键可请求停止。")

    def stop_automated_comment_reply(self):
        if not self.is_replying_running: print("自动评论回复流程未运行。"); return
        print("收到停止请求，自动评论回复流程将在当前视频/评论处理完毕后停止...")
        self.is_replying_running = False
        if self.reply_thread and self.reply_thread.is_alive():
            self.reply_thread.join(timeout=30)
            if self.reply_thread.is_alive(): print("警告：回复线程在超时后仍未结束。")
        self.reply_thread = None
        print("自动评论回复流程已停止。")

    def _get_video_links_and_filter_pinned(self):
        # ... (此方法与之前版本相同，保持不变) ...
        if self.debug_mode: print("  执行 _get_video_links_and_filter_pinned...")
        current_driver = get_driver()
        if not current_driver:
            print("错误：无法获取浏览器驱动实例。")
            return []
        profile_url = "https://www.douyin.com/user/self?from_tab_name=main&tab_name=post"
        if not (current_driver.current_url.startswith(
                "https://www.douyin.com/user/self") and "tab_name=post" in current_driver.current_url):
            if self.debug_mode: print(f"  当前不在目标个人主页作品页，导航至: {profile_url}")
            self._navigate_to_url(profile_url)
            wait_until(S("//div[@data-e2e='user-post-list']").exists, timeout_secs=10, interval_secs=0.5)
        for _ in range(3):
            if not self.is_replying_running: return []
            if self.debug_mode: print("    滚动页面加载更多视频...")
            execute_js("window.scrollBy(0, document.body.scrollHeight * 0.3);")
            time.sleep(1.5)
        video_list_items_xpath = "//div[@data-e2e='user-post-list']/ul/li[contains(@class, 'niBfRBgX')]"
        video_list_items_fallback_xpath = "//div[@data-e2e='user-post-list']/ul/li"
        raw_li_elements_web = []
        try:
            raw_li_elements_web = current_driver.find_elements("xpath", video_list_items_xpath)
            if not raw_li_elements_web:
                if self.debug_mode: print(f"  主视频列表XPath '{video_list_items_xpath}' 未找到元素, 尝试备选XPath...")
                raw_li_elements_web = current_driver.find_elements("xpath", video_list_items_fallback_xpath)
        except Exception as e:
            print(f"  查找视频列表项时出错: {e}")
            return []
        if self.debug_mode: print(f"  初步找到 {len(raw_li_elements_web)} 个视频列表项 (WebElements)。")
        non_pinned_video_link_elements = []
        for li_element_web in raw_li_elements_web:
            if not self.is_replying_running: break
            is_pinned = False
            try:
                pinned_tag_xpath = ".//div[contains(@class, 'user-video-tag')]//div[text()='置顶'] | .//div[contains(@class, 'TQTCdYql')]//div[text()='置顶']"
                pinned_tag = li_element_web.find_element("xpath", pinned_tag_xpath)
                if pinned_tag.is_displayed():
                    is_pinned = True
                    if self.debug_mode: print("    发现一个置顶视频，将排除。")
            except NoSuchElementException:
                is_pinned = False
            except Exception as e_pin:
                if self.debug_mode: print(f"    检查置顶时发生错误: {e_pin}")
                is_pinned = False
            if not is_pinned:
                try:
                    video_a_tag_web_element = li_element_web.find_element("xpath", ".//a[contains(@href, '/video/')]")
                    video_href = video_a_tag_web_element.get_attribute('href')
                    if video_href and "video/" in video_href:
                        if not any(existing_el.get_attribute('href') == video_href for existing_el in
                                   non_pinned_video_link_elements):
                            non_pinned_video_link_elements.append(video_a_tag_web_element)
                            if self.debug_mode: print(f"    添加非置顶视频链接: {video_href}")
                except NoSuchElementException:
                    if self.debug_mode: print("    列表项中未找到视频链接<a>标签。")
                except Exception as e_link:
                    if self.debug_mode: print(f"    获取视频链接时出错: {e_link}")
            if len(non_pinned_video_link_elements) >= self.max_videos_to_reply:
                if self.debug_mode: print(f"    已找到 {self.max_videos_to_reply} 个非置顶视频，停止收集。")
                break
        if self.debug_mode: print(
            f"  _get_video_links_and_filter_pinned 返回 {len(non_pinned_video_link_elements)} 个非置顶视频WebElement。")
        return non_pinned_video_link_elements

    def _core_comment_reply_loop(self):
        # ... (此方法与之前版本相同，保持不变) ...
        print("核心评论回复循环已启动。")
        current_driver = get_driver()
        if not current_driver:
            print("错误：浏览器驱动未初始化。")
            self.is_replying_running = False
            return
        videos_successfully_processed_in_run = 0
        for video_idx_in_plan in range(self.max_videos_to_reply):
            if not self.is_replying_running:
                print(f"流程被用户停止 (在处理计划中的视频 {video_idx_in_plan + 1} 之前)。")
                break
            if videos_successfully_processed_in_run >= self.max_videos_to_reply:
                print(f"已成功处理 {videos_successfully_processed_in_run} 个视频，达到本次运行上限。")
                break
            print(
                f"\n--- 准备处理个人主页的第 {video_idx_in_plan + 1} 个非置顶视频 (已成功处理 {videos_successfully_processed_in_run} 个) ---")
            current_profile_video_elements = self._get_video_links_and_filter_pinned()
            if not current_profile_video_elements:
                print(
                    f"错误：在尝试处理第 {video_idx_in_plan + 1} 个视频前，无法从个人主页获取视频列表。可能无更多非置顶视频。")
                break
            if video_idx_in_plan >= len(current_profile_video_elements):
                print(
                    f"错误：计划处理的视频索引 {video_idx_in_plan} 超出现有非置顶视频数量 {len(current_profile_video_elements)}。已处理完所有可用视频。")
                break
            video_a_element_to_process = current_profile_video_elements[video_idx_in_plan]
            video_href_for_log = "[href获取失败]"
            try:
                video_href_for_log = video_a_element_to_process.get_attribute('href')
            except Exception as e_href:
                print(f"  获取视频链接 (href) 失败: {e_href}. 跳过此轮。")
                self._navigate_to_url("https://www.douyin.com/user/self?from_tab_name=main&tab_name=post");
                time.sleep(2)
                continue
            print(f"  步骤1: 点击“视频链接”: {video_href_for_log}")
            try:
                execute_js("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                           video_a_element_to_process)
                time.sleep(0.7)
                click(video_a_element_to_process)
                time.sleep(4)
            except Exception as e_click:
                print(f"  点击视频链接 ({video_href_for_log}) 时发生错误: {e_click}. 跳过此视频。")
                self._navigate_to_url("https://www.douyin.com/user/self?from_tab_name=main&tab_name=post");
                time.sleep(2)
                continue
            print("  步骤2: 点击“评论图标”")
            comment_icon_selectors = ["//div[@data-e2e='feed-comment-icon']",
                                      "//div[@data-e2e='video-player-aside-comp-comment-icon']",
                                      "//div[contains(@class, 'action-item-comment') or contains(@class, 'videoComment') or contains(@class, 'bar-item-comment') or @data-e2e='video-info-comment']//div[.//svg[path]]"]
            comment_icon_s_obj = None
            for selector in comment_icon_selectors:
                temp_s_obj = S(selector)
                if temp_s_obj.exists():
                    try:
                        if temp_s_obj.web_element.is_displayed() and temp_s_obj.web_element.is_enabled():
                            comment_icon_s_obj = temp_s_obj
                            if self.debug_mode: print(f"    找到评论图标使用选择器: {selector}")
                            break
                    except Exception:
                        pass
            if comment_icon_s_obj:
                try:
                    execute_js("arguments[0].click();", comment_icon_s_obj.web_element)
                    if self.debug_mode: print("    评论图标点击成功。")
                    time.sleep(1)
                    try:
                        wait_until(S("//div[@data-e2e='comment-list']").exists, timeout_secs=15, interval_secs=0.5)
                        if self.debug_mode: print("    评论列表容器已出现。")
                    except TimeoutException:
                        print("    等待评论列表容器超时。可能无评论或加载失败。")
                        self._browser_back();
                        time.sleep(2);
                        videos_successfully_processed_in_run += 1;
                        continue
                    time.sleep(1.5)
                except Exception as e_comm_icon_click:
                    print(f"    点击评论图标失败: {e_comm_icon_click}. 跳过此视频。")
                    self._browser_back();
                    time.sleep(2);
                    videos_successfully_processed_in_run += 1;
                    continue
            else:
                print("    未找到可点击的评论图标。跳过此视频。")
                self._browser_back();
                time.sleep(2);
                videos_successfully_processed_in_run += 1;
                continue
            print("  步骤3: 滚动“下拉式滚动条”加载评论")
            comment_scroll_container_xpath = "//div[@data-e2e='comment-list' and contains(@class,'comment-mainContent')]"
            comment_scroll_container_s_obj = S(comment_scroll_container_xpath)
            if comment_scroll_container_s_obj.exists():
                for i in range(5):
                    if not self.is_replying_running: break
                    execute_js("arguments[0].scrollTop = arguments[0].scrollHeight;",
                               comment_scroll_container_s_obj.web_element)
                    if self.debug_mode: print(f"    评论区滚动第 {i + 1} 次")
                    time.sleep(2)
            else:
                if self.debug_mode: print("    警告：未找到评论区滚动容器。")
            comment_items_xpath = "//div[@data-e2e='comment-item']"
            all_comment_s_objects = find_all(S(comment_items_xpath))
            print(f"  找到 {len(all_comment_s_objects)} 个评论项。")
            if not all_comment_s_objects:
                print("    未找到任何评论项进行处理。")
                self._browser_back();
                time.sleep(2);
                videos_successfully_processed_in_run += 1;
                continue
            replied_in_this_video_count = 0
            processed_comment_authors = set()
            for comment_s_obj_idx, comment_s_obj in enumerate(all_comment_s_objects):
                if not self.is_replying_running: break
                if replied_in_this_video_count >= self.max_replies_per_video_per_run:
                    print(f"    已达到此视频的回复上限 ({self.max_replies_per_video_per_run})。")
                    break
                comment_web_element = comment_s_obj.web_element
                try:
                    execute_js("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", comment_web_element)
                    time.sleep(0.8)
                except StaleElementReferenceException:
                    if self.debug_mode: print(f"    滚动到评论项 {comment_s_obj_idx + 1} 时元素失效，跳过。")
                    continue
                except Exception as scroll_err:
                    if self.debug_mode: print(f"    滚动到评论项失败: {scroll_err}")
                print(f"\n  处理第 {comment_s_obj_idx + 1} 个评论项...")
                author_tag_xpath = ".//span[contains(@class,'comment-item-tag-text') and normalize-space(text())='作者']"
                try:
                    author_tag = comment_web_element.find_element("xpath", author_tag_xpath)
                    if author_tag.is_displayed():
                        if self.debug_mode: print(f"    评论 {comment_s_obj_idx + 1}: 作者的评论，跳过。")
                        continue
                except NoSuchElementException:
                    pass
                except Exception as e_author_check:
                    if self.debug_mode: print(f"    检查作者标签时出错: {e_author_check}")
                user_name_xpath = ".//a[contains(@href,'/user/')][1]//span[contains(@class,'E7y2ZDk0')]"
                user_name = "[未知用户]"
                try:
                    user_name_el = comment_web_element.find_element("xpath", user_name_xpath)
                    user_name = user_name_el.text.strip()
                    if not user_name: user_name = "[空用户名]"
                    if user_name in processed_comment_authors:
                        if self.debug_mode: print(
                            f"    评论 {comment_s_obj_idx + 1}: 已回复过用户 '{user_name}' (在此视频中)，跳过。")
                        continue
                except NoSuchElementException:
                    if self.debug_mode: print(f"    评论 {comment_s_obj_idx + 1}: 未找到用户名元素。为避免重复，跳过。")
                    continue
                except StaleElementReferenceException:
                    if self.debug_mode: print(f"    获取用户名时元素失效，跳过。")
                    continue
                except Exception as e_uname:
                    if self.debug_mode: print(f"    获取评论用户名时出错: {e_uname}，跳过。")
                    continue
                if self.debug_mode: print(f"    用户名: {user_name}")
                print("    步骤4: 查看“评论内容”")
                comment_text, comment_type = self._extract_comment_content_and_type(comment_web_element)
                if comment_type == "未知" or comment_type == "空评论" or "[评论解析出错]" in comment_text:
                    if self.debug_mode: print(f"      无法解析或空评论，跳过。类型: {comment_type}, 内容: {comment_text}")
                    continue
                if self.debug_mode: print(f"      评论类型='{comment_type}', 内容='{comment_text[:80]}...'")
                coze_input_map = {"文本": f"收到文本评论：'{comment_text}'", "表情": f"收到表情评论：{comment_text}",
                                  "表情包": f"收到表情包评论：{comment_text}"}
                coze_input = coze_input_map.get(comment_type, f"收到评论：'{comment_text}'")
                ai_response = self.coze_client.get_response(coze_input, self.system_prompt)
                if not ai_response or "AI回复获取失败" in ai_response:
                    if self.debug_mode: print(f"      Coze机器人回复无效: '{ai_response}'。跳过。")
                    continue
                if self.debug_mode: print(f"      Coze回复: {ai_response[:50]}...")
                print("    步骤5: 点击“评论按钮” (回复)")
                reply_button_on_comment_xpath = ".//div[contains(@class,'uh012Eth') and .//span[normalize-space(text())='回复']]"
                try:
                    reply_button_el = comment_web_element.find_element("xpath", reply_button_on_comment_xpath)
                    if self.debug_mode: print("      找到评论上的'回复'按钮，点击...")
                    execute_js("arguments[0].click();", reply_button_el)
                    time.sleep(1.8)
                except NoSuchElementException:
                    if self.debug_mode: print("      未找到评论上的'回复'按钮。")
                    continue
                except Exception as e_reply_btn_click:
                    if self.debug_mode: print(f"      点击评论上的'回复'按钮失败: {e_reply_btn_click}。跳过。")
                    continue
                print("    步骤6: 输入回复到“回复评论区域”")
                reply_input_xpath = "//div[contains(@class, 'comment-input-container-inside-comment-item')]//div[@contenteditable='true'] | //div[contains(@class,'public-DraftEditor-content') and @contenteditable='true']"
                reply_input_s_obj = S(reply_input_xpath)
                if reply_input_s_obj.exists():
                    try:
                        if self.debug_mode: print("      找到回复输入框，输入内容...")
                        click(reply_input_s_obj)
                        time.sleep(0.4)
                        reply_input_s_obj.web_element.send_keys(CONTROL + 'a');
                        time.sleep(0.2)
                        reply_input_s_obj.web_element.send_keys(DELETE);
                        time.sleep(0.2)
                        write(ai_response, into=reply_input_s_obj)
                        time.sleep(0.7)
                    except Exception as e_write_reply:
                        if self.debug_mode: print(f"      输入回复内容失败: {e_write_reply}。尝试按ESC。")
                        press(ESCAPE);
                        time.sleep(0.5);
                        continue
                else:
                    print("      未找到回复输入框。跳过。")
                    press(ESCAPE);
                    time.sleep(0.5);
                    continue
                print("    步骤7: 点击“发送按钮”")
                send_button_xpath = "//div[contains(@class, 'comment-input-container-inside-comment-item')]//button[.//svg[path[contains(@d,'M17.5 30C') and @fill='#FE2C55']]] | //div[contains(@class, 'comment-input-container-inside-comment-item')]//button[.//span[text()='发布']]"
                send_button_s_obj = S(send_button_xpath)
                if send_button_s_obj.exists() and send_button_s_obj.web_element.is_enabled():
                    try:
                        if self.debug_mode: print("      找到发送按钮，点击...")
                        click(send_button_s_obj)
                        time.sleep(2.5)
                        print(f"      对用户 '{user_name}' 的评论 '{comment_text[:30]}...' 回复成功!")
                        replied_in_this_video_count += 1
                        processed_comment_authors.add(user_name)
                    except Exception as e_send_btn_click:
                        if self.debug_mode: print(f"      点击发送按钮失败: {e_send_btn_click}。尝试按ESC。")
                        press(ESCAPE);
                        time.sleep(0.5)
                else:
                    print("      未找到可用的发送按钮或按钮不可点击。尝试按ESC。")
                    press(ESCAPE);
                    time.sleep(0.5)
            print(f"  步骤8: “返回按钮” - 当前视频评论处理完毕 ({video_href_for_log})，返回主页...")
            self._browser_back()
            time.sleep(3.5)
            videos_successfully_processed_in_run += 1
            if videos_successfully_processed_in_run < self.max_videos_to_reply and self.is_replying_running:
                wait_time = random.uniform(7, 15)
                print(f"    等待 {wait_time:.1f} 秒后处理下一个视频...")
                time.sleep(wait_time)
        print(f"\n核心评论回复循环结束。总共成功处理了 {videos_successfully_processed_in_run} 个视频。")
        self.is_replying_running = False

    def _extract_comment_content_and_type(self, comment_item_element):
        # ... (此方法与之前版本相同，保持不变) ...
        content_str = ""
        content_type = "未知"
        try:
            sticker_elements = comment_item_element.find_elements("xpath", ".//img[contains(@class, 'AXaKGat3')]")
            if sticker_elements:
                sticker_alt = sticker_elements[0].get_attribute('alt')
                sticker_src_name = ""
                try:
                    sticker_src_name_match = re.search(r'/([^/?]+)(\?|$)', sticker_elements[0].get_attribute('src'))
                    if sticker_src_name_match: sticker_src_name = sticker_src_name_match.group(1)
                except:
                    pass
                content_str = f"[表情包:{sticker_alt or sticker_src_name or '未知表情包'}]"
                content_type = "表情包"
                if self.debug_mode: print(f"    评论内容解析: 表情包 - {content_str}")
                return content_str, content_type
            content_container = None
            try:
                content_container = comment_item_element.find_element("xpath",
                                                                      ".//div[contains(@class, 'LvAtyU_f')] | .//div[@data-e2e='comment-content-container']")
            except NoSuchElementException:
                if self.debug_mode: print("    未找到标准评论内容容器 LvAtyU_f 或 data-e2e。尝试备用。")
                try:
                    text_elements = comment_item_element.find_elements("xpath", ".//span[normalize-space()]")
                    if text_elements:
                        raw_text = " ".join([el.text for el in text_elements if
                                             el.text and not el.find_elements("xpath",
                                                                              ".//ancestor::*[contains(@class, 'comment-item-tag') or contains(@class, 'GOkWHE6S')]")])
                        content_str = raw_text.strip()
                        if content_str:
                            content_type = "文本"
                            if self.debug_mode: print(f"    评论内容解析 (备用直接文本): {content_str}")
                            return content_str, content_type
                except:
                    pass
                return "[无法解析的评论]", "未知"
            script = """
            let container = arguments[0]; let parts = []; if (!container) return { text: '', type: '未知' };
            let hasText = false; let hasEmoji = false; let hasSticker = false;
            function extractContent(node) {
                if (node.nodeType === Node.TEXT_NODE) { let text = node.textContent.trim(); if (text) { parts.push(text); hasText = true; } }
                else if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.tagName.toLowerCase() === 'img') {
                        if (node.classList.contains('nxcdnPYU') && node.alt && node.alt.startsWith('[')) { parts.push(node.alt); hasEmoji = true; }
                        else if (node.classList.contains('AXaKGat3')) {
                             let stickerAlt = node.alt || ''; let stickerSrcName = '';
                             try { let match = node.src.match(/\/([^\/?]+)(\?|$)/); if (match) stickerSrcName = match[1]; } catch(e){}
                             parts.push(`[表情包:${stickerAlt || stickerSrcName || '未知表情包'}]`); hasSticker = true;
                        }
                    } else if (node.tagName.toLowerCase() === 'br') { if (parts.length > 0 && !parts[parts.length -1].endsWith(' ')) { parts.push(' '); } }
                    if (node.childNodes && node.childNodes.length > 0 && node.style.display !== 'none' && !node.classList.contains('comment-item-reply-container') && !node.classList.contains('GOkWHE6S') && !node.classList.contains('qfuN5lMO')) {
                        for (let i = 0; i < node.childNodes.length; i++) { extractContent(node.childNodes[i]); }
                    }
                }
            }
            extractContent(container);
            let finalType = '未知';
            if (hasSticker) finalType = '表情包'; else if (hasText) finalType = '文本'; else if (hasEmoji) finalType = '表情'; else if (parts.length > 0) finalType = '文本';
            return { text: parts.join(' ').trim().replace(/\s+/g, ' '), type: finalType };
            """
            extracted_result = execute_js(script, content_container)
            if extracted_result:
                content_str = extracted_result.get('text', '');
                content_type = extracted_result.get('type', '未知')
                if not content_str and content_type != '表情包': content_type = "空评论"; content_str = "[空评论]"
            else:
                content_str = "[评论解析出错_JS]"; content_type = "未知"
            if self.debug_mode: print(f"    评论内容解析 (JS): 类型='{content_type}', 内容='{content_str}'")
        except Exception as e:
            if self.debug_mode: print(f"    解析评论内容时严重出错: {e}")
            content_str = "[评论解析出错_Py]";
            content_type = "未知"
        if not content_str.strip() and content_type != "表情包": content_type = "空评论"; content_str = "[空评论]"
        return content_str, content_type

    def search_account(self, operation_num):
        # ... (此方法与之前版本相同，保持不变) ...
        print("警告：search_account 方法与新的自动回复流程可能冲突。")
        for link_idx, link in enumerate(self.link_items):
            if not self.is_replying_running and not self.message_monitoring:
                if not keyboard.is_pressed('q'):
                    pass
                else:
                    print("旧流程被Q键停止"); break
            print(f"处理账号链接 (旧流程) {link_idx + 1}/{len(self.link_items)}: {link}")
            go_to(link);
            time.sleep(2.5)
            self.operate.user_click_follow()
            print("旧流程处理账号链接完成一个。")

    def search_video(self, operation_num):
        # ... (此方法与之前版本相同，保持不变) ...
        print("警告：search_video 方法与新的自动回复流程可能冲突。")
        for link_idx, link in enumerate(self.link_items):
            if not self.is_replying_running and not self.message_monitoring:
                if not keyboard.is_pressed('q'):
                    pass
                else:
                    print("旧流程被Q键停止"); break
            print(f"处理视频链接 (旧流程) {link_idx + 1}/{len(self.link_items)}: {link}")
            go_to(link);
            time.sleep(2.5)
            if operation_num == "1":
                self.operate.video_click_like()
                self.operate.video_comment(self.match_comment_item_map)
            elif operation_num == "2":
                self.operate.video_discuss_comment(self.match_comment_item_map)
        print("旧流程处理视频链接完成。")

    def set_custom_message(self, message):
        self.custom_message = message
        print(f"已设置自定义回复消息: {message}")

    def set_system_prompt(self, prompt):
        self.system_prompt = prompt
        print(f"已设置AI系统提示词: {prompt}")

    def toggle_ai_reply(self, use_ai):
        self.use_ai_reply = use_ai
        mode = "AI回复" if use_ai else "自定义消息回复"
        print(f"私信回复已切换到{mode}模式")

    def toggle_debug_mode(self, enable_debug):
        self.debug_mode = enable_debug
        if hasattr(self, 'coze_client') and self.coze_client:
            self.coze_client.debug_mode = enable_debug
        mode = "开启" if enable_debug else "关闭"
        print(f"调试模式已{mode}")

    def update_coze_credentials(self, token=None, bot_id=None):
        if token: self.coze_token = token
        if bot_id: self.coze_bot_id = bot_id
        self.coze_client = CozeClient(self.coze_token, self.coze_bot_id, self.debug_mode)
        print("Coze凭证已更新")

    def start_message_monitoring(self):
        if not self.is_login: print("请先登录抖音！"); return
        if self.message_monitoring: print("私信监控已在运行！"); return
        self.message_monitoring = True
        self.message_thread = threading.Thread(target=self._monitor_messages, daemon=True)
        self.message_thread.start()
        if not (hasattr(self,
                        'message_process_thread') and self.message_process_thread and self.message_process_thread.is_alive()):
            self.message_process_thread = threading.Thread(target=self._process_message_queue, daemon=True)
            self.message_process_thread.start()
        print("开始监控私信...")

    def stop_message_monitoring(self):
        if not self.message_monitoring: print("私信监控未运行！"); return
        self.message_monitoring = False
        if hasattr(self, 'message_queue'): self.message_queue.put(None)
        if self.message_thread and self.message_thread.is_alive(): self.message_thread.join(timeout=5)
        if hasattr(self,
                   'message_process_thread') and self.message_process_thread and self.message_process_thread.is_alive(): self.message_process_thread.join(
            timeout=5)
        self.message_thread = None
        self.message_process_thread = None
        print("停止监控私信...")

    def _monitor_messages(self):
        # ... (此方法与之前版本相同，包含未读消息检测的更新) ...
        last_check_time = 0
        while self.message_monitoring:
            try:
                if time.time() - last_check_time < 10: time.sleep(1); continue
                last_check_time = time.time()
                if self.debug_mode: print("检查私信 (私信监控线程)...")
                message_button_entry = S("//div[@data-e2e='im-entry']")
                if not message_button_entry.exists():
                    if self.debug_mode: print("  找不到私信入口按钮。"); time.sleep(5); continue
                hover(message_button_entry);
                time.sleep(1.5)
                scroll_container_im_list = S("//div[@class='iXcuFCYr'] | //div[@data-e2e='im-list-container']")
                if not scroll_container_im_list.exists():
                    if self.debug_mode: print("  找不到私信列表滚动容器。")
                    try:
                        click(message_button_entry); time.sleep(0.5)
                    except:
                        pass
                    time.sleep(2)
                    scroll_container_im_list = S("//div[@class='iXcuFCYr'] | //div[@data-e2e='im-list-container']")
                    if not scroll_container_im_list.exists(): time.sleep(5); continue
                unread_item_container_selectors = ["//div[@data-e2e='conversation-item']"]
                unread_message_items_s_obj = []
                for item_container_selector in unread_item_container_selectors:
                    temp_items_s_objects = find_all(S(item_container_selector))
                    if self.debug_mode: print(
                        f"  使用会话项选择器 '{item_container_selector}', 原始找到 {len(temp_items_s_objects)} 个会话项。")
                    valid_unread_items = []
                    for item_s in temp_items_s_objects:
                        try:
                            is_item_unread = False
                            badge_count_xpath_within_item = ".//span[contains(@class, 'semi-badge-count')]"
                            try:
                                badge_el = item_s.web_element.find_element("xpath", badge_count_xpath_within_item)
                                if badge_el.is_displayed():
                                    badge_text = badge_el.text.strip()
                                    if self.debug_mode: print(
                                        f"    检查项: 找到 'semi-badge-count' 元素，文本='{badge_text}'")
                                    if badge_text and badge_text != '0': is_item_unread = True
                            except NoSuchElementException:
                                if self.debug_mode: print(
                                    f"    检查项: 在会话项内未找到 '{badge_count_xpath_within_item}'。")
                            if is_item_unread:
                                valid_unread_items.append(item_s)
                                if self.debug_mode: print(f"      ==> 有效未读项确认。")
                        except StaleElementReferenceException:
                            if self.debug_mode: print("    检查未读项时遇到StaleElement，跳过此项。")
                        except Exception as e_val:
                            if self.debug_mode: print(f"    验证单个未读项时出错: {e_val}")
                    if valid_unread_items:
                        unread_message_items_s_obj = valid_unread_items
                        if self.debug_mode: print(
                            f"  通过主项选择器 '{item_container_selector}' 找到并确认 {len(unread_message_items_s_obj)} 个有效未读会话。")
                        break
                if unread_message_items_s_obj:
                    if self.debug_mode: print(f"  发现 {len(unread_message_items_s_obj)} 个未读私信会话。")
                    for i in range(len(unread_message_items_s_obj)):
                        self.message_queue.put({"type": "unread_index", "index": i})
                        if self.debug_mode: print(f"    将未读索引 {i} 添加到队列。")
                else:
                    if self.debug_mode: print("  当前视图未发现未读私信。")
            except StaleElementReferenceException:
                if self.debug_mode: print("  私信监控中遇到StaleElement，将重试。")
            except Exception as e:
                print(f"监控私信时出错: {e}")
            try:
                body_s = S("/html/body");
                if body_s.exists(): hover(body_s); time.sleep(0.5)
            except:
                pass
            time.sleep(1)

    def _process_message_queue(self):
        # ... (此方法与之前版本相同，保持不变) ...
        while True:
            try:
                queue_item = self.message_queue.get()
                if queue_item is None:
                    if self.debug_mode: print("  消息处理队列收到退出信号。")
                    self.message_queue.task_done();
                    break
                if isinstance(queue_item, dict) and queue_item.get("type") == "unread_index":
                    idx = queue_item.get("index")
                    if self.message_monitoring:
                        self._process_single_message(idx)
                    else:
                        if self.debug_mode: print(f"  监控已停止，丢弃队列消息 (索引 {idx})。")
                self.message_queue.task_done()
            except Exception as e:
                print(f"处理消息队列时出错: {e}")
                if hasattr(self.message_queue, 'task_done'): self.message_queue.task_done()
                time.sleep(1)

    def _process_single_message(self, idx):
        if self.debug_mode: print(f"\n--- 处理排队的第 {idx + 1} 条未读私信 ---")
        try:
            message_button_entry = S("//div[@data-e2e='im-entry']")
            if not message_button_entry.exists():
                print("  找不到私信入口按钮。无法处理。");
                return

            if self.debug_mode: print("  重新悬停/点击私信入口以确保列表可见...")
            hover(message_button_entry);
            time.sleep(0.5)
            chat_list_container = S("//div[@data-e2e='im-list-container'] | //div[@class='iXcuFCYr']")
            if not chat_list_container.exists() or not chat_list_container.web_element.is_displayed():
                click(message_button_entry);
                time.sleep(1.5)

            unread_item_container_selectors_in_process = ["//div[@data-e2e='conversation-item']"]
            target_message_s_item = None
            for item_container_selector in unread_item_container_selectors_in_process:
                current_unread_s_items_candidates = find_all(S(item_container_selector))
                if self.debug_mode: print(
                    f"    在 _process_single_message 中，使用选择器 '{item_container_selector}' 找到 {len(current_unread_s_items_candidates)} 个候选会话项。")
                confirmed_unread_s_items = []
                for s_item_candidate in current_unread_s_items_candidates:
                    try:
                        is_candidate_unread = False
                        badge_count_xpath_within_item = ".//span[contains(@class, 'semi-badge-count')]"
                        try:
                            badge_el = s_item_candidate.web_element.find_element("xpath", badge_count_xpath_within_item)
                            if badge_el.is_displayed():
                                badge_text = badge_el.text.strip()
                                if badge_text and badge_text != '0': is_candidate_unread = True
                        except NoSuchElementException:
                            pass
                        if is_candidate_unread and s_item_candidate.web_element.is_displayed():
                            confirmed_unread_s_items.append(s_item_candidate)
                    except Exception as e_confirm:
                        if self.debug_mode: print(
                            f"      确认单个未读项时出错 (in _process_single_message): {e_confirm}")
                if idx < len(confirmed_unread_s_items):
                    target_message_s_item = confirmed_unread_s_items[idx]
                    if self.debug_mode: print(
                        f"    成功定位到目标未读项 (队列索引 {idx}) 使用选择器 '{item_container_selector}'。")
                    break
                else:
                    if self.debug_mode: print(
                        f"    队列索引 {idx} 超出当前找到的 {len(confirmed_unread_s_items)} 个确认未读项 (使用选择器 '{item_container_selector}')。")

            if not target_message_s_item or not target_message_s_item.exists():
                print(f"  未能重新定位到第 {idx + 1} 条未读私信项。可能已被读取或列表变化。")
                try:
                    S("/html/body").web_element.click();
                    time.sleep(0.5)
                except:
                    pass
                return

            if self.debug_mode: print("    点击目标未读项进入聊天...")
            try:
                click(target_message_s_item);
                time.sleep(2.5)
            except Exception as e_click_unread:
                print(f"    点击未读项时出错: {e_click_unread}");
                return

            # --- START: 用户消息提取逻辑 ---
            extracted_user_message = "你好"  # 默认值，如果提取失败
            extraction_failed_or_empty = True

            if self.debug_mode: print("      获取用户消息内容...")
            try:
                latest_pre_text = ""
                other_message_pre_selectors = [
                    "//div[contains(@class,'message-item-other')][last()]//pre",
                ]
                found_actual_message = False
                for selector in other_message_pre_selectors:
                    pre_elements = find_all(S(selector))
                    if pre_elements:
                        latest_pre_text = pre_elements[-1].web_element.text.strip()
                        if latest_pre_text:
                            if self.debug_mode: print(f"        通过通用 <pre> 选择器找到内容: {latest_pre_text}")
                            if not (
                                    "加入了群聊" in latest_pre_text or "分享[" in latest_pre_text or "发来一个[表情]" in latest_pre_text):
                                extracted_user_message = latest_pre_text
                                extraction_failed_or_empty = False
                                found_actual_message = True
                                break

                if not found_actual_message:  # 如果通用 <pre> 未找到有效内容
                    if self.debug_mode: print("        通用 <pre> 未提取到有效消息，尝试特定 XPath...")
                    message_elements_xpath1 = find_all(
                        S("//*[@id='messageContent']/div/div[3]/div/div/div[2]/div[1]/div/div/div/div/span"))
                    if message_elements_xpath1:
                        temp_msg = message_elements_xpath1[-1].web_element.text.strip()
                        if temp_msg and not ("加入了群聊" in temp_msg or "分享[" in temp_msg):
                            extracted_user_message = temp_msg
                            extraction_failed_or_empty = False
                            found_actual_message = True
                            if self.debug_mode: print(f"        通过特定 XPath 1 找到内容: {extracted_user_message}")

                    if not found_actual_message:
                        message_elements_xpath2 = find_all(
                            S("//*[@id='messageContent']/div/div[5]/div/div/div[2]/div[1]/div[2]/div/div/div/div[1]/span"))
                        if message_elements_xpath2:
                            temp_msg = message_elements_xpath2[-1].web_element.text.strip()
                            if temp_msg and not ("加入了群聊" in temp_msg or "分享[" in temp_msg):
                                extracted_user_message = temp_msg
                                extraction_failed_or_empty = False
                                # found_actual_message = True # No need to set again
                                if self.debug_mode: print(
                                    f"        通过特定 XPath 2 找到内容: {extracted_user_message}")

                if extracted_user_message.startswith("{}"):  # 移除可能的前缀
                    extracted_user_message = extracted_user_message[2:]
                    if self.debug_mode: print(f"        移除前缀后的消息: {extracted_user_message}")

                if extraction_failed_or_empty:  # 如果所有尝试都失败或内容无效
                    if self.debug_mode: print(
                        f"        所有提取尝试均失败或消息无效，视为默认情况处理。实际提取: '{extracted_user_message}'")
                    extracted_user_message = "你好"  # 确保在这种情况下也是“你好”
                else:
                    if self.debug_mode: print(f"      最终获取到的用户消息: {repr(extracted_user_message)}")

            except Exception as me:
                if self.debug_mode: print(f"      获取用户消息过程中发生错误: {me}")
                extracted_user_message = "你好"  # 发生异常时，也视为默认情况
                extraction_failed_or_empty = True  # 标记为提取失败
                if self.debug_mode: print(f"      因异常，视为默认情况处理。")
            # --- END: 用户消息提取逻辑 ---

            ai_reply_content = ""  # 初始化回复内容

            # 判断是否使用预设话术
            # 条件：1. AI回复模式开启； 2. 提取到的用户消息是“你好” (或提取失败/无效时等同于“你好”)
            if self.use_ai_reply and extracted_user_message.strip() == "你好":
                if self.debug_mode: print("      检测到用户消息为“你好”或提取失败，使用预设话术。")
                if not self.available_predefined_replies:  # 如果可用列表为空
                    if self.debug_mode: print("        预设话术已用完，重新填充列表。")
                    self.available_predefined_replies = list(self.predefined_replies)  # 重新填充

                if self.available_predefined_replies:  # 再次检查以防万一
                    chosen_reply = random.choice(self.available_predefined_replies)
                    ai_reply_content = chosen_reply
                    self.available_predefined_replies.remove(chosen_reply)  # 从可用列表中移除，实现不重复
                    if self.debug_mode: print(
                        f"        选择预设回复: '{ai_reply_content}' (剩余可用: {len(self.available_predefined_replies)})")
                else:  # 理论上不会到这里，因为上面会重新填充
                    if self.debug_mode: print("        错误：预设话术列表为空且无法重新填充。使用默认AI。")
                    # 回退到调用Coze处理“你好”
                    ai_reply_content = self.coze_client.get_response(extracted_user_message, self.system_prompt)
            elif self.use_ai_reply:  # 用户消息不是“你好”，正常调用Coze
                if self.debug_mode: print(f"      用户消息为 '{extracted_user_message[:30]}...'，调用Coze API。")
                if self.debug_mode: print(f"      AI回复模式 (系统提示: '{self.system_prompt[:30]}...')")
                ai_reply_content = self.coze_client.get_response(extracted_user_message, self.system_prompt)
            else:  # 非AI回复模式，使用自定义消息
                ai_reply_content = self.custom_message
                if self.debug_mode: print(f"      非AI回复模式，使用自定义消息: '{ai_reply_content}'")

            if not ai_reply_content or "AI回复获取失败" in ai_reply_content:
                print(f"      回复无效 ('{ai_reply_content}'). 不发送。")
            else:
                if self.debug_mode: print(f"      准备发送回复: '{ai_reply_content[:60]}...'")
                chat_input_selectors = [
                    "//div[@data-e2e='msg-input']//div[@contenteditable='true' and contains(@class, 'public-DraftEditor-content')]",
                    "//div[@data-e2e='msg-input']//div[contains(@class, 'DraftEditor-root')]//div[@contenteditable='true']",
                    "//div[@data-e2e='im-chat-input']//div[@contenteditable='true']",
                    "//div[@data-slate-editor='true']",
                    "//textarea[contains(@placeholder,'发送消息') or contains(@placeholder,'输入')]"
                ]
                chat_input_area_s = None
                for selector in chat_input_selectors:
                    temp_s = S(selector)
                    if temp_s.exists():
                        chat_input_area_s = temp_s
                        if self.debug_mode: print(f"        找到聊天输入框 (选择器: {selector})")
                        break
                if chat_input_area_s:
                    try:
                        click(chat_input_area_s);
                        time.sleep(0.3)
                        chat_input_area_s.web_element.send_keys(CONTROL + 'a');
                        time.sleep(0.1)
                        chat_input_area_s.web_element.send_keys(DELETE);
                        time.sleep(0.1)
                        write(ai_reply_content, into=chat_input_area_s);
                        time.sleep(0.5)
                        send_btn_selectors = [
                            "//div[@data-e2e='im-chat-input']//button[(@type='submit' or contains(@class,'send')) and not(@disabled)]",
                            "//div[contains(@class,'im-footer-bar')]//button[contains(.,'发送') and not(@disabled)]//span[text()='发送']",
                            "//button[@aria-label='发送' and not(@disabled)]"
                        ]
                        sent_by_button = False
                        for sel_btn in send_btn_selectors:
                            send_button_s = S(sel_btn)
                            if send_button_s.exists() and send_button_s.web_element.is_enabled():
                                try:
                                    click(send_button_s)
                                    if self.debug_mode: print(
                                        f"        通过按钮发送回复: '{ai_reply_content[:30]}...' (选择器: {sel_btn})")
                                    sent_by_button = True;
                                    break
                                except Exception as e_btn_send:
                                    if self.debug_mode: print(f"        按钮发送失败 (选择器: {sel_btn}): {e_btn_send}")
                        if not sent_by_button:
                            if self.debug_mode: print("        未通过按钮发送，尝试回车发送...")
                            press(ENTER)
                        print(f"    已发送回复: '{ai_reply_content[:60]}...'")
                        time.sleep(1.5)
                    except Exception as e_send_process:
                        print(f"      发送回复过程中出错: {e_send_process}")
                else:
                    print("      未找到聊天输入框。无法发送回复。")

            if self.debug_mode: print("    尝试退出当前聊天会话...")
            exit_chat_selectors = [
                "//span[normalize-space(text())='退出会话']",
                "//div[@data-e2e='im-chat-header-back-btn']",
                "//div[contains(@class,'chat-header')]//span[contains(@class,'back-icon') or contains(@class,'arrow-left')]",
                "//div[contains(@class,'dy-icon-arrow-left')]/parent::div[contains(@class,'chat-window-header-left')]"
            ]
            exited_chat_ui = False
            for sel_exit in exit_chat_selectors:
                exit_btn_s = S(sel_exit)
                if exit_btn_s.exists():
                    try:
                        click(exit_btn_s)
                        if self.debug_mode: print(f"      点击退出聊天按钮成功 (选择器: {sel_exit})。")
                        exited_chat_ui = True;
                        break
                    except Exception as e_exit_click:
                        if self.debug_mode: print(f"      点击退出聊天按钮 (选择器 {sel_exit}) 失败: {e_exit_click}")
            if not exited_chat_ui:
                if self.debug_mode: print("      未找到或未能成功点击UI退出聊天按钮，尝试强制导航回主页或个人页...")
                self._navigate_to_url("https://www.douyin.com/user/self")
                time.sleep(2.5)
                if self.debug_mode: print("      尝试重新打开消息列表...")
                message_button_entry_temp = S("//div[@data-e2e='im-entry']")
                if message_button_entry_temp.exists():
                    hover(message_button_entry_temp);
                    time.sleep(1.5)
                    chat_list_container_temp = S("//div[@data-e2e='im-list-container'] | //div[@class='iXcuFCYr']")
                    if not chat_list_container_temp.exists() or not chat_list_container_temp.web_element.is_displayed():
                        if self.debug_mode: print("        消息列表未通过悬停打开，尝试点击入口...")
                        try:
                            click(message_button_entry_temp);
                            time.sleep(1.5)
                        except Exception as e_click_entry:
                            if self.debug_mode: print(f"        点击消息入口时出错: {e_click_entry}")
                else:
                    if self.debug_mode: print("      强制导航后也未找到消息入口。")
            time.sleep(2)
        except StaleElementReferenceException:
            print(f"  处理单条私信时元素过时，跳过。")
        except Exception as e_single_msg:
            print(f"  处理单条私信时发生严重错误: {e_single_msg}")
            import traceback
            if self.debug_mode: traceback.print_exc()
        finally:
            try:
                main_im_panel = S("//div[@data-e2e='im-chat-panel' and descendant::div[@data-e2e='im-list-container']]")
                if main_im_panel.exists() and main_im_panel.web_element.is_displayed():
                    if self.debug_mode: print("    确保主私信面板关闭 (点击body)...")
                    S("/html/body").web_element.click();
                    time.sleep(0.5)
            except:
                pass