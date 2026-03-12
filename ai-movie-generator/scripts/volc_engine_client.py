import os
import time
import uuid
import base64
import requests
import functools
import inspect
import json
from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark
from core.logger import logger

# 加载 .env 文件中的环境变量
load_dotenv()

def llm_retry(max_retries=1):
    """
    错误重试装饰器，利用 LLM 优化参数（比如Prompt）并重试。
    主要用于图片生成和视频生成的模型重试。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"方法 {func.__name__} 执行失败: {e}。正在尝试 LLM 优化重试...")
                
                # 获取函数签名和绑定的参数
                sig = inspect.signature(func)
                bound_args = sig.bind(self, *args, **kwargs)
                bound_args.apply_defaults()
                original_params = {k: v for k, v in bound_args.arguments.items() if k != 'self'}
                
                # 构造 LLM 提示词
                prompt = f"""
                方法 {func.__name__} 调用失败。
                报错信息: {str(e)}
                原始输入参数: {json.dumps(original_params, ensure_ascii=False, indent=2)}
                
                请分析报错原因（例如是否包含敏感词、参数配置不合理等），并提供优化后的参数以规避错误。
                你需要返回一个 JSON 对象，其中包含需要更新的参数键值对。
                
                注意：
                1. 保持其他参数不变，仅修改必要的参数（如 prompt）。
                2. 严格返回 JSON 格式，不要有任何解释文字。
                """
                
                try:
                    # 调用 LLM 获取优化建议
                    llm_response = self.chat(prompt)
                    
                    # 清洗 JSON
                    if "```json" in llm_response:
                        llm_response = llm_response.split("```json")[1].split("```")[0].strip()
                    elif "```" in llm_response:
                        llm_response = llm_response.split("```")[1].split("```")[0].strip()
                    
                    optimized_params = json.loads(llm_response)
                    logger.info(f"LLM 优化建议参数: {optimized_params}")
                    
                    # 更新参数并重试
                    new_kwargs = {**kwargs, **optimized_params}
                    
                    # 避免在重试时再次触发装饰器导致死循环（虽然 max_retries=1，但这样更安全）
                    # 这里简单处理，只重试一次
                    logger.info(f"正在使用优化后的参数重新调用 {func.__name__}...")
                    return func(self, *args, **new_kwargs)
                    
                except Exception as retry_e:
                    logger.error(f"LLM 优化重试失败: {retry_e}")
                    # 如果重试也失败，抛出原始异常
                    raise e
        return wrapper
    return decorator

class VolcEngineAI:
    """
    火山引擎模型服务封装类，集成文生文、语音合成、图生图、图生视频四大功能。
    """

    def __init__(self, api_key=None, tts_appid=None, tts_token=None, tts_cluster=None):
        """
        初始化客户端。
        :param api_key: 方舟平台 API KEY (ARK_API_KEY)
        :param tts_appid: 语音合成 AppID
        :param tts_token: 语音合成 Access Token
        :param tts_cluster: 语音合成 Cluster ID
        """
        logger.info("正在初始化 VolcEngineAI 客户端...")
        self.api_key = api_key or os.getenv("ARK_API_KEY")
        self.client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=self.api_key
        )
        
        # 语音合成配置
        self.tts_config = {
            "appid": tts_appid or os.getenv("VOLC_TTS_APPID"),
            "token": tts_token or os.getenv("VOLC_TTS_TOKEN"),
            "cluster": tts_cluster or os.getenv("VOLC_TTS_CLUSTER", "volcano_tts")
        }
        logger.info("VolcEngineAI 客户端初始化完成。")

    def chat(self, prompt, image_urls=None, model="doubao-seed-1-8-251228"):
        """
        文生文（大语言模型LLM） / 多模态对话接口。
        :param prompt: 文本提示词
        :param image_urls: 图片链接列表 (可选，用于多模态)
        :param model: 模型 ID
        :return: 模型响应结果
        """
        debug_params = {k: v for k, v in locals().items() if k != 'self'}
        logger.debug(f"🤖 [chat] 输入 - model: {model}")
        logger.debug(f"🤖 [chat] 输入 - prompt: {prompt}")
        if image_urls:
            logger.debug(f"🤖 [chat] 输入 - image_urls: {image_urls}")
        
        content = []
        if image_urls:
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            for url in image_urls:
                content.append({"type": "input_image", "image_url": url})
        
        content.append({"type": "input_text", "text": prompt})

        try:
            response = self.client.responses.create(
                model=model,
                input=[{"role": "user", "content": content}]
            )
            
            for item in response.output:
                if item.type == "message":
                    for content_item in item.content:
                        if content_item.type == "output_text":
                            result = content_item.text
                            logger.debug(f"🤖 [chat] 输出 - response: {result}")
                            return result
            logger.warning(f"🤖 [chat] 返回非标准响应内容: {response}")
            return str(response)
        except Exception as e:
            logger.error(f"🤖 [chat] 失败 - error: {str(e)}, input_prompt: {prompt}")
            raise e

    def chat_messages(self, messages, model="doubao-seed-1-8-251228"):
        """
        支持完整消息历史的对话接口。
        :param messages: 消息列表，格式为 [{"role": "user", "content": ...}, ...]
        :param model: 模型 ID
        :return: 模型响应文本
        """
        logger.info(f"调用 chat_messages 方法, model: {model}, 消息数: {len(messages)}")
        try:
            # 转换 content 格式以适配 Ark runtime
            ark_input = []
            for msg in messages:
                role = msg['role']
                content = msg['content']
                
                # Filter out empty content to avoid Ark SDK MissingParameter error
                if not content:
                    logger.warning(f"Skipping message with empty content: {msg}")
                    continue
                
                if isinstance(content, list):
                    # 转换 OpenAI 格式的多模态 content 为 VolcEngine 格式
                    new_content = []
                    for item in content:
                        if isinstance(item, dict):
                            item_type = item.get('type')
                            if item_type == 'text':
                                # 尝试优先使用 input_text (VolcEngine 格式)
                                new_content.append({
                                    "type": "input_text", 
                                    "text": item.get('text')
                                })
                            elif item_type == 'image_url':
                                img_url_obj = item.get('image_url')
                                url = img_url_obj.get('url') if isinstance(img_url_obj, dict) else img_url_obj
                                
                                # Validate URL scheme
                                if url and not (url.startswith('http://') or url.startswith('https://') or url.startswith('data:')):
                                    # Fallback for invalid URLs or relative paths if needed, or skip
                                    # For now, just logging warning and skipping invalid image to avoid API error
                                    logger.warning(f"Skipping invalid image URL: {url}")
                                    continue
                                    
                                # VolcEngine 使用 input_image 且 image_url 为字符串
                                new_content.append({
                                    "type": "input_image", 
                                    "image_url": url
                                })
                            else:
                                new_content.append(item)
                        else:
                            new_content.append(item)
                    content = new_content
                
                ark_input.append({"role": role, "content": content})

            logger.info(f"Ark Input: {json.dumps(ark_input, ensure_ascii=False)}")

            response = self.client.responses.create(
                model=model,
                input=ark_input
            )
            
            for item in response.output:
                if item.type == "message":
                    if hasattr(item, 'content'):
                        text_parts = []
                        for content_item in item.content:
                            if content_item.type == "output_text" or content_item.type == "text":
                                text_parts.append(content_item.text)
                        if text_parts:
                            return "".join(text_parts)
            
            return str(response)
        except Exception as e:
            # 如果 input_text 也不行，或者有其他错误，记录日志并抛出
            # 也可以在这里尝试回退到 'text' 类型，如果 SDK 更新支持了的话
            logger.error(f"chat_messages 调用失败: {str(e)}")
            raise e


    def text_to_speech(self, text, voice_type="zh_female_vv_uranus_bigtts", speed=1.0, output_path="output.mp3", context_texts=None, emotion=None):
        """
        语音合成接口 (TTS) - V3 版本。
        :param text: 待合成文本
        :param voice_type: 音色类型
        :param speed: 语速 (0.2-3.0)，映射到 V3 的 [-50, 100]
        :param output_path: 音频保存路径
        :param context_texts: 上下文文本列表，用于提升合成效果
        :param emotion: 情感类型 (如果支持)
        :return: 保存的路径 or 错误信息
        """
        # 记录详细的调试日志
        debug_params = {k: v for k, v in locals().items() if k != 'self'}
        logger.debug(f"text_to_speech 方法详细输入参数: {json.dumps(debug_params, ensure_ascii=False)}")
        
        logger.info(f"调用 text_to_speech (V3) 方法, voice_type: {voice_type}, text: {text[:50]}...")
        if not all(self.tts_config.values()):
            logger.error("TTS 配置缺失")
            raise ValueError("TTS 配置缺失，请检查环境变量或初始化参数。")

        url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
        headers = {
            "Content-Type": "application/json",
            "X-Api-App-Id": self.tts_config['appid'],
            "X-Api-Access-Key": self.tts_config['token'],
            "X-Api-Resource-Id": "seed-tts-2.0"
        }

        # 构造 additions 字段 (JSON 字符串)
        additions_dict = {}
        if context_texts and len(context_texts) > 0:
            additions_dict["context_texts"] = context_texts
        
        # 语速映射: 0.2-3.0 -> -50~100
        # 1.0 -> 0, 2.0 -> 100, 0.5 -> -50
        speech_rate = int((speed - 1.0) * 100)
        speech_rate = max(-50, min(100, speech_rate))  # 限制范围

        audio_params = {
            "format": "mp3",
            "sample_rate": 24000,
            "speech_rate": speech_rate,
            "volume_rate": 0,
            "pitch_rate": 0
        }

        if emotion:
            audio_params["emotion"] = emotion

        req_params = {
            "text": text,
            "speaker": voice_type,
            "audio_params": audio_params
        }

        if additions_dict:
            req_params["additions"] = json.dumps(additions_dict, ensure_ascii=False)

        body = {
            "user": {"uid": "volc_ai_user"},
            "req_params": req_params
        }
        
        logger.info(f"TTS V3 Request Body: {json.dumps(body, ensure_ascii=False)}")

        try:
            # 使用 stream=True 处理流式响应
            resp = requests.post(url, json=body, headers=headers, stream=True)
            if resp.status_code == 200:
                audio_content = bytearray()
                for line in resp.iter_lines():
                    if line:
                        try:
                            json_data = json.loads(line.decode('utf-8'))
                            # 检查 code
                            if json_data.get("code") == 3000 or json_data.get("code") == 0:
                                data_str = json_data.get("data")
                                if data_str:
                                    audio_content.extend(base64.b64decode(data_str))
                            elif json_data.get("code") == 3031: # 3031 可能是中间状态或其他非错误码，需根据实际情况调整
                                logger.warning(f"TTS V3 返回状态码 3031: {json_data}")
                            else:
                                # 如果是结束包且没有错误，可能 code 是其他值，或者就是 0 但没有 data
                                if "data" not in json_data and "usage" in json_data:
                                    logger.info(f"TTS 合成结束: {json_data}")
                                    continue
                                logger.error(f"TTS 业务错误: {json_data}")
                                # 如果已经有音频数据，可能只是最后的 metadata 包报错或非音频包，暂时不抛出异常，除非没有数据
                                if not audio_content:
                                     raise Exception(f"TTS Error: {json_data.get('message')} (Code: {json_data.get('code')})")
                        except json.JSONDecodeError:
                             logger.warning(f"无法解析 JSON 行: {line}")
                             continue

                if audio_content:
                    with open(output_path, "wb") as f:
                        f.write(audio_content)
                    logger.info(f"TTS 成功，音频已保存至: {output_path}")
                    return output_path
                else:
                    raise Exception("TTS 响应中未找到有效的音频数据")
            else:
                logger.error(f"TTS HTTP 错误: {resp.status_code}, Response: {resp.text}")
                raise Exception(f"HTTP Error: {resp.status_code}")
        except Exception as e:
            params = {
                "text": text, "voice_type": voice_type, "speed": speed, "output_path": output_path
            }
            logger.error(f"text_to_speech 调用异常: {str(e)}, 输入参数: {json.dumps(params, ensure_ascii=False)}")
            raise

    @llm_retry()
    def text_to_image(self, prompt, model="doubao-seedream-4-5-251128", size="4K"):
        """
        文生图接口。
        :param prompt: 提示词
        :param model: 模型 ID
        :param size: 图片尺寸
        :return: 生成的图片链接
        """
        logger.debug(f"🎨 [text_to_image] 输入 - model: {model}, size: {size}")
        logger.debug(f"🎨 [text_to_image] 输入 - prompt: {prompt}")

        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                response_format="url",
                size=size,
                watermark=False
            )
            url = response.data[0].url
            logger.debug(f"🎨 [text_to_image] 输出 - url: {url}")
            return url
        except Exception as e:
            logger.error(f"🎨 [text_to_image] 失败 - error: {str(e)}, input_prompt: {prompt}")
            raise

    @llm_retry()
    def image_to_image(self, prompt, image_urls, model="doubao-seedream-4-5-251128", size="2K"):
        """
        图生图接口。
        :param prompt: 提示词
        :param image_urls: 参考图链接列表
        :param model: 模型 ID
        :param size: 图片尺寸
        :return: 生成的图片链接
        """
        logger.debug(f"🖼️ [image_to_image] 输入 - model: {model}, size: {size}")
        logger.debug(f"🖼️ [image_to_image] 输入 - prompt: {prompt}")
        logger.debug(f"🖼️ [image_to_image] 输入 - image_urls: {image_urls}")
        
        if isinstance(image_urls, str):
            image_urls = [image_urls]

        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                image=image_urls,
                response_format="url",
                size=size,
                watermark=False
            )
            url = response.data[0].url
            logger.debug(f"🖼️ [image_to_image] 输出 - url: {url}")
            return url
        except Exception as e:
            logger.error(f"🖼️ [image_to_image] 失败 - error: {str(e)}, input_prompt: {prompt}")
            raise

    def async_image_to_video(self, prompt, first_frame=None, last_frame=None, 
                             model="doubao-seedance-1-5-pro-251215", 
                             resolution="720p", ratio="adaptive", duration=10, 
                             callback_url=None, execution_expires_after=3600):
        """
        异步图生视频接口。
        :param prompt: 视频描述提示词，描述视频中的动作和场景。 (必须)
        :param first_frame: 视频的首帧图片链接，作为视频生成的起点。 (可选，但如果有 last_frame 则必须)
        :param last_frame: 视频的尾帧图片链接，作为视频生成的终点。 (可选)
        :param model: 使用的模型 ID。
        :param resolution: 视频分辨率 (如 480p, 720p, 1080p)。
        :param ratio: 视频宽高比 (如 16:9, 9:16, 1:1)。
        :param duration: 视频时长 (秒)，通常为 4-12 秒。
        :param callback_url: 任务完成后的回调通知地址。
        :param execution_expires_after: 任务过期时间 (秒)。
        :return: 创建的任务 ID。
        """
        # 记录详细的调试日志
        debug_params = {k: v for k, v in locals().items() if k != 'self'}
        logger.debug(f"async_image_to_video 方法详细输入参数: {json.dumps(debug_params, ensure_ascii=False)}")
        
        # 参数校验
        if last_frame and not first_frame:
            raise ValueError("If 'last_frame' is provided, 'first_frame' must also be provided.")
        
        logger.info(f"调用 async_image_to_video 方法, model: {model}, resolution: {resolution}, ratio: {ratio}, duration: {duration}")
        content = [{"type": "text", "text": prompt}]
        
        if first_frame:
            content.append({"type": "image_url", "image_url": {"url": first_frame}, "role": "first_frame"})
        
        if last_frame:
            content.append({"type": "image_url", "image_url": {"url": last_frame}, "role": "last_frame"})

        try:
            # 准备请求参数
            params = {
                "model": model,
                "content": content,
                "generate_audio": True,
                "resolution": resolution,
                "ratio": ratio,
                "duration": duration,
                "execution_expires_after": execution_expires_after
            }
            if callback_url:
                params["callback_url"] = callback_url

            task = self.client.content_generation.tasks.create(**params)
            task_id = task.id
            logger.info(f"视频生成任务已创建 (异步), task_id: {task_id}")
            return task_id
        except Exception as e:
            input_params = {
                "prompt": prompt, "first_frame": first_frame, "last_frame": last_frame,
                "model": model, "resolution": resolution, "ratio": ratio, "duration": duration
            }
            logger.error(f"视频生成任务创建失败: {str(e)}, 输入参数: {json.dumps(input_params, ensure_ascii=False)}")
            raise

    @llm_retry()
    def image_to_video(self, prompt, first_frame=None, last_frame=None,
                       model="doubao-seedance-1-5-pro-251215",
                       resolution="720p", ratio="adaptive", duration=10,
                       callback_url=None, execution_expires_after=3600,
                       task_id_to_track=None):
        """
        同步图生视频接口（通过异步接口 + 轮询状态模拟监听回调）。
        :param prompt: 视频描述提示词。 (必须)
        :param first_frame: 视频首帧图片链接。 (可选，但如果有 last_frame 则必须)
        :param last_frame: 视频尾帧图片链接。 (可选)
        :param model: 模型 ID。
        :param resolution: 分辨率。
        :param ratio: 宽高比。
        :param duration: 视频时长。
        :param callback_url: 回调通知地址。
        :param execution_expires_after: 任务过期时间。
        :param task_id_to_track: 后端任务系统的任务ID，用于更新进度。
        :return: 生成的视频链接。
        """
        logger.debug(f"🎬 [image_to_video] 输入 - model: {model}, resolution: {resolution}, ratio: {ratio}, duration: {duration}")
        logger.debug(f"🎬 [image_to_video] 输入 - prompt: {prompt}")
        if first_frame:
            logger.debug(f"🎬 [image_to_video] 输入 - first_frame: {first_frame}")
        if last_frame:
            logger.debug(f"🎬 [image_to_video] 输入 - last_frame: {last_frame}")
        
        logger.info("开始同步生成视频...")
        volc_task_id = self.async_image_to_video(
            prompt=prompt,
            first_frame=first_frame,
            last_frame=last_frame,
            model=model,
            resolution=resolution,
            ratio=ratio,
            duration=duration,
            callback_url=callback_url,
            execution_expires_after=execution_expires_after
        )

        logger.info(f"开始轮询监听任务状态 (Volc Task ID: {volc_task_id})...")
        start_time = time.time()
        input_params = {
            "prompt": prompt, "first_frame": first_frame, "last_frame": last_frame,
            "model": model, "resolution": resolution, "ratio": ratio, "duration": duration
        }
        
        while True:
            if time.time() - start_time > execution_expires_after:
                logger.error(f"🎬 [image_to_video] 失败 - 超时, input: {input_params}")
                raise Exception(f"Task {volc_task_id} timed out during local polling.")

            if task_id_to_track:
                current_task = task_manager.get_task(task_id_to_track)
                if current_task and current_task['status'] == 'aborted':
                    logger.info(f"后端任务 {task_id_to_track} 已被中止，停止轮询火山任务 {volc_task_id}")
                    raise Exception("Task aborted by user")

            result = self.client.content_generation.tasks.get(task_id=volc_task_id)
            status = result.status
            
            if status == "succeeded":
                logger.info(f"任务 {volc_task_id} 成功。")
                    
                video_url = None
                
                if hasattr(result, "content") and result.content:
                    if hasattr(result.content, "video_url"):
                        video_url = result.content.video_url
                    elif isinstance(result.content, dict) and "video_url" in result.content:
                        video_url = result.content["video_url"]
                
                if not video_url and hasattr(result, "video_url"):
                    video_url = result.video_url
                    
                if not video_url:
                    try:
                        data_dict = result.model_dump()
                        if "content" in data_dict and "video_url" in data_dict["content"]:
                            video_url = data_dict["content"]["video_url"]
                        elif "video_url" in data_dict:
                            video_url = data_dict["video_url"]
                    except:
                        pass
                
                if video_url:
                    logger.debug(f"🎬 [image_to_video] 输出 - video_url: {video_url}")
                    return video_url
                else:
                    logger.warning(f"🎬 [image_to_video] 成功但未找到 video_url: {result}")
                    return str(result)
                    
            elif status == "failed":
                logger.error(f"🎬 [image_to_video] 失败 - error: {result.error}, input: {input_params}")
                raise Exception(f"Video Task {volc_task_id} Failed: {result.error}")
            elif status == "expired":
                logger.error(f"🎬 [image_to_video] 失败 - 过期, input: {input_params}")
                raise Exception(f"Video Task {volc_task_id} Expired.")
            else:
                time.sleep(5)
