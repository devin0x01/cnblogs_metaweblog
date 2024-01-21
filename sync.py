#!/usr/bin/python3
# -*-coding:utf-8 -*-
import xmlrpc.client
import ssl
import sys
import os
import re
import hashlib
import logging
import time

logging.basicConfig(level=logging.INFO)

# 设置 ssl 很重要，否则将报 ssl 错
ssl._create_default_https_context = ssl._create_unverified_context

# 博客园/设置/博客设置(https://i.cnblogs.com/settings)，翻到最下面可以查到username和token
config = {
    'url': 'https://rpc.cnblogs.com/metaweblog/devin1024',  # 这个地址可以查看 MetaWeblog API
    'username': 'devin1024',
    'token': '',
    'file_extension': '.md',
    'encoding': 'UTF-8',
    "posts_max_nr": 1000,
}


class MetaWeblog:
    def __init__(self, url, username, token):
        self.url, self.username, self.token = url, username, token
        self.proxy = xmlrpc.client.ServerProxy(self.url)

    # 博客的ID和用户名等
    def getUsersBlogs(self):
        return self.proxy.blogger.getUsersBlogs('', self.username, self.token)

    def getPost(self, post_id):
        return self.proxy.metaWeblog.getPost(post_id, self.username, self.token)

    def getRecentPosts(self, count):
        return self.proxy.metaWeblog.getRecentPosts(
            '', self.username, self.token, count
        )

    def deletePost(self, post_id):
        return self.proxy.blogger.deletePost(
            '', post_id, self.username, self.token, True
        )

    def newPost(self, article):
        # 下面的categories必须设置为Markdown
        post = dict(
            title=article['title'],
            description=article['content'],
            categories=['[Markdown]'],
            mt_keywords=article['tags'],
        )
        return self.proxy.metaWeblog.newPost('', self.username, self.token, post, True)

    def editPost(self, post_id, article):
        # 下面的categories必须设置为Markdown
        post = dict(
            title=article['title'],
            description=article['content'],
            categories=['[Markdown]'],
            mt_keywords=article['tags'],
        )
        return self.proxy.metaWeblog.editPost(
            post_id, self.username, self.token, post, True
        )


# 根据文章路径设置文章（标题、标签和内容）
def parse_local_artical(path: str, encoding: str = 'UTF-8') -> dict:
    with open(path, 'rb') as f:
        stream = f.read()
    content = stream.decode(encoding)

    # 计算md5值
    hash = hashlib.md5(stream)
    hash_value = hash.hexdigest()

    # 最小匹配，获取文件头
    res = re.match(r"(---((.|[\n])*?)---)", content)
    if not res:
        raise ValueError(f"no headers in article: {path}")

    headers = res.group(1)
    header_lines = res.group(2).split('\n')
    # 去除空行
    header_lines = list(filter(lambda x: x.strip(), header_lines))

    logging.debug(f"header lines: {header_lines}")
    # e.g. lines = ['title: "Notepad++替换"', 'date: 2023-06-18T14:05:25+08:00', 'tags: ["工具", "Notepad++"]', 'categories: []', 'draft: false', 'toc: true']

    # 抽取tags和title
    title, tags = '', []
    for line in header_lines:
        elements = line.split(': ')
        if len(elements) < 2:
            continue
        left, right = elements[0], elements[1]
        if left == 'title':
            # 标题两侧不能有双引号和空格
            title = right.strip(' "')
        elif left == 'tags':
            tags = right.lstrip('[').rstrip(']').replace('"', '')

    # 保证本地文件名和markdown文件里的title内容一致
    if os.path.basename(path) != (title + config['file_extension']):
        raise ValueError(f"filename is not different title element: {path}")

    # 不删文件头，否则会导致md5值和本地不一样
    # content = content.replace(headers, '', 1)

    if not title or not content or not tags:
        raise ValueError(f'title, content and tags cannot be empty: {path}')
    article = {'title': title, 'tags': tags, 'content': content, 'hash': hash_value}
    logging.debug(
        f"parse local file: {path}, title={title}, tags={tags}, hash={hash_value}"
    )

    return article


def get_local_files(dir_name: str, extension: str) -> list:
    res = []
    if not os.path.exists(dir_name):
        logging.error(f"{dir_name} is not existed!")
        return res

    entries = os.listdir(dir_name)
    for file in entries:
        new_path = os.path.join(dir_name, file)
        if os.path.isdir(new_path):
            res.extend(get_local_files(new_path, extension))
        elif file.endswith(extension):
            res.append(new_path)
    return res


# 根据postid删除文章
def delete_post(postid: str) -> bool:
    metaWeblog = MetaWeblog(config["url"], config["username"], config["token"])

    title, status = "", False
    try:
        post = metaWeblog.getPost(postid)
        title = post["title"]
        status = metaWeblog.deletePost(postid)
    except Exception as e:
        logging.fatal(e)
    else:
        logging.info(f"--- delete success: {title}\n")

    return status


def sync_posts(local_files: list[str], strong: bool = False) -> None:
    """保证本地的markdown文章和博客园网站一致

    Args:
        strong (bool, optional): 如果博客园的文章在本地不存在，是否删除博客园的文章. Defaults to False.
    """
    blog = MetaWeblog(config['url'], config['username'], config['token'])
    posts = blog.getRecentPosts(config['posts_max_nr'])

    # 网站的帖子标题和md5
    remote_info = {}
    for post in posts:
        title = post["title"]
        content = post["description"].encode(config["encoding"])
        hash = hashlib.md5(content).hexdigest()
        postid = post["postid"]

        # post["categories"] is array of string
        remote_info[title] = (hash, postid, "[Markdown]" in post["categories"])

    # 和本地比较，获取是新帖子还是需要更新的帖子
    new_articles = []
    modified_articles = []
    skip_posts_nr = 0
    for file in local_files:
        article = parse_local_artical(file, config["encoding"])
        title = article["title"]
        remote = remote_info.get(title)  # no exception

        if remote is None:
            new_articles.append(article)
            continue

        hash, postid, is_md = remote[0], remote[1], remote[2]
        if article["hash"] == hash:
            skip_posts_nr += 1
        else:
            modified_articles.append((article, postid))
        remote_info.pop(title)

    logging.info(
        f"total_articles={len(local_files)}, skip={skip_posts_nr}, new={len(new_articles)}, modified={len(modified_articles)}, waited_to_delete={len(remote_info)}\n"
    )

    # 发布帖子
    cur = 0
    total = len(new_articles)
    for article in new_articles:
        cur += 1
        title = article["title"]

        id = blog.newPost(article)
        if id:
            logging.info(f"[{cur}/{total}] +++ post success: {title}\n")
        else:
            logging.error(f"[{cur}/{total}] +++ post failed: {title}\n")
        if cur < total:
            time.sleep(65)

    # 修改帖子
    cur = 0
    total = len(modified_articles)
    for article, postid in modified_articles:
        cur += 1
        title = article["title"]

        status = blog.editPost(postid, article)
        if status:
            logging.info(f"[{cur}/{total}] *** update success: {title}\n")
        else:
            logging.error(f"[{cur}/{total}] *** update failed: {title}\n")
        if cur < total:
            time.sleep(65)

    # 删除网站上存在，但是本地不存在的帖子
    if strong:
        cur = 0
        total = len(remote_info)
        for title in remote_info:
            cur += 1
            postid = remote_info[title][1]
            delete_post(postid)

            if cur < total:
                time.sleep(65)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: ./sync.py <token> <local_directory_or_single_file>\n")
        return

    config['token'] = sys.argv[1]
    local_path = sys.argv[2]
    local_files = []
    if os.path.isdir(local_path):
        local_files = get_local_files(local_path, config['file_extension'])
        sync_posts(local_files, True)
    else:
        local_files = [local_path]
        sync_posts(local_files, False)

    return


if __name__ == '__main__':
    main()
