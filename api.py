import os
import time
import shutil

from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse
from amiyabot import AmiyaBot
from amiyabot.util import random_code

from .server import *
from .database import *

logo_save = 'uploads/logos'

create_dir(logo_save)


@server.app.post('/uploadPlugin')
async def upload(file: UploadFile = File(...)):
    code = f'{int(time.time())}{random_code(10)}'
    dest = f'uploads/dest/{code}'
    path = f'uploads/plugins/{file.filename}'

    create_dir(dest)
    create_dir(path, is_file=True)

    data = {}
    try:
        with open(path, mode='wb') as f:
            c = await file.read()
            f.write(c)

        plugin = AmiyaBot.load_plugin(path, extract_plugin=True, extract_plugin_dest=dest)

        doc = plugin.document
        if doc and os.path.isfile(doc):
            with open(doc, mode='r', encoding='utf-8') as doc_file:
                document = doc_file.read()
        else:
            document = doc

        logo = ''
        if plugin.path:
            logo_path = os.path.join(dest, 'logo.png')
            if os.path.exists(logo_path):
                logo = logo_save + f'/{code}.png'
                shutil.copy(logo_path, logo)

        data = {
            'file': file.filename,
            'name': plugin.name,
            'version': plugin.version,
            'plugin_id': plugin.plugin_id,
            'plugin_type': plugin.plugin_type,
            'description': plugin.description,
            'document': document,
            'logo': logo,
            'success': [],
            'warning': [],
            'error': [],
            'ready': True
        }

        exists: Plugin = Plugin.get_or_none(plugin_id=plugin.plugin_id)
        if exists:
            data['warning'].append(f'插件ID【{plugin.plugin_id}】已存在，你需要验证插件ID【{plugin.plugin_id}】的密钥')

            item: PluginRelease = PluginRelease.get_or_none(plugin_id=exists.plugin_id, on_shelf=1)
            if item:
                if item.version != plugin.version:
                    data['warning'].append(f'版本变更：{plugin.version} >> {item.version}')
                if item.name != plugin.name:
                    data['warning'].append('插件名称更新')
                if item.description != plugin.description:
                    data['warning'].append('插件描述更新')
                if not document:
                    data['warning'].append('未添加插件文档')
                if not logo:
                    data['warning'].append('未添加 LOGO（在根目录放置 logo.png）')
        else:
            data['success'].append(f'插件ID【{plugin.plugin_id}】未注册，将自动注册此ID')

        if plugin.plugin_type == 'official':
            data['error'].append('不允许上传标签为【官方】的插件，请修改 plugin_type 属性，可更改为空')
            data['ready'] = False
    finally:
        shutil.rmtree(dest)

    return data


@server.app.post('/commitPlugin')
async def commit_plugin(data: CommitModel):
    if not data.secret_key:
        return server.response(message='密钥不能为空', code=500)

    if not Plugin.check_secret_key(data.plugin_id, data.secret_key):
        return server.response(message='密钥不匹配', code=500)

    uni_file = f'{data.plugin_id}-{data.version}.zip'

    path = os.path.abspath(f'uploads/plugins/{data.file}')
    uploader.upload_file(path, f'plugins/custom/{data.plugin_id}/{uni_file}')

    info_id: Plugin = Plugin.get_or_none(plugin_id=data.plugin_id)
    if not info_id:
        info_id = Plugin.create(**{
            'plugin_id': data.plugin_id,
            'author': data.author,
            'secret_key': Plugin.get_secret_key(data.plugin_id, data.secret_key)
        })
    else:
        Plugin.update(author=data.author).where(Plugin.plugin_id == data.plugin_id).execute()

    # 下架所有在架插件
    PluginRelease.update(on_shelf=0).where(PluginRelease.plugin_id == data.plugin_id).execute()
    # 删除同版本插件
    PluginRelease.delete().where(PluginRelease.plugin_id == data.plugin_id,
                                 PluginRelease.version == data.version).execute()
    # 上架该版本的插件
    PluginRelease.create(**{
        'file': uni_file,
        'name': data.name,
        'version': data.version,
        'plugin_id': data.plugin_id,
        'plugin_type': data.plugin_type,
        'description': data.description,
        'document': data.document,
        'logo': data.logo,
        'remark': data.remark,
        'upload_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
        'on_shelf': 1,
        'plugin_info': info_id
    })

    return server.response(message='提交成功')


@server.app.post('/deletePlugin')
async def delete_plugin(data: DeleteModel):
    if not data.secret_key:
        return server.response(message='密钥不能为空', code=500)

    if not Plugin.check_secret_key(data.plugin_id, data.secret_key):
        return server.response(message='密钥不匹配', code=500)

    if data.force_delete:
        # 永久下架，清空数据库，删除 COS 文件夹
        Plugin.delete().where(Plugin.plugin_id == data.plugin_id).execute()
        PluginRelease.delete().where(PluginRelease.plugin_id == data.plugin_id).execute()
        uploader.delete_folder(f'plugins/custom/{data.plugin_id}')
    else:
        # 暂时下架，修改在架状态，删除 COS 文件
        PluginRelease.update(on_shelf=0).where(PluginRelease.plugin_id == data.plugin_id).execute()
        uploader.delete_file(f'plugins/custom/{data.plugin_id}/{data.plugin_id}-{data.version}.zip')

        # todo 上架历史版本

    return server.response(message='下架成功')


@server.app.post('/getPlugins')
async def get_plugins():
    return server.response(
        data=query_to_list(PluginRelease.select().where(PluginRelease.on_shelf == 1))
    )


@server.app.get('/image', response_class=StreamingResponse)
async def get_image(path: str):
    return StreamingResponse(open(path, mode='rb'), media_type='image/png')
