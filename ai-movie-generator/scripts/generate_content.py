#!/usr/bin/env python3
import sys
import os
import json
import argparse
import requests
import subprocess
import re
import shutil
from datetime import datetime
from PIL import Image
import logging

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

from config import OUTPUT_DIR, DATA_DIR, tos_client, TOS_BUCKET, TOS_REGION
from database import init_db, add_character, get_character, add_storyboard
from volc_engine_client import VolcEngineAI
from prompts import (
    DIRECTOR_SYSTEM_PROMPT, 
    CHARACTER_DESIGNER_SYSTEM_PROMPT, 
    STORYBOARD_DESIGNER_SYSTEM_PROMPT, 
    EDITOR_SYSTEM_PROMPT,
    QA_INSPECTOR_SYSTEM_PROMPT
)
from core.task_manager import create_movie_workflow, LLMTaskManager
from core.logger import logger

print("🎬 ===== AI 电影生成器 - 真实 API 模式 (VolcEngineAI) ===== \n")

def clean_json_response(text):
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return text

def sanitize_filename(name):
    return re.sub(r'[<>:\"/\\|?*]', '_', name)

def generate_project_md(movie_dir, script_content, plan, character_data, storyboard_records):
    md_path = os.path.join(movie_dir, "project.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {plan.get('movie_title', 'AI Movie')}\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("---\n\n")
        f.write("## 📜 原始剧本\n\n")
        f.write(f"```\n{script_content}\n```\n\n")
        
        f.write("---\n\n")
        f.write("## 🎭 角色设计\n\n")
        for char_name, char_info in character_data.items():
            f.write(f"### {char_name}\n\n")
            f.write(f"- **主图提示词**: {char_info.get('main_prompt', '')}\n")
            f.write(f"- **正面视图**: {char_info.get('front_view_prompt', '')}\n")
            f.write(f"- **侧面视图**: {char_info.get('side_view_prompt', '')}\n")
            f.write(f"- **背面视图**: {char_info.get('back_view_prompt', '')}\n")
            f.write(f"- **完整概念图提示词**: {char_info.get('all_in_one_concept_prompt', '')}\n\n")
        
        f.write("---\n\n")
        f.write("## 🎞️ 分镜设计\n\n")
        for idx, record in enumerate(storyboard_records, 1):
            f.write(f"### 分镜 {idx}\n\n")
            f.write(f"- **场景描述**: {record.get('description', '')}\n")
            f.write(f"- **角色**: {record.get('characters', '')}\n")
            f.write(f"- **对话**: {record.get('dialogue', '')}\n")
            f.write(f"- **BGM/音效**: {record.get('bgm_sfx', '')}\n")
            f.write(f"- **图片提示词**: {record.get('image_prompt', '')}\n")
            f.write(f"- **视频提示词**: {record.get('video_prompt', '')}\n")
            f.write(f"- **时长**: {record.get('duration', 0)} 秒\n\n")
        
        f.write("---\n\n")
        f.write("## 📋 大导演规划\n\n")
        f.write("```json\n")
        f.write(json.dumps(plan, ensure_ascii=False, indent=2))
        f.write("\n```\n")
    
    print(f"✅ 生成项目记录: {md_path}")
    return md_path

def qa_inspector_agent(volc_ai, first_frame_url, ref_image_urls, image_prompt, character_descriptions=None, shot_description="", max_retries=1):
    print("  🔍 ===== Agent QA: 优化提示词...")
    
    qa_prompt = f"""
{QA_INSPECTOR_SYSTEM_PROMPT}

图生图提示词: {image_prompt}
分镜描述: {shot_description}
参考角色描述: {json.dumps(character_descriptions or [], ensure_ascii=False)}
"""
    
    qa_response = volc_ai.chat(qa_prompt, model="doubao-seed-2-0-pro-260215")
    qa_response = clean_json_response(qa_response)
    
    try:
        qa_result = json.loads(qa_response)
    except Exception as e:
        print(f"  ⚠️ 质检 JSON 解析失败，使用原始提示词: {e}")
        return {"passed": True, "first_frame_url": first_frame_url, "issues": []}
    
    passed = qa_result.get("passed", True)
    issues = qa_result.get("issues", [])
    optimized_prompt = qa_result.get("optimized_prompt", "")
    
    if passed or not optimized_prompt:
        print(f"  ✅ 提示词无需优化或未提供优化建议")
        return {"passed": True, "first_frame_url": first_frame_url, "issues": []}
    else:
        print(f"  ❌ 提示词需要优化，问题: {issues}")
        print(f"  🔄 使用优化后的提示词重新生成...")
        try:
            if ref_image_urls:
                first_frame_url = volc_ai.image_to_image(
                    prompt=optimized_prompt, 
                    image_urls=ref_image_urls
                )
            else:
                first_frame_url = volc_ai.text_to_image(optimized_prompt)
            print(f"  ✅ 使用优化后的提示词重新生成成功")
            return {"passed": True, "first_frame_url": first_frame_url, "issues": issues}
        except Exception as e:
            print(f"  ⚠️ 重新生成失败，使用原始图片: {e}")
            return {"passed": False, "first_frame_url": first_frame_url, "issues": issues}

def download_file(url, save_path):
    """下载 URL 内容到本地文件"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return save_path
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return None

def upload_to_tos(file_path, object_key=None):
    """
    上传文件到火山引擎对象存储 (TOS)
    :param file_path: 本地文件路径
    :param object_key: TOS 对象键，可选，默认使用文件名
    :return: 公网访问 URL
    """
    if not object_key:
        object_key = os.path.basename(file_path)
    
    logger.debug(f"upload_to_tos: 上传文件 {file_path} 到 TOS，对象键: {object_key}")
    
    try:
        tos_client.upload_file(file_path, TOS_BUCKET, object_key)
        
        url = f"https://{TOS_BUCKET}.{TOS_REGION}.tos-s3-cn-guangzhou.volces.com/{object_key}"
        
        logger.info(f"upload_to_tos: 上传成功，URL: {url}")
        return url
    except Exception as e:
        logger.error(f"upload_to_tos: 上传失败 - {e}")
        raise

def check_and_resize_image(image_path, max_width=6000, max_height=6000, quality=95):
    """
    检查并压缩图片尺寸
    :param image_path: 图片文件路径
    :param max_width: 最大宽度 (px)
    :param max_height: 最大高度 (px)
    :param quality: 压缩质量 (0-100)
    :return: 处理后的图片路径
    """
    try:
        img = Image.open(image_path)
        orig_width, orig_height = img.size
        
        if orig_width <= max_width and orig_height <= max_height:
            print(f"ℹ️  图片尺寸 {orig_width}x{orig_height} 在限制范围内，无需压缩")
            return image_path
        
        ratio = min(max_width / orig_width, max_height / orig_height)
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        print(f"📐 压缩图片: {orig_width}x{orig_height} -> {new_width}x{new_height}")
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        base, ext = os.path.splitext(image_path)
        resized_path = f"{base}_resized{ext}"
        resized_img.save(resized_path, quality=quality, optimize=True)
        
        print(f"✅ 图片已压缩并保存到: {resized_path}")
        return resized_path
        
    except Exception as e:
        print(f"❌ 图片处理失败: {e}")
        return image_path

def compress_image(input_path, output_path, max_width=2048, max_height=2048, quality=95):
    """
    将图片压缩到指定尺寸并保存到指定路径
    :param input_path: 输入图片路径
    :param output_path: 输出图片路径
    :param max_width: 最大宽度 (px)
    :param max_height: 最大高度 (px)
    :param quality: 压缩质量 (0-100)
    """
    try:
        img = Image.open(input_path)
        orig_width, orig_height = img.size
        
        ratio = min(max_width / orig_width, max_height / orig_height)
        new_width = int(orig_width * ratio)
        new_height = int(orig_height * ratio)
        
        logger.debug(f"compress_image: 压缩图片 {orig_width}x{orig_height} -> {new_width}x{new_height}")
        
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        resized_img.save(output_path, quality=quality, optimize=True)
        
        logger.debug(f"compress_image: 压缩完成，保存到 {output_path}")
        
    except Exception as e:
        logger.error(f"compress_image: 压缩失败 - {e}")
        raise

def merge_videos(video_paths, output_path, temp_dir=None):
    """使用 FFmpeg 拼接多个视频"""
    if not temp_dir:
        temp_dir = OUTPUT_DIR
    if not video_paths:
        print("⚠️  没有视频文件可拼接")
        logger.warning("merge_videos: 没有视频文件可拼接")
        return None
    
    logger.debug(f"merge_videos: 输入视频路径列表: {video_paths}")
    
    valid_paths = []
    for path in video_paths:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            valid_paths.append(path)
            logger.debug(f"merge_videos: 有效视频文件: {path} (大小: {os.path.getsize(path)} bytes)")
        else:
            print(f"⚠️  跳过无效视频文件: {path}")
            logger.warning(f"merge_videos: 跳过无效视频文件: {path} (存在: {os.path.exists(path)}, 大小: {os.path.getsize(path) if os.path.exists(path) else 'N/A'})")
    
    if not valid_paths:
        print("⚠️  没有有效的视频文件可拼接")
        logger.warning("merge_videos: 没有有效的视频文件可拼接")
        return None
    
    if len(valid_paths) == 1:
        print("ℹ️  只有一个视频，无需拼接")
        logger.debug("merge_videos: 只有一个视频，无需拼接")
        return valid_paths[0]
    
    list_file = os.path.join(temp_dir, "video_list.txt")
    logger.debug(f"merge_videos: 创建视频列表文件: {list_file}")
    
    try:
        with open(list_file, 'w', encoding='utf-8') as f:
            for vid_path in valid_paths:
                abs_path = os.path.abspath(vid_path)
                f.write(f"file '{abs_path}'\n")
                logger.debug(f"merge_videos: 添加到列表: {abs_path}")
        
        print(f"🎬 正在拼接 {len(valid_paths)} 个视频...")
        logger.info(f"merge_videos: 开始拼接 {len(valid_paths)} 个视频")
        print(f"📋 视频列表:")
        for i, path in enumerate(valid_paths, 1):
            print(f"  {i}. {path}")
        
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            "-y",
            output_path
        ]
        logger.debug(f"merge_videos: 执行 FFmpeg 命令 (copy): {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        logger.debug(f"merge_videos: FFmpeg 返回码: {result.returncode}")
        
        if result.returncode != 0:
            print(f"❌ FFmpeg 执行失败:")
            print(f"   标准错误: {result.stderr}")
            print(f"   标准输出: {result.stdout}")
            logger.error(f"merge_videos: FFmpeg copy 失败 - stderr: {result.stderr}, stdout: {result.stdout}")
            print(f"⚠️  尝试使用重新编码方式拼接...")
            logger.info("merge_videos: 尝试重新编码方式拼接")
            
            cmd_reencode = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",
                output_path
            ]
            logger.debug(f"merge_videos: 执行 FFmpeg 命令 (reencode): {' '.join(cmd_reencode)}")
            
            result_reencode = subprocess.run(cmd_reencode, capture_output=True, text=True)
            logger.debug(f"merge_videos: FFmpeg reencode 返回码: {result_reencode.returncode}")
            
            if result_reencode.returncode == 0 and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"✅ 使用重新编码方式拼接完成: {output_path} ({file_size:.2f} MB)")
                logger.info(f"merge_videos: 重新编码拼接成功 - {output_path} ({file_size:.2f} MB)")
                return output_path
            else:
                print(f"❌ 重新编码拼接也失败: {result_reencode.stderr}")
                logger.error(f"merge_videos: FFmpeg reencode 失败 - stderr: {result_reencode.stderr}, stdout: {result_reencode.stdout}")
                return None
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ 视频拼接完成: {output_path} ({file_size:.2f} MB)")
            logger.info(f"merge_videos: 拼接成功 - {output_path} ({file_size:.2f} MB)")
            return output_path
        else:
            print(f"⚠️  FFmpeg 执行成功但输出文件不存在")
            logger.warning("merge_videos: FFmpeg 执行成功但输出文件不存在")
            return None
            
    except FileNotFoundError:
        print(f"❌ FFmpeg 未安装，请先安装 FFmpeg")
        logger.error("merge_videos: FFmpeg 未安装")
        return None
    except Exception as e:
        print(f"❌ 视频拼接失败: {e}")
        logger.error(f"merge_videos: 异常 - {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if os.path.exists(list_file):
            try:
                os.remove(list_file)
                logger.debug(f"merge_videos: 删除临时文件: {list_file}")
            except Exception as e:
                logger.warning(f"merge_videos: 删除临时文件失败 - {e}")

def main():
    parser = argparse.ArgumentParser(description="AI 电影生成器")
    parser.add_argument("--script", type=str, help="剧本文件路径或直接输入剧本内容")
    args = parser.parse_args()

    if not args.script:
        print("❌ 请提供剧本内容或剧本文件路径。")
        return

    manager = create_movie_workflow()
    manager.start_workflow()

    plan = None
    character_data = {}
    storyboard_data = []
    storyboard_records = []
    video_paths = []
    volc_ai = None
    movie_dir = None

    try:
        def _init_db():
            init_db()
            return True
        manager.execute_task("init_db", _init_db, input_data={"db_path": os.path.join(DATA_DIR, "movie_gen.db")}, result_summary="数据库初始化完成")

        def _init_ai():
            nonlocal volc_ai
            volc_ai = VolcEngineAI()
            return volc_ai
        manager.execute_task("init_ai", _init_ai, result_summary="AI 客户端初始化完成")

        script_content = None
        def _read_script():
            nonlocal script_content
            script_content = args.script
            source = "直接输入"
            if os.path.exists(args.script):
                source = f"文件: {args.script}"
                with open(args.script, "r", encoding="utf-8") as f:
                    script_content = f.read()
            logger.debug(f"📖 剧本来源: {source}, 长度: {len(script_content)} 字符")
            return script_content
        script_content = manager.execute_task(
            "read_script", 
            _read_script, 
            input_data={"script_input": args.script, "is_file": os.path.exists(args.script)},
            result_summary=lambda res: f"剧本读取完成，长度: {len(res)} 字符" if res else "剧本读取失败"
        )
        print(f"✅ 读取剧本内容: {script_content[:60]}...")

        def _director_plan():
            nonlocal plan
            director_prompt = f"{DIRECTOR_SYSTEM_PROMPT}\n\n请分析以下剧本：\n{script_content}"
            logger.debug(f"🎬 导演提示词长度: {len(director_prompt)}")
            plan_response = volc_ai.chat(director_prompt, model="doubao-seed-2-0-pro-260215")
            plan_response = clean_json_response(plan_response)
            plan = json.loads(plan_response)
            logger.debug(f"🎬 导演计划: {json.dumps(plan, ensure_ascii=False)[:500]}...")
            return plan
        plan = manager.execute_task(
            "director_plan", 
            _director_plan,
            input_data={"script_preview": script_content[:200]},
            result_summary=lambda res: f"电影标题: {res.get('movie_title', 'N/A')}, 场景数: {len(res.get('scenes', []))}, 角色数: {len(res.get('characters_to_design', []))}"
        )
        print("✅ 剧本分析完成！\n")

        movie_title = plan.get("movie_title", "ai_movie")
        movie_dirname = sanitize_filename(movie_title)
        movie_dir = os.path.join(OUTPUT_DIR, movie_dirname)
        if os.path.exists(movie_dir):
            shutil.rmtree(movie_dir)
        os.makedirs(movie_dir, exist_ok=True)
        print(f"📁 创建输出目录: {movie_dir}\n")

        def _character_design():
            nonlocal character_data
            char_list = plan.get("characters_to_design", [])
            logger.debug(f"👤 待设计角色列表: {[c['name'] for c in char_list]}")
            
            for char_info in char_list:
                char_name = char_info["name"]
                print(f"👤 角色设计师正在设计角色: {char_name}...")
                
                char_design_prompt = f"{CHARACTER_DESIGNER_SYSTEM_PROMPT}\n\n角色信息：\n{json.dumps(char_info, ensure_ascii=False)}"
                
                try:
                    design_response = volc_ai.chat(char_design_prompt, model="doubao-seed-2-0-pro-260215")
                except Exception as e:
                    print(f"⚠️ 角色设计LLM调用失败，使用默认设计: {e}")
                    design_response = json.dumps({
                        "character_name": char_name,
                        "main_prompt": f"动漫风格角色 {char_name}",
                        "front_view_prompt": f"{char_name} 正面视图",
                        "side_view_prompt": f"{char_name} 侧面视图",
                        "back_view_prompt": f"{char_name} 背面视图",
                        "all_in_one_concept_prompt": f"专业动漫角色设计，{char_name}"
                    })
                
                try:
                    design_response = clean_json_response(design_response)
                    design = json.loads(design_response)
                except Exception:
                    design = {
                        "character_name": char_name,
                        "main_prompt": f"动漫风格角色 {char_name}",
                        "front_view_prompt": f"{char_name} 正面视图",
                        "side_view_prompt": f"{char_name} 侧面视图",
                        "back_view_prompt": f"{char_name} 背面视图",
                        "all_in_one_concept_prompt": f"专业动漫角色设计，{char_name}"
                    }
                
                concept_prompt = design.get("all_in_one_concept_prompt", f"专业动漫角色设计，{char_name}")
                concept_url = None
                try:
                    concept_url = volc_ai.text_to_image(concept_prompt)
                except Exception as e:
                    print(f"❌ 角色概念图生成失败: {e}")
                
                concept_path = os.path.join(movie_dir, sanitize_filename(f"{char_name}_concept.png"))
                if concept_url:
                    download_file(concept_url, concept_path)
                
                add_character(
                    design.get("character_name", char_name),
                    design.get("main_prompt", ""),
                    design.get("front_view_prompt", ""),
                    design.get("side_view_prompt", ""),
                    design.get("back_view_prompt", ""),
                    concept_path if concept_url else None
                )
                character_data[design.get("character_name", char_name)] = {
                    **design,
                    "concept_url": concept_url,
                    "concept_path": concept_path
                }
                
                logger.debug(f"👤 角色 {char_name} 设计完成，概念图: {'已生成' if concept_url else '未生成'}")
                print(f"✅ 角色 {char_name} 设计完成！\n")
            return character_data
        character_data = manager.execute_task(
            "character_design", 
            _character_design,
            input_data={"character_count": len(plan.get("characters_to_design", []))},
            result_summary=lambda res: f"完成角色设计: {list(res.keys())}"
        )

        def _storyboard_design():
            nonlocal storyboard_data, storyboard_records
            total_shots = sum(len(scene.get("shots", [])) for scene in plan.get("scenes", []))
            logger.debug(f"🎞️  开始分镜设计，总分镜数: {total_shots}")
            
            for scene in plan.get("scenes", []):
                for shot in scene.get("shots", []):
                    shot_idx = shot["shot_index"]
                    print(f"🎞️ 分镜设计师正在规划分镜: Scene {scene['scene_index']} Shot {shot_idx}...")
                    
                    relevant_chars = [character_data[name] for name in shot.get("characters", []) if name in character_data]
                    storyboard_prompt = f"{STORYBOARD_DESIGNER_SYSTEM_PROMPT}\n\n分镜描述: {shot['shot_description']}\n角色设定: {json.dumps(relevant_chars, ensure_ascii=False)}"
                    
                    try:
                        storyboard_response = volc_ai.chat(storyboard_prompt, model="doubao-seed-2-0-pro-260215")
                    except Exception as e:
                        print(f"⚠️ 分镜设计LLM调用失败，使用默认设计: {e}")
                        storyboard_response = json.dumps({
                            "shot_index": shot_idx,
                            "image_prompt": f"动漫风格，{shot['shot_description']}",
                            "video_generation_guidance": f"动态镜头，时长 {shot.get('duration', 5)} 秒"
                        })
                    
                    try:
                        storyboard_response = clean_json_response(storyboard_response)
                        storyboard = json.loads(storyboard_response)
                    except Exception:
                        storyboard = {
                            "shot_index": shot_idx,
                            "image_prompt": f"动漫风格，{shot['shot_description']}",
                            "video_generation_guidance": f"动态镜头，时长 {shot.get('duration', 5)} 秒"
                        }
                    
                    img_prompt = storyboard.get("image_prompt", shot['shot_description'])
                    
                    ref_image_urls = []
                    character_descriptions = []
                    storyboard_chars = shot.get("characters", [])
                    for char_name in storyboard_chars:
                        char_db = get_character(char_name)
                        if char_db and char_db.get("concept_url"):
                            ref_image_urls.append(char_db["concept_url"])
                            character_descriptions.append(f"{char_name}: {char_db.get('main_prompt', '')}")
                        elif char_name in character_data and character_data[char_name].get("concept_url"):
                            ref_image_urls.append(character_data[char_name]["concept_url"])
                            character_descriptions.append(f"{char_name}: {character_data[char_name].get('main_prompt', '')}")
                    
                    img_url = None
                    img_url_for_video = None
                    if ref_image_urls:
                        print(f"  🖼️  使用图生图，参考 {len(ref_image_urls)} 个角色概念图...")
                        try:
                            img_url = volc_ai.image_to_image(prompt=img_prompt, image_urls=ref_image_urls)
                        except Exception as e:
                            print(f"  ⚠️ 图生图失败，回退到文生图: {e}")
                            print(f"  🖼️  使用文生图...")
                            img_url = volc_ai.text_to_image(img_prompt)
                    else:
                        print(f"  🖼️  无参考图，使用文生图...")
                        img_url = volc_ai.text_to_image(img_prompt)
                    
                    logger.debug(f"🎞️  分镜 {shot_idx} 4K 图已生成: {img_url[:80]}...")
                    
                    qa_result = qa_inspector_agent(
                        volc_ai,
                        img_url,
                        ref_image_urls,
                        img_prompt,
                        character_descriptions=character_descriptions,
                        shot_description=shot["shot_description"],
                        max_retries=1
                    )
                    img_url = qa_result["first_frame_url"]
                    
                    img_filename = sanitize_filename(f"shot_{scene['scene_index']}_{shot_idx}_first_frame.png")
                    img_path = os.path.join(movie_dir, img_filename)
                    if img_url:
                        download_file(img_url, img_path)
                    
                    img_url_for_video = img_url
                    
                    img_filename_2k = sanitize_filename(f"shot_{scene['scene_index']}_{shot_idx}_first_frame_2k.png")
                    img_path_2k = os.path.join(movie_dir, img_filename_2k)
                    try:
                        compress_image(img_path, img_path_2k, max_width=2048, max_height=2048)
                        print(f"✅ 已生成本地 2K 压缩图")
                        logger.debug(f"🎞️  分镜 {shot_idx} 2K 压缩图已保存: {img_path_2k}")
                        
                        print(f"☁️  正在上传 2K 压缩图到对象存储...")
                        tos_object_key = f"movie_gen/{os.path.basename(movie_dir)}/{img_filename_2k}"
                        img_url_for_video = upload_to_tos(img_path_2k, tos_object_key)
                        print(f"✅ 2K 压缩图已上传到对象存储: {img_url_for_video[:80]}...")
                        logger.debug(f"🎞️  分镜 {shot_idx} 2K 图已上传: {img_url_for_video}")
                    except Exception as e:
                        print(f"⚠️  处理 2K 图失败，将使用原图: {e}")
                        logger.warning(f"🎞️  分镜 {shot_idx} 2K 图处理失败: {e}")
                        img_path_2k = None
                        img_url_for_video = img_url
                    
                    video_guidance = storyboard.get("video_generation_guidance", {})
                    video_prompt = video_guidance.get("prompt", shot['shot_description'])
                    duration_str = str(video_guidance.get("duration", shot.get("duration", 5)))
                    duration_str = re.sub(r'\D', '', duration_str)
                    duration = int(duration_str) if duration_str else shot.get("duration", 5)
                    
                    add_storyboard(
                        shot_idx,
                        shot["shot_description"],
                        ", ".join(shot.get("characters", [])),
                        shot.get("dialogue", ""),
                        shot.get("bgm_sfx", ""),
                        storyboard.get("image_prompt", ""),
                        img_path if img_url else None,
                        None,
                        duration
                    )
                    
                    storyboard_data.append({
                        "scene_index": scene['scene_index'],
                        "shot_index": shot_idx,
                        "shot_description": shot['shot_description'],
                        "img_url": img_url,
                        "img_url_for_video": img_url_for_video,
                        "img_path": img_path,
                        "video_generation_guidance": str(storyboard.get("video_generation_guidance", shot['shot_description'])),
                        "duration": duration
                    })
                    
                    storyboard_records.append({
                        "description": shot["shot_description"],
                        "characters": ", ".join(shot.get("characters", [])),
                        "dialogue": shot.get("dialogue", ""),
                        "bgm_sfx": shot.get("bgm_sfx", ""),
                        "image_prompt": storyboard.get("image_prompt", ""),
                        "video_prompt": video_prompt,
                        "duration": duration
                    })
                    
                    logger.debug(f"🎞️  分镜 {shot_idx} 设计完成，4K图: {'已生成' if img_url else '未生成'}, 2K图: {'已生成' if img_url_for_video else '未生成'}")
                    print(f"✅ 分镜 Scene {scene['scene_index']} Shot {shot_idx} 完成！\n")
            return storyboard_data
        storyboard_data = manager.execute_task(
            "storyboard_design", 
            _storyboard_design,
            input_data={"total_shots": sum(len(scene.get("shots", [])) for scene in plan.get("scenes", []))},
            result_summary=lambda res: f"完成分镜设计: {len(res)} 个分镜"
        )

        def _video_generation():
            nonlocal video_paths
            logger.debug(f"🎬 开始视频生成，分镜数: {len(storyboard_data)}")
            
            for sb in storyboard_data:
                shot_idx = sb["shot_index"]
                scene_idx = sb["scene_index"]
                print(f"🎬 正在生成分镜视频: Scene {scene_idx} Shot {shot_idx}...")
                
                vid_url = None
                vid_filename = sanitize_filename(f"shot_{scene_idx}_{shot_idx}.mp4")
                vid_path = os.path.join(movie_dir, vid_filename)
                
                img_to_use = sb.get("img_url_for_video", sb["img_url"])
                if img_to_use:
                    try:
                        video_prompt = sb["video_generation_guidance"]
                        if isinstance(video_prompt, dict) and "prompt" in video_prompt:
                            video_prompt = video_prompt["prompt"]
                        duration = sb["duration"]
                        logger.debug(f"🎬 分镜 {shot_idx} 视频生成参数: prompt={len(video_prompt)} chars, duration={duration}s")
                        print(f"🎬 正在生成视频 (基于首帧)...")
                        vid_url = volc_ai.image_to_video(
                            prompt=video_prompt,
                            first_frame=img_to_use,
                            duration=duration
                        )
                        logger.debug(f"🎬 分镜 {shot_idx} 视频已生成: {vid_url[:80]}...")
                    except Exception as e:
                        print(f"⚠️ 视频生成失败: {e}")
                        logger.error(f"🎬 分镜 {shot_idx} 视频生成失败: {e}")
                
                if vid_url:
                    download_file(vid_url, vid_path)
                    video_paths.append(vid_path)
                    logger.debug(f"🎬 分镜 {shot_idx} 视频已保存: {vid_path}")
                    print(f"✅ 分镜视频 Scene {scene_idx} Shot {shot_idx} 完成！\n")
                else:
                    print(f"⚠️  分镜视频 Scene {scene_idx} Shot {shot_idx} 未生成，跳过\n")
                    logger.warning(f"🎬 分镜 {shot_idx} 视频未生成")
            
            logger.debug(f"🎬 视频生成完成，成功生成 {len(video_paths)}/{len(storyboard_data)} 个视频")
            return video_paths
        video_paths = manager.execute_task(
            "video_generation", 
            _video_generation,
            input_data={"storyboard_count": len(storyboard_data)},
            result_summary=lambda res: f"成功生成 {len(res)}/{len(storyboard_data)} 个视频，视频路径: {res}"
        )

        final_video_path = None
        def _video_editing():
            nonlocal final_video_path
            logger.debug(f"🎬 开始视频拼接，待拼接视频: {video_paths}")
            if video_paths:
                movie_title = plan.get('movie_title', 'final_movie')
                final_video_filename = sanitize_filename(f"{movie_title}.mp4")
                final_video_path = os.path.join(movie_dir, final_video_filename)
                logger.debug(f"🎬 输出路径: {final_video_path}")
                final_video_path = merge_videos(video_paths, final_video_path, temp_dir=movie_dir)
            return final_video_path
        final_video_path = manager.execute_task(
            "video_editing", 
            _video_editing,
            input_data={"video_count": len(video_paths), "video_paths": video_paths},
            result_summary=lambda res: f"视频拼接完成，最终成片: {res}" if res else "视频拼接跳过"
        )

        def _generate_project_md():
            generate_project_md(movie_dir, script_content, plan, character_data, storyboard_records)
            return True
        manager.execute_task(
            "generate_project_md", 
            _generate_project_md,
            input_data={"movie_dir": movie_dir},
            result_summary="项目文档生成完成"
        )

        def _finalization():
            logger.debug("🏁 开始最终整理")
            print("\n🎉 ===== 电影生成主流程完成！=====")
            print(f"🎬 电影标题: {plan.get('movie_title')}")
            print(f"📹 分镜数量: {sum(len(scene.get('shots', [])) for scene in plan.get('scenes', []))}")
            print(f"🎥 生成视频数: {len(video_paths)}")
            if final_video_path:
                print(f"🎞️  最终成片: {final_video_path}")
            print(f"⏱️  总时长: {sum(shot['duration'] for scene in plan['scenes'] for shot in scene['shots'])} 秒")
            print(f"📁 输出目录: {movie_dir}")
            
            report_path = os.path.join(movie_dir, "workflow_report.json")
            manager.save_report(report_path)
            logger.debug(f"📄 工作流报告已保存: {report_path}")
            return True
        manager.execute_task(
            "finalization", 
            _finalization,
            input_data={
                "movie_title": plan.get('movie_title'),
                "total_shots": sum(len(scene.get("shots", [])) for scene in plan.get("scenes", [])),
                "video_count": len(video_paths),
                "final_video": final_video_path
            },
            result_summary=lambda res: f"电影生成完成: {plan.get('movie_title')}"
        )

    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        manager.end_workflow()

if __name__ == "__main__":
    main()
