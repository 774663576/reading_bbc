import requests
from bs4 import BeautifulSoup
import os
import logging
from typing import Optional
from urllib.parse import urljoin
import random
from datetime import datetime
from dataclasses import dataclass, asdict
import json

@dataclass
class ArticleInfo:
    """文章信息数据类"""
    url: str
    title: str  # 格式: title_en=title_cn
    cover: str  # 封面图片地址
    mp3_url: str
    pdf_url: str
    update_time: str
    views: int
    category: str = "take-away-english"  # 添加默认值

class BBCLearningEnglishScraper:
    def __init__(self, category: str = 'take-away-english'):
        """初始化爬虫配置"""
        self.category = category  # 使用 category 来动态设置输出目录
        self.base_output_dir = category  # 将 category 作为输出文件夹的目录
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def extract_title(self, soup: BeautifulSoup) -> str:
        """提取并格式化标题"""
        heading_div = soup.find('div', class_='widget widget-heading clear-left')
        if heading_div:
            h3 = heading_div.find('h3')
            if h3:
                full_title = h3.text.strip()
                # 分割英文和中文标题
                parts = full_title.split('=') if '=' in full_title else full_title.split(' ', maxsplit=1)
                if len(parts) == 2:
                    return f"{parts[0].strip()}={parts[1].strip()}"
        return ""

    def get_cover_image_url(self, article_soup: BeautifulSoup, base_url: str) -> str:
        """获取封面图片URL"""
        audio_player = article_soup.find('div', class_='audio-player')
        if audio_player:
            img = audio_player.find('img')
            if img and img.get('src'):
                return urljoin(base_url, img['src'])
        return ""

    def create_directories(self, base_name: str):
        """创建必要的目录结构"""
        directories = ['img', 'pdf', 'mp3']
        for dir_name in directories:
            dir_path = os.path.join(self.base_output_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)

    def download_file(self, url: str, output_path: str) -> bool:
        """下载文件并保存到指定路径"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
            self.logger.info(f"文件下载成功: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"下载文件失败 {url}: {str(e)}")
            return False

    def process_images(self, article_soup: BeautifulSoup, base_url: str, base_name: str) -> BeautifulSoup:
        """只处理audio-player类中的图片"""
        audio_player = article_soup.find('div', class_='audio-player')
        if audio_player:
            img = audio_player.find('img')
            if img and img.get('src'):
                img_url = urljoin(base_url, img['src'])
                img_filename = f"{base_name}.jpg"
                img_path = os.path.join(self.base_output_dir, 'img', img_filename)
                
                if self.download_file(img_url, img_path):
                    # img['src'] = f'./img/{img_filename}'
                    img['src'] = f"http://readingstuday.top/{self.base_output_dir}/img/{base_name}.jpg"

        
        return article_soup

    def find_resource_urls(self, article_soup: BeautifulSoup, base_url: str) -> tuple[str, str]:
        """查找PDF和MP3的URL"""
        pdf_url = ""
        mp3_url = ""
        
        download_links = article_soup.find_all('a', href=True)
        for link in download_links:
            href = link.get('href', '')
            text = link.get_text().strip()
            
            if '文字稿' in text and '.pdf' in href.lower():
                pdf_url = urljoin(base_url, href)
            elif '音频' in text and ('.mp3' in href.lower() or '/download/' in href):
                mp3_url = urljoin(base_url, href)
        
        return pdf_url, mp3_url

    def download_resources(self, article_soup: BeautifulSoup, base_url: str, base_name: str):
        """下载PDF和MP3文件"""
        pdf_url, mp3_url = self.find_resource_urls(article_soup, base_url)
        
        if pdf_url:
            pdf_path = os.path.join(self.base_output_dir, 'pdf', f'{base_name}.pdf')
            self.download_file(pdf_url, pdf_path)
            
        if mp3_url:
            mp3_path = os.path.join(self.base_output_dir, 'mp3', f'{base_name}.mp3')
            self.download_file(mp3_url, mp3_path)

    def clean_article(self, article_soup: BeautifulSoup) -> BeautifulSoup:
        """清理文章内容"""
        elements_to_remove = [
            ('div', {'class': 'widget widget-pagelink widget-pagelink-next-activity'}),
            ('div', {'class': 'widget widget-list widget-list-automatic'}),
            ('div', {'class': 'clearfix'}),
            ('div', {'class': 'widget widget-bbcle-featuresubheader'}),
            ('div', {'id': 'heading-'}),
            ('div', {'class': 'widget-container widget-container-right'})
        ]
        
        for element in elements_to_remove:
            parts = article_soup.find_all(*element)
            for part in parts:
                part.decompose()
                
        return article_soup

    def generate_html(self, article_content: str) -> str:
        """生成HTML内容"""
        return f"""
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="./style.css">
</head>
<body>
    {article_content}
  <script src="./script.js"></script>
</body>
</html>
"""

    def scrape_article(self, url: str) -> Optional[ArticleInfo]:
        """爬取和保存文章的主要方法"""
        try:
            # 获取页面
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 解析内容
            soup = BeautifulSoup(response.content, 'html.parser')
            article = soup.find('div', {'role': 'article'})
            
            if not article:
                self.logger.error("找不到文章内容")
                return None

            # 提取标题
            title = self.extract_title(soup)
            
            # 获取封面图片URL
            cover = self.get_cover_image_url(article, url)
            
            # 从URL提取基础名称
            base_name = url.split('/')[-1]
            
            # 创建必要的目录
            self.create_directories(base_name)
            
            # 获取资源URL
            pdf_url, mp3_url = self.find_resource_urls(article, url)
            
            # 处理图片
            article = self.process_images(article, url, base_name)
            
            # 下载PDF和MP3
            self.download_resources(article, url, base_name)
            
            # 清理文章内容
            cleaned_article = self.clean_article(article)
            
            # 生成HTML
            html_content = self.generate_html(cleaned_article.prettify())

            # 保存HTML文件
            file_path = os.path.join(self.base_output_dir, f'{base_name}.html')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"文章成功保存到: {file_path}")

            # 创建文章信息对象
            article_info = ArticleInfo(
                url=f"http://readingstuday.top/bbc/{self.category}/{base_name}.html",  # 修改URL
                title=title,
                cover=f"http://readingstuday.top/{self.base_output_dir}/img/{base_name}.jpg",  # 修改封面
                mp3_url=f"http://readingstuday.top/{self.base_output_dir}/mp3/{base_name}.mp3",  # 修改mp3路径
                pdf_url=f"http://readingstuday.top/{self.base_output_dir}/pdf/{base_name}.pdf",  # 修改pdf路径
                update_time=datetime.now().strftime('%Y-%m-%d'),
                views=random.randint(5000, 10000),
                category=self.category  # 设置category
            )
            
            return article_info
            
        except Exception as e:
            self.logger.error(f"处理文章失败: {str(e)}")
            return None

def main():
    scraper = BBCLearningEnglishScraper(category='take-away-english')
    url = 'https://www.bbc.co.uk/learningenglish/chinese/features/take-away-english/ep-250203'
    article_info = scraper.scrape_article(url)
    
    if article_info:
        # 打印 ArticleInfo 对象为 JSON 格式
        print(json.dumps(asdict(article_info), ensure_ascii=False, indent=4))
    else:
        print("爬取文章失败")
        exit(1)

if __name__ == "__main__":
    main()
