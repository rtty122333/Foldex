#encoding=utf-8
import MySQLdb
from MySQLdb.cursors import DictCursor
from oslo_config import cfg


opt_db_group = cfg.OptGroup(name='mysql',
                            title='Server Mysql Configuration')

db_opts = [
    cfg.StrOpt('host', default='127.0.0.1',
                help=('Host IP for Mysql')),
    cfg.IntOpt('port', default=3306,
                help=('Host Port for Mysql')),
    cfg.StrOpt('user', default='root',
                help=('User to access Mysql')),
    cfg.StrOpt('password', default='root',
                help=('Password to access Mysql')),
    cfg.StrOpt('db', default='foldexserver',
                help=('Database name used for foldex')),
    cfg.StrOpt('charset', default='utf8',
                help=('db charset')),
    cfg.IntOpt('mincached', default='5',
                help=('mincached')),
    cfg.IntOpt('maxcached', default='25',
                help=('maxcached')),
] 

CONF = cfg.CONF
CONF.register_group(opt_db_group)
CONF.register_opts(db_opts, opt_db_group)

class Mysql(object):
    def __init__(self):
       self._conn = MySQLdb.connect(host=CONF.mysql.host,
                                    port=CONF.mysql.port,
                                    user=CONF.mysql.user,
                                    passwd=CONF.mysql.password,
                                    db=CONF.mysql.db,
                                    use_unicode=False,
                                    charset=CONF.mysql.charset,
                                    cursorclass=DictCursor)
       self._conn.autocommit(True)
       self._cursor=self._conn.cursor()
 
    def getAllRows(self,sql,param=None):
        """
        @summary: 执行查询，并取出所有结果集
        @param sql:查询SQL，如果有查询条件，请只指定条件列表，并将条件值使用参数[param]传递进来
        @param param: 可选参数，条件列表值（元组/列表）
        @return: result list/boolean 查询到的结果集
        """
        if param is None:
            count = self._cursor.execute(sql)
        else:
            count = self._cursor.execute(sql,param)
        if count>0:
            result = self._cursor.fetchall()
        else:
            result = None
        return result
 
    def getOneRow(self,sql,param=None):
        """
        @summary: 执行查询，并取出第一条
        @param sql:查询SQL，如果有查询条件，请只指定条件列表，并将条件值使用参数[param]传递进来
        @param param: 可选参数，条件列表值（元组/列表）
        @return: result list/boolean 查询到的结果集
        """
        if param is None:
            count = self._cursor.execute(sql)
        else:
            count = self._cursor.execute(sql,param)
        if count>0:
            result = self._cursor.fetchone()
        else:
            result = None
        return result
 
    def getSomeRows(self,sql,num,param=None):
        """
        @summary: 执行查询，并取出num条结果
        @param sql:查询SQL，如果有查询条件，请只指定条件列表，并将条件值使用参数[param]传递进来
        @param num:取得的结果条数
        @param param: 可选参数，条件列表值（元组/列表）
        @return: result list/boolean 查询到的结果集
        """
        if param is None:
            count = self._cursor.execute(sql)
        else:
            count = self._cursor.execute(sql,param)
        if count>0:
            result = self._cursor.fetchmany(num)
        else:
            result = None
        return result
 
    def insertOneRow(self,sql,value):
        """
        @summary: 向数据表插入一条记录
        @param sql:要插入的SQL格式
        @param value:要插入的记录数据tuple/list
        @return: insertId 受影响的行数
        """
        result=self._cursor.execute(sql,value)
        return self.__getInsertId()
 
    def insertSomeRows(self,sql,values):
        """
        @summary: 向数据表插入多条记录
        @param sql:要插入的SQL格式
        @param values:要插入的记录数据tuple(tuple)/list[list]
        @return: count 受影响的行数
        """
        count = self._cursor.executemany(sql,values)
        return count
 
    def __getInsertId(self):
        """
        获取当前连接最后一次插入操作生成的id,如果没有则为０
        """
        self._cursor.execute("SELECT @@IDENTITY AS id")
        result = self._cursor.fetchall()
        return result[0]['id']
 
    def __query(self,sql,param=None):
        if param is None:
            count = self._cursor.execute(sql)
        else:
            count = self._cursor.execute(sql,param)
        return count
 
    def update(self,sql,param=None):
        """
        @summary: 更新数据表记录
        @param sql: SQL格式及条件，使用(%s,%s)
        @param param: 要更新的  值 tuple/list
        @return: count 受影响的行数
        """
        return self.__query(sql,param)
 
    def delete(self,sql,param=None):
        """
        @summary: 删除数据表记录
        @param sql: SQL格式及条件，使用(%s,%s)
        @param param: 要删除的条件 值 tuple/list
        @return: count 受影响的行数
        """
        return self.__query(sql,param)
 
    def begin(self):
        """
        @summary: 开启事务
        """
        self._conn.autocommit=True
 
    def end(self,option='commit'):
        """
        @summary: 结束事务
        """
        if option=='commit':
            self._conn.commit()
        else:
            self._conn.rollback()
 
    def dispose(self,isEnd=1):
        """
        @summary: 释放连接池资源
        """
        if isEnd==1:
            self.end('commit')
        else:
            self.end('rollback');
        self._cursor.close()
        self._conn.close()
