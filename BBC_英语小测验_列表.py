import requests
from bs4 import BeautifulSoup
import os
import logging
from typing import Optional, List
from urllib.parse import urljoin
import random
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import time
import re


titleDict = {}

@dataclass
class ArticleInfo:
    """文章信息数据类"""
    article_id:str
    url: str
    title: str  # 格式: title_en=title_cn
    cover: str  # 封面图片地址
    mp3_url: str
    pdf_url: str
    update_time: str
    views: int
    category: str = "english-quizzes"  # 添加默认值

class BBCLearningEnglishScraper:
    def __init__(self, category: str = 'english-quizzes', start_pos: int = 0, count: int = 50):
        """初始化爬虫配置"""
        self.base_url = 'https://www.bbc.co.uk'
        self.category = category
        self.base_output_dir = category
        self.start_pos = start_pos  # 新增：起始位置
        self.count = count  # 改名：原来的limit改为count
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # 创建输出目录
        os.makedirs('output', exist_ok=True)
        os.makedirs(self.base_output_dir, exist_ok=True)

    def get_article_urls(self, list_url: str) -> List[str]:
        """获取列表页中所有文章的URL，从后往前排序并限制数量"""
        try:
            self.logger.info(f"正在获取列表页: {list_url}")
            response = requests.get(list_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content_list = soup.find('div', class_='widget widget-bbcle-coursecontentlist widget-bbcle-coursecontentlist-standard widget-progress-enabled')
            
            if not content_list:
                self.logger.error("找不到文章列表")
                return []
            
            article_urls = []
            for item in content_list.find_all('li', class_='course-content-item'):
                link = item.find('h2').find('a')
                full_url=''
                if link and 'href' in link.attrs:
                    full_url = urljoin(self.base_url, link['href'])
                    article_urls.append(full_url)
                    self.logger.info(f"找到文章: {full_url}")
                    text = link.text.strip()
                    match = re.match(r"([A-Za-z0-9\s'.-]+)([\u4e00-\u9fa5]+)", text)
                    if match:
                        english_text = match.group(1).strip()
                        chinese_text = match.group(2).strip()
                        title = f"{english_text}={chinese_text}"
                        # print(title)
                    else:
                        title=text
                    titleDict[full_url] = title


                
            
            # 反转列表顺序并限制数量
            article_urls.reverse()
            self.logger.info(f"总共: {len(article_urls)}篇文章")

            selected_urls = article_urls[self.start_pos:self.start_pos + self.count]

            self.logger.info(f"从第{self.start_pos + 1}篇开始，获取{len(selected_urls)}篇文章")

            return selected_urls
            
        except Exception as e:
             self.logger.error(f"获取文章列表失败: {str(e)}")
             return []

    def extract_title(self, soup: BeautifulSoup) -> str:
         """从列表中获取标题并格式化"""
          # 查找列表中的 <a> 标签
         a_tag = soup.find('a', href=True)
         if a_tag:
            full_title = a_tag.text.strip()
            # 使用正则表达式来分割英文和中文标题
            match = re.match(r'([A-Za-z0-9\s\-\']+)([\u4e00-\u9fa5]+)', full_title)
            if match:
               title_en = match.group(1).strip()
               title_cn = match.group(2).strip()
               return f"{title_en}={title_cn}"
         return ""

    def get_cover_image_url(self, article_soup: BeautifulSoup, base_url: str) -> str:
        """获取封面图片URL"""
        audio_player = article_soup.find('div', class_='image-single')
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
        
        if os.path.exists(output_path):
           self.logger.info(f"文件已存在，跳过下载: {output_path}")
           return True
    
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
        """处理audio-player类中的图片，将src改为与cover相同的格式"""
        audio_player = article_soup.find('div', class_='image-single')
        if audio_player:
            img = audio_player.find('img')
            if img and img.get('src'):
                img_url = urljoin(base_url, img['src'])
                img_filename = f"{base_name}.jpg"
                img_path = os.path.join(self.base_output_dir, 'img', img_filename)
                
                if self.download_file(img_url, img_path):
                    # 修改图片src为与cover相同的URL格式
                    img['src'] = f"https://774663576.github.io/reading_bbc/{self.base_output_dir}/img/{base_name}.jpg"
        
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
            # title = self.extract_title(soup)
            title=titleDict[url]
            self.logger.info(f"title: {title}")

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
                article_id=base_name,
                url=f"http://readingstuday.top/bbc/{self.category}/{base_name}.html",
                title=title,
                cover=f"https://774663576.github.io/reading_bbc/{self.base_output_dir}/img/{base_name}.jpg",
                mp3_url=f"https://774663576.github.io/reading_bbc/{self.base_output_dir}/mp3/{base_name}.mp3",
                pdf_url=f"https://774663576.github.io/reading_bbc/{self.base_output_dir}/pdf/{base_name}.pdf",
                update_time=datetime.now().strftime('%Y-%m-%d'),
                views=random.randint(5000, 10000),
                category=self.category,
            )
            
            return article_info
            
        except Exception as e:
            self.logger.error(f"处理文章失败: {str(e)}")
            return None

    def scrape_all_articles(self, list_url: str):
        """爬取指定数量的文章"""
        # 获取文章URL（已经过反转和限制）
        article_urls = self.get_article_urls(list_url)
        self.logger.info(f"将处理最新的 {len(article_urls)} 篇文章")
        
        # 存储所有文章信息
        all_articles = []
        
        # 遍历爬取每篇文章
        for index, url in enumerate(article_urls, 1):
            try:
                self.logger.info(f"正在处理第 {index}/{len(article_urls)} 篇文章: {url}")
                article_info = self.scrape_article(url)
                
                if article_info:
                    all_articles.append(asdict(article_info))
                    self.logger.info("文章处理成功")
                
                # 添加延时，避免请求过于频繁
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                self.logger.error(f"处理文章失败 {url}: {str(e)}")
                continue
        
        # 保存所有文章信息到JSON文件
        if all_articles:
            output_file = os.path.join('output', f'{self.category}_articles.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_articles, f, ensure_ascii=False, indent=4)
            self.logger.info(f"所有文章信息已保存到: {output_file}")
            
        return all_articles

def main():
    # 创建爬虫实例，设置限制为50篇文章
    scraper = BBCLearningEnglishScraper(
        category='english-quizzes',
        start_pos=0,  #从第0篇开始
        count=499 #499       # 爬取50篇文章
    )
    
    # 列表页URL
    list_url = 'https://www.bbc.co.uk/learningenglish/chinese/features/english-quizzes'
    
    # 开始爬取
    articles = scraper.scrape_all_articles(list_url)
    
    # 打印统计信息
    print(f"\n爬取完成！总共处理 {len(articles)} 篇文章")

if __name__ == "__main__":
    main()