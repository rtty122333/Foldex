## 环境配置

- 安装 `funcsigs` 库和 `pip` 工具

        sudo dnf install -y python2-funcsigs python-pip

- 安装 `openstacksdk` 库（依赖 `funcsigs`）

        sudo pip install openstacksdk

- 安装 `mysql` 模块

    在 `http://www.codegood.com/downloads` 下载对应版本编译版本并安装

- 建立数据库

    在 `mysql` 命令行模式下执行 `source server.sql`（注意正确路径）加入数据信息

### TODO:

- 用部署工具自动配置环境

- 自动配置数据库

## 程序配置

- 将 `etc/foldex.conf` 中的参数修改为合适值，复制到 `/etc/foldex/`下
