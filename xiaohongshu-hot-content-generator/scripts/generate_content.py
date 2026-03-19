#!/usr/bin/env python3
import sys
import argparse
from search import search_cases
from prompts import generate_prompts
from image_generator import generate_images, validate_images
from output import send_to_feishu
from xiaohongshu_publisher import publish_note, ensure_chrome_running, inject_cookies, check_login_status


def main():
    parser = argparse.ArgumentParser(description="小红书热门内容生成器")
    parser.add_argument("--publish", action="store_true", help="生成内容后自动发布到小红书")
    parser.add_argument("--topic", type=str, help="指定生成内容的主题，默认搜索OpenClaw商业化变现")
    args = parser.parse_args()

    try:
        if args.publish:
            print("🚀 准备发布模式，初始化环境...")
            print("1️⃣  确保 Chrome 浏览器正在运行...")
            ensure_chrome_running()
            print("2️⃣  注入 cookies...")
            inject_cookies()
            print("3️⃣  检查登录状态...")
            ok, msg = check_login_status()
            if not ok:
                print(f"❌ {msg}")
                print("⚠️  发布功能需要有效 cookies，请检查 .env 配置")
                return
            print("✅ 登录检查通过！")

        case = search_cases(args.topic)
        prompt_json = generate_prompts(case)
        image_urls = generate_images(prompt_json)
        valid = validate_images(image_urls, prompt_json)
        if not valid:
            print("❌ 图片校验不通过，重新生成...")
            return main()
        send_to_feishu(prompt_json, image_urls)

        if args.publish:
            title = prompt_json["images"][0]["title"]
            content = prompt_json["copy"]
            tags = prompt_json["tags"]
            publish_success = publish_note(title, content, image_urls, tags)
            if publish_success:
                print("\n🎉 小红书热门图文生成并发布完成！")
            else:
                print("\n⚠️  内容生成完成，但发布失败")
        else:
            print("\n🎉 小红书热门图文生成完成！")
            print("\n提示：如需自动发布到小红书，请使用 --publish 参数")
            print("如需配置发布功能，请使用 --setup-guide 参数")

    except Exception as e:
        print(f"❌ 生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

