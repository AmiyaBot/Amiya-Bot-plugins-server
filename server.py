import logging

from amiyabot.network.httpServer import HttpServer, BaseModel
from amiyabot.util import argv

from build.uploadFile import COSUploader

HOST = argv('host') or '0.0.0.0'
PORT = argv('port', int) or 8020
SSL_KEY = argv('ssl-keyfile')
SSL_CERT = argv('ssl-certfile')
SECRET_ID = argv('secret-id')
SECRET_KEY = argv('secret-key')

server = HttpServer(HOST, PORT, title='AmiyaBot-PluginsServer', uvicorn_options={
    'ssl_keyfile': SSL_KEY,
    'ssl_certfile': SSL_CERT
})
uploader = COSUploader(SECRET_ID, SECRET_KEY, logger_level=logging.FATAL)


class CommitModel(BaseModel):
    file: str
    name: str
    version: str
    plugin_id: str
    plugin_type: str
    description: str
    document: str
    logo: str
    remark: str = None
    author: str = None
    secret_key: str


class DeleteModel(CommitModel):
    force_delete: bool
