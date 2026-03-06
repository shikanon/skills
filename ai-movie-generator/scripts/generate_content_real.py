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

scripts_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, scripts_dir)

from config import OUTPUT_DIR, DATA_DIR
from database import init_db, add_character, get_character, add_storyboard
from volc_engine_client import VolcEngineAI
from prompts import (
    DIRECTOR_SYSTEM_PROMPT,
    CHARACTER_DESIGNER_SYSTEM_PROMPT,
    STORYBOARD_DESIGNER_SYSTEM_PROMPT,
    EDITOR_SYSTEM_PROMPT,
    QA_INSPECTOR_SYSTEM_PROMPT
)

print("🎬 ===== AI 电影生成器 - 真实 API 完整流程 =====\n")

def download_file(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return save_path
    except Exception as e:
        print(f"❌ 下载文件失败: {e}")
        return None

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

def director_agent(volc_ai, script_content):
    print("🎬 ===== Agent 1/4: 大导演分析剧本...")
    director_prompt = f"{DIRECTOR_SYSTEM_PROMPT}\n\n请分析以下剧本：\n{script_content}"
    response = volc_ai.chat(director_prompt, model="doubao-seed-2-0-pro-260215")
    response = clean_json_response(response)
    plan = json.loads(response)
    print(f"✅ 大导演分析完成！电影标题: {plan.get('movie_title')}\n")
    return plan

def character_designer_agent(volc_ai, plan, movie_dir):
    print("👤 ===== Agent 2/4: 角色设计师设计角色...")
    character_data = {}
    for char_info in plan.get("characters_to_design", []):
        char_name = char_info.get("name", "Unknown")
        char_desc = char_info.get("brief_description", "")
        print(f"  🎨 设计角色: {char_name}")
        
        char_design_prompt = f"{CHARACTER_DESIGNER_SYSTEM_PROMPT}\n\n角色信息：\n角色名称：{char_name}\n角色描述：{char_desc}"
        design_response = volc_ai.chat(char_design_prompt, model="doubao-seed-2-0-pro-260215")
        design_response = clean_json_response(design_response)
        
        try:
            design = json.loads(design_response)
        except Exception:
            design = {
                "character_name": char_name,
                "main_prompt": f"动漫风格角色 {char_name}",
                "front_view_prompt": f"{char_name} 正面视图",
                "side_view_prompt": f"{char_name} 侧面视图",
                "back_view_prompt": f"{char_name} 背面视图",
                "all_in_one_concept_prompt": f"专业动漫角色设计页，包含细节区、主视图区、新服装区、动作区、表情区，{char_desc}"
            }
        
        concept_prompt = design.get("all_in_one_concept_prompt", f"专业动漫角色设计，{char_name}")
        print(f"  🖼️  生成角色概念图...")
        concept_url = volc_ai.text_to_image(concept_prompt)
        concept_filename = sanitize_filename(f"{char_name}_concept.png")
        concept_path = os.path.join(movie_dir, concept_filename)
        download_file(concept_url, concept_path)
        
        add_character(
            design.get("character_name", char_name),
            design.get("main_prompt", ""),
            design.get("front_view_prompt", ""),
            design.get("side_view_prompt", ""),
            design.get("back_view_prompt", ""),
            concept_url
        )
        character_data[design.get("character_name", char_name)] = {
            **design,
            "concept_url": concept_url,
            "concept_path": concept_path
        }
        print(f"  ✅ 角色 {char_name} 设计完成\n")
    print("✅ 所有角色设计完成！\n")
    return character_data

def qa_inspector_agent(volc_ai, first_frame_url, ref_image_urls, image_prompt, character_descriptions=None, shot_description="", max_retries=1):
    """
    质检智能体：优化提示词，防止角色崩坏
    """
    print("  🔍 ===== Agent QA: 优化提示词...")
    
    # 构造质检请求
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

def storyboard_designer_agent(volc_ai, plan, character_data, movie_dir):
    print("🎞️ ===== Agent 3/4: 分镜设计师生成分镜...")
    video_paths = []
    storyboard_records = []
    for scene in plan.get("scenes", []):
        for shot in scene.get("shots", []):
            shot_idx = shot["shot_index"]
            print(f"  🎬 Scene {scene['scene_index']} Shot {shot_idx}")
            
            relevant_chars = [character_data[name] for name in shot.get("characters", []) if name in character_data]
            storyboard_prompt = f"{STORYBOARD_DESIGNER_SYSTEM_PROMPT}\n\n分镜描述: {shot['shot_description']}\n角色设定: {json.dumps(relevant_chars, ensure_ascii=False)}"
            
            storyboard_response = volc_ai.chat(storyboard_prompt, model="doubao-seed-2-0-pro-260215")
            storyboard_response = clean_json_response(storyboard_response)
            
            try:
                storyboard = json.loads(storyboard_response)
            except Exception:
                storyboard = {
                    "shot_index": shot_idx,
                    "image_prompt": f"动漫风格，{shot['shot_description']}",
                    "characters": shot.get("characters", []),
                    "video_generation_guidance": {
                        "prompt": f"动态镜头，时长 {shot.get('duration', 5)} 秒",
                        "duration": shot.get("duration", 5)
                    }
                }
            
            img_prompt = storyboard.get("image_prompt", f"{shot['shot_description']}")
            
            # 从数据库读取角色图用于图生图
            ref_image_urls = []
            character_descriptions = []
            storyboard_chars = storyboard.get("characters", [])
            for char_name in storyboard_chars:
                char_db = get_character(char_name)
                if char_db and char_db.get("concept_url"):
                    ref_image_urls.append(char_db["concept_url"])
                    character_descriptions.append(f"{char_name}: {char_db.get('main_prompt', '')}")
                elif char_name in character_data and character_data[char_name].get("concept_url"):
                    ref_image_urls.append(character_data[char_name]["concept_url"])
                    character_descriptions.append(f"{char_name}: {character_data[char_name].get('main_prompt', '')}")
            
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
            
            # ===== 质检智能体优化提示词 =====
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
            download_file(img_url, img_path)
            
            # 使用 video_generation_guidance 的 prompt 和 duration 生成视频
            video_guidance = storyboard.get("video_generation_guidance", {})
            video_prompt = video_guidance.get("prompt", shot['shot_description'])
            duration_str = str(video_guidance.get("duration", shot.get("duration", 5)))
            duration_str = re.sub(r'\D', '', duration_str)
            duration = int(duration_str) if duration_str else shot.get("duration", 5)
            
            print(f"  🎬 生成视频 (prompt: {video_prompt[:60]}..., duration: {duration}s)...")
            vid_url = None
            try:
                vid_url = volc_ai.image_to_video(
                    prompt=video_prompt,
                    first_frame=img_url,
                    duration=duration
                )
            except Exception as e:
                print(f"  ⚠️ 视频生成功能需要专用API: {e}")
            
            vid_filename = sanitize_filename(f"shot_{scene['scene_index']}_{shot_idx}.mp4")
            vid_path = os.path.join(movie_dir, vid_filename)
            if vid_url:
                download_file(vid_url, vid_path)
                video_paths.append(vid_path)
            
            add_storyboard(
                shot_idx,
                shot["shot_description"],
                ", ".join(shot.get("characters", [])),
                shot.get("dialogue", ""),
                shot.get("bgm_sfx", ""),
                storyboard.get("image_prompt", ""),
                img_path,
                vid_path if vid_url else None,
                duration
            )
            
            # 保存记录用于 project.md
            storyboard_records.append({
                "description": shot["shot_description"],
                "characters": ", ".join(shot.get("characters", [])),
                "dialogue": shot.get("dialogue", ""),
                "bgm_sfx": shot.get("bgm_sfx", ""),
                "image_prompt": storyboard.get("image_prompt", ""),
                "video_prompt": video_prompt,
                "duration": duration
            })
            
            print(f"  ✅ 分镜 Scene {scene['scene_index']} Shot {shot_idx} 完成\n")
    print("✅ 所有分镜完成！\n")
    return video_paths, storyboard_records

def editor_agent(volc_ai, plan, video_paths, movie_dir):
    print("✂️ ===== Agent 4/4: 剪辑师拼接视频...")
    if video_paths:
        print("📋 剪辑师审核分镜顺序...")
        editor_prompt = f"{EDITOR_SYSTEM_PROMPT}\n\n电影标题: {plan.get('movie_title')}\n分镜数量: {len(video_paths)}"
        try:
            editor_response = volc_ai.chat(editor_prompt, model="doubao-seed-2-0-pro-260215")
            editor_response = clean_json_response(editor_response)
            editor_plan = json.loads(editor_response)
            print(f"✅ 剪辑规划: {editor_plan.get('final_movie_description', '')}\n")
        except Exception as e:
            print(f"⚠️ 剪辑师LLM调用失败，按顺序拼接: {e}")
        
        list_file = os.path.join(movie_dir, "video_list.txt")
        with open(list_file, "w") as f:
            for vp in video_paths:
                f.write(f"file '{vp}'\n")
        
        final_video_filename = sanitize_filename(f"{plan.get('movie_title', 'final_movie')}.mp4")
        final_video_path = os.path.join(movie_dir, final_video_filename)
        
        try:
            print("🔗 正在使用 ffmpeg 拼接视频...")
            result = subprocess.run([
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", final_video_path
            ], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ 视频拼接成功！")
            else:
                print(f"⚠️ ffmpeg 输出: {result.stderr}")
        except Exception as e:
            print(f"❌ ffmpeg 拼接失败: {e}")
            final_video_path = None
        
        return final_video_path
    else:
        print("⚠️ 没有视频可以拼接！")
        return None

def main():
    parser = argparse.ArgumentParser(description="AI 电影生成器 - 完整真实流程")
    parser.add_argument("--script", type=str, help="剧本文件路径或直接输入剧本内容")
    args = parser.parse_args()

    if not args.script:
        print("❌ 请提供剧本内容或剧本文件路径。")
        return

    print("===== 步骤 1: 初始化环境 =====")
    init_db()
    volc_ai = VolcEngineAI()

    print("\n===== 步骤 2: 读取剧本 =====")
    script_content = args.script
    if os.path.exists(args.script):
        with open(args.script, "r", encoding="utf-8") as f:
            script_content = f.read()
    print(f"✅ 读取剧本: {script_content[:80]}...\n")

    plan = director_agent(volc_ai, script_content)
    
    # 创建电影标题目录
    movie_title = plan.get("movie_title", "ai_movie")
    movie_dirname = sanitize_filename(movie_title)
    movie_dir = os.path.join(OUTPUT_DIR, movie_dirname)
    if os.path.exists(movie_dir):
        shutil.rmtree(movie_dir)
    os.makedirs(movie_dir, exist_ok=True)
    print(f"📁 创建输出目录: {movie_dir}\n")

    character_data = character_designer_agent(volc_ai, plan, movie_dir)
    video_paths, storyboard_records = storyboard_designer_agent(volc_ai, plan, character_data, movie_dir)
    final_video = editor_agent(volc_ai, plan, video_paths, movie_dir)
    
    # 生成 project.md
    generate_project_md(movie_dir, script_content, plan, character_data, storyboard_records)

    print("\n🎉 ===== 电影生成完成！=====")
    print(f"🎬 电影标题: {movie_title}")
    total_shots = sum(len(scene.get('shots', [])) for scene in plan.get('scenes', []))
    print(f"📹 分镜数量: {total_shots}")
    print(f"⏱️  总时长: {sum(shot['duration'] for scene in plan['scenes'] for shot in scene['shots'])} 秒")
    print(f"📁 输出目录: {movie_dir}")
    if final_video and os.path.exists(final_video):
        print(f"🎥 最终视频: {final_video}")
    print(f"📝 项目记录: {os.path.join(movie_dir, 'project.md')}")

if __name__ == "__main__":
    main()
