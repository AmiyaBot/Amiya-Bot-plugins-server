from typing import Union
from amiyabot.util import argv
from amiyabot.database import *

MYSQL_HOST = argv('mysql-host') or '127.0.0.1'
MYSQL_PORT = argv('mysql-port', int) or 3306
MYSQL_USER = argv('mysql-user') or 'root'
MYSQL_PWD = argv('mysql-password')


class BaseModelClass(ModelClass):
    class Meta:
        database = connect_database('custom_plugins', True, MysqlConfig(MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PWD))


@table
class Plugin(BaseModelClass):
    plugin_id: str = CharField(null=True)
    author: str = CharField(null=True)
    secret_key: str = CharField(null=True)
    download_num: int = IntegerField(default=0)

    @classmethod
    def get_secret_key(cls, plugin_id: str, secret_key: str):
        md5 = hashlib.md5((plugin_id + secret_key).encode())
        return md5.hexdigest()

    @classmethod
    def check_secret_key(cls, plugin_id: str, secret_key: str):
        res: Plugin = cls.get_or_none(plugin_id=plugin_id)
        if res:
            return res.secret_key == cls.get_secret_key(plugin_id, secret_key)
        return True


@table
class PluginRelease(BaseModelClass):
    file: str = CharField(unique=True)
    name: str = CharField()
    version: str = CharField()
    plugin_id: str = CharField(null=True)
    plugin_type: str = CharField(null=True)
    description: str = CharField(null=True)
    document: str = TextField(null=True)
    logo: str = TextField(null=True)
    remark: str = CharField(null=True)
    upload_time: str = CharField(null=True)
    on_shelf: int = SmallIntegerField(default=1, null=True)
    plugin_info: Union[ForeignKeyField, Plugin] = ForeignKeyField(Plugin, db_column='plugin_info', on_delete='CASCADE')
