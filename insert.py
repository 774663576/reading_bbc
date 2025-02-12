import json
import mysql.connector

# 连接到 MySQL 数据库
conn = mysql.connector.connect(
    host='59.110.149.111',
    user='root',
    password='SP123456!',
    database='reading'
)
cursor = conn.cursor()

# 创建表
cursor.execute('''
CREATE TABLE IF NOT EXISTS bbc_english_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id VARCHAR(20),
    url VARCHAR(255),
    title VARCHAR(255),
    cover VARCHAR(255),
    mp3_url VARCHAR(255),
    mp4_url VARCHAR(255),
    pdf_url VARCHAR(255),
    update_time DATE,
    views INT,
    category VARCHAR(50)
);
''')

# 读取 JSON 文件
with open('/Users/songbinbin/Downloads/reading_app/book/read_book/voa_tingclass/bbc/authentic-real-english_articles.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 插入数据
for item in data:
    cursor.execute('''
    INSERT INTO bbc_english_articles (article_id,url, title, cover, mp3_url,mp4_url, pdf_url, update_time, views, category)
    VALUES (%s,%s, %s, %s, %s,%s, %s, %s, %s, %s)
    ''', (
        item['article_id'],
        item['url'],
        item['title'],
        item['cover'],
        item['mp3_url'],
        "",
        item['pdf_url'],
        item['update_time'],
        item['views'],
        item['category']
    ))

# 提交事务
conn.commit()

# 关闭连接
cursor.close()
conn.close()

print("数据插入完成")