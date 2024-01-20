## 功能
对本地md5和博客园markdown源文件的md5值，比较后检验本地文件是否发生变更，把变更的markdown文件批量同步到博客园。

## 用法
博客园/设置/博客设置(https://i.cnblogs.com/settings), 翻到最下面可以查到username和token  
`Usage: ./sync.py <token> <local_directory_or_single_file>`

## 参考
[博客园自动化之MetaWeblog - 知乎](https://zhuanlan.zhihu.com/p/412880353)  
[DeppWang/cnblogs-post: 一个发布文章到博客园的 Python 脚本](https://github.com/DeppWang/cnblogs-post)  
上面的帖子里说，`getRecentPosts`接口最多只能获取最近100个帖子。

```bash
# 查看git两个commit之间修改了哪些文件
git diff <hash1> <hash2> --stat
```
