import requests
import json
import random

COZE_CLIENT_VERSION = "2.0.3-stream-focus"  # 新版本号


class CozeClient:
    def __init__(self, token, bot_id, debug_mode=False):
        self.base_url = "https://api.coze.cn/v3/chat"
        self.token = token
        self.bot_id = bot_id
        self.debug_mode = debug_mode
        self.client_version_log_tag = COZE_CLIENT_VERSION
        if self.debug_mode:
            print(f"CozeClient 已初始化 (客户端版本: {self.client_version_log_tag})")

    def get_response(self, user_message, system_prompt):
        if self.debug_mode:
            print(f"\nCozeClient.get_response 调用 (客户端版本 {self.client_version_log_tag})...")
            print(f"  用户消息: {user_message}")
            print(f"  系统提示词: {system_prompt[:70]}...")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Connection": "keep-alive",
        }

        payload = {
            "bot_id": self.bot_id,
            "user_id": f"douyin_user_{random.randint(1000, 9999)}",
            "stream": True,
            "auto_save_history": False,
            "additional_messages": []
        }

        if system_prompt:
            payload["additional_messages"].append({"role": "system", "content": system_prompt})
        payload["additional_messages"].append({"role": "user", "content": user_message})

        if self.debug_mode:
            print(f"\n===== Coze API 请求 (客户端版本 {self.client_version_log_tag}) =====")
            print(f"URL: {self.base_url}")
            print(f"Authorization: Bearer {self.token[:10]}...{self.token[-5:]}")
            print("Payload:", json.dumps(payload, indent=2, ensure_ascii=False))
            print("正在发送 API 请求...")

        final_answer_content = ""

        try:
            response_stream = requests.post(self.base_url, headers=headers, json=payload, stream=True, timeout=120)
            response_stream.raise_for_status()

            if self.debug_mode:
                print("\n===== Coze API 响应流 =====")
                print(f"状态码: {response_stream.status_code}")
                print("正在处理流以获取 AI 答案...")

            full_raw_response_for_pp_check = ""  # 用于启发式检查的完整原始字符串

            for line_bytes in response_stream.iter_lines():
                if not line_bytes: continue
                line = line_bytes.decode('utf-8').strip()

                if self.debug_mode and len(line) < 250: print(f"  Stream line: {line}")

                if line.startswith("data:"):
                    json_str = line[len("data:"):].strip()
                    if not json_str or json_str == "[DONE]":  # 跳过空的或结束标记
                        if json_str == "[DONE]" and self.debug_mode: print("  Stream [DONE] received.")
                        continue

                    try:
                        data_event = json.loads(json_str)
                        event_name = data_event.get("event")  # Coze stream uses an 'event' field
                        message_type = data_event.get("type")
                        content = data_event.get("content", "")
                        content_type = data_event.get("content_type")

                        if self.debug_mode:
                            preview = str(content)[:60] + "..." if isinstance(content, (str, dict, list)) else content
                            print(
                                f"    Parsed: event='{event_name}', type='{message_type}', content_type='{content_type}', content='{preview}'")

                        # 根据您的日志，最终的完整答案在 type="answer", content_type="text" 的 message.completed 事件中
                        # 或者在 type="answer", content_type="text" 的 message.delta 事件中累积
                        # Coze 的流式响应，最终的答案文本在 event:conversation.message.completed, type:answer
                        # 或者在 event:conversation.message.delta, type:answer 事件中，需要拼接

                        if event_name == "conversation.message.delta" and message_type == "answer" and content_type == "text":
                            if isinstance(content, str):
                                final_answer_content += content  # 累积delta的内容
                                if self.debug_mode: print(
                                    f"      -> Delta answer appended: current full = '{final_answer_content[:70]}...'")

                        # 另外，您的日志显示 `event:conversation.message.completed` 中也有 `type:answer`
                        # 这通常包含完整的消息。如果 delta 也在累积，我们需要决定哪个优先。
                        # Coze 文档："仅解析流式响应的智能体回复部分 ... 在事件 event:conversation.message.completed中，取 type=answer 的事件"
                        # 这表明 `completed` 事件中的 `type=answer` 是最终的。
                        elif event_name == "conversation.message.completed" and message_type == "answer" and content_type == "text":
                            if isinstance(content, str):
                                final_answer_content = content  # 这个应该是完整的最终答案
                                full_raw_response_for_pp_check = content  # 保存用于启发式检查
                                if self.debug_mode: print(
                                    f"      -> Completed answer set: '{final_answer_content[:70]}...'")

                        # 保留原始的 full_raw_response_for_pp_check 逻辑，以防万一 API 返回了您之前看到的那种重复格式
                        # 在您的日志中，这种 "AnswerAnswerFollowUp" 的模式是在 type=answer 的 content 里直接出现的
                        if message_type == "answer" and content_type == "text" and isinstance(content, str):
                            # 这个 content 可能就是您之前看到的 "禁止私加微信哦禁止私加微信哦有什么更好的交流方式吗？..."
                            # 我们将用这个进行启发式检查
                            if len(content) > len(full_raw_response_for_pp_check):  # 取最长的那个作为启发式检查的源
                                full_raw_response_for_pp_check = content


                    except json.JSONDecodeError:
                        if self.debug_mode: print(f"    JSON decode error for stream data: '{json_str}'")
                    except AttributeError as e_attr:  # 捕获 'str' object has no attribute 'get'
                        if self.debug_mode: print(
                            f"    AttributeError (likely on '[DONE]'): {e_attr} for data: '{json_str}'")
                    except Exception as e_parse:
                        if self.debug_mode: print(f"    Error processing parsed stream data: {e_parse}")

            if self.debug_mode: print("===== Stream processing finished. =====")

            # 如果 final_answer_content 通过 delta 或 completed 事件正确填充了，优先使用它
            # 否则，回退到对 full_raw_response_for_pp_check 进行启发式处理
            if final_answer_content:
                if self.debug_mode: print(
                    f"  Using final_answer_content from delta/completed: '{final_answer_content}'")
            elif full_raw_response_for_pp_check:
                if self.debug_mode:
                    print(
                        f"  final_answer_content is empty. Applying heuristic to full_raw_response_for_pp_check: '{full_raw_response_for_pp_check}'")

                processed_answer_from_pp = ""
                raw_len = len(full_raw_response_for_pp_check)
                for i in range(raw_len // 2, 0, -1):
                    prefix = full_raw_response_for_pp_check[:i]
                    if full_raw_response_for_pp_check.startswith(prefix + prefix):
                        processed_answer_from_pp = prefix
                        if self.debug_mode: print(f"    Heuristic PP match: found prefix '{prefix}' (len {i})")
                        break

                if processed_answer_from_pp:
                    final_answer_content = processed_answer_from_pp
                else:  # 如果启发式也失败，就用原始的（可能包含后续问题的）
                    final_answer_content = full_raw_response_for_pp_check
                    if self.debug_mode: print(f"    Heuristic PP no match. Using raw: '{final_answer_content}'")
            else:
                if self.debug_mode: print("  Warning: No answer content extracted from stream.")

            if self.debug_mode: print(f"Final processed AI answer: '{final_answer_content}'")
            return final_answer_content

        except requests.exceptions.HTTPError as e_http:
            if self.debug_mode: print(
                f"Coze API HTTP Error: {e_http.response.status_code}. Details: {e_http.response.text}")
            return f"AI回复获取失败 (HTTP {e_http.response.status_code})"
        except requests.exceptions.RequestException as e_req:
            if self.debug_mode: print(f"Coze API Request Failed: {e_req}")
            return f"AI回复获取失败 (网络问题: {type(e_req).__name__})"
        except Exception as e_generic:
            if self.debug_mode: print(f"An unexpected error in CozeClient: {e_generic}")
            return "AI回复获取失败 (未知客户端错误)"