import requests
import logging
import re
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_m3u():
    """下载原始 M3U 文件"""
    url = "https://raw.githubusercontent.com/Tzwcard/ChinaTelecom-GuangdongIPTV-RTP-List/refs/heads/master/GuangdongIPTV_rtp_all.m3u"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logging.info("Successfully downloaded M3U file")
        return response.text
    except requests.RequestException as e:
        logging.error(f"Failed to download M3U file: {e}")
        raise

def process_m3u(content):
    """处理 M3U 内容，替换 RTP 地址并添加 tvg-id"""
    try:
        # 将内容按行分割
        lines = content.split('\n')
        processed_lines = []
        rtp_count = 0
        tvg_count = 0
        
        for line in lines:
            if line.startswith('#EXTINF:'):
                # 查找现有的 tvg-name
                tvg_name_match = re.search(r'tvg-name="([^"]*)"', line)
                if tvg_name_match:
                    tvg_name = tvg_name_match.group(1)
                    # 检查是否已经有 tvg-id
                    if 'tvg-id="' not in line:
                        # 在 tvg-name 后添加 tvg-id
                        line = line.replace(f'tvg-name="{tvg_name}"', 
                                         f'tvg-name="{tvg_name}" tvg-id="{tvg_name}"')
                        tvg_count += 1
                processed_lines.append(line)
            elif line.startswith('rtp://'):
                # 替换 RTP 地址
                line = line.replace('rtp://', 'http://10.109.60.250:4022/udp/')
                rtp_count += 1
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        # 重新组合内容
        processed_content = '\n'.join(processed_lines)
        
        logging.info(f"Replaced {rtp_count} RTP addresses")
        logging.info(f"Added {tvg_count} tvg-id attributes")
        
        return processed_content
    except Exception as e:
        logging.error(f"Error processing M3U content: {e}")
        raise

def save_m3u(content, filename='processed.m3u'):
    """保存处理后的 M3U 文件"""
    try:
        output_path = Path(filename)
        output_path.write_text(content, encoding='utf-8')
        logging.info(f"Successfully saved processed M3U to {filename}")
    except Exception as e:
        logging.error(f"Failed to save M3U file: {e}")
        raise

def main():
    try:
        # 下载原始文件
        logging.info("Starting M3U processing")
        original_content = download_m3u()
        
        # 处理内容
        processed_content = process_m3u(original_content)
        
        # 保存处理后的文件
        save_m3u(processed_content)
        
        logging.info("M3U processing completed successfully")
    except Exception as e:
        logging.error(f"Failed to process M3U file: {e}")
        raise

if __name__ == "__main__":
    main()
