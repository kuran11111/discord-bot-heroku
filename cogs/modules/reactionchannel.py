import pickle
import discord
from discord.message import Attachment
from discord.utils import get
import os
from os.path import join, dirname
import base64
import json
from . import settings

class ReactionChannel:
    FILE = 'reaction-channel.json'
    REACTION_CHANNEL = 'reaction_channel_control'

    def __init__(self, guilds, bot):
        self.guilds = guilds
        self.bot = bot
        self.reaction_channels = []
        self.guild_reaction_channels = []
        self.guild_rc_txt_lists = []
        self.rc_len = 0
        self.rc_err = ''

    # Heroku対応
    async def get_discord_attachment_file(self, guild:discord.Guild):
        # Herokuの時のみ実施
        if settings.IS_HEROKU:
            if settings.IS_DEBUG:
                print('Heroku mode.start get_discord_attachment_file.')
            # # ファイルをチェックし、存在しなければ最初と見做す
            if not os.path.exists('first_time'):
                with open('first_time','w') as f:
                    print('存在しない')
                    Attachment_file_date = None

                    # BotがログインしているGuildごとに繰り返す
                    for guild in self.guilds:
                        # チャンネルのチェック
                        get_control_channel = discord.utils.get(guild.text_channels, name=self.REACTION_CHANNEL)
                        if get_control_channel is not None:
                            last_message = await get_control_channel.history(limit=1).flatten()
                            # last_messageがない場合以外で、reaction-channel.jsonが本文である場合、ファイルを取得する
                            if len(last_message) == 0:
                                return
                            elif last_message[0].content == self.FILE:
                                if len(last_message[0].attachments) > 0:

                                    # 日付が新しい場合、ファイルを取得
                                    if Attachment_file_date is None or Attachment_file_date < last_message[0].created_at:
                                        Attachment_file_date = last_message[0].created_at
                                        file_path = join(dirname(__file__), 'files' + os.sep + self.FILE)
                                        await last_message[0].attachments[0].save(file_path)
                                        print(f'channel_file_save:{guild.name}')
        if settings.IS_DEBUG:
            print('get_discord_attachment_file is over!')

    async def set_discord_attachment_file(self, guild:discord.Guild):
        # Herokuの時のみ実施
        if settings.IS_HEROKU:
            if settings.IS_DEBUG:
                print('Heroku mode.start set_discord_attachment_file.')

            # チャンネルをチェック(チャンネルが存在しない場合は勝手に作成する)
            get_control_channel = discord.utils.get(guild.text_channels, name=self.REACTION_CHANNEL)
            if get_control_channel is None:
                permissions = []
                target = []
                permissions.append(discord.PermissionOverwrite(read_messages=False,read_message_history=False))
                target.append(guild.default_role)
                permissions.append(discord.PermissionOverwrite(read_messages=True,read_message_history=True))
                target.append(guild.owner)
                permissions.append(discord.PermissionOverwrite(read_messages=True,read_message_history=True))
                target.append(self.bot.user)
                overwrites = dict(zip(target, permissions))

                try:
                    print((f'＊＊＊{self.REACTION_CHANNEL}を作成しました！＊＊＊'))
                    get_control_channel = await guild.create_text_channel(name=self.REACTION_CHANNEL, overwrites=overwrites)
                except discord.errors.Forbidden:
                    print((f'＊＊＊{self.REACTION_CHANNEL}の作成に失敗しました！＊＊＊'))

            # チャンネルの最後のメッセージを確認し、所定のメッセージなら削除する
            last_message = await get_control_channel.history(limit=1).flatten()
            if len(last_message) != 0:
                if last_message[0].content == self.FILE:
                    await get_control_channel.purge(limit=1)

            # チャンネルにファイルを添付する
            file_path = join(dirname(__file__), 'files' + os.sep + self.FILE)
            await get_control_channel.send(self.FILE, file=discord.File(file_path))
            print((f'＊＊＊{get_control_channel.name}へファイルを添付しました！＊＊＊'))

        if settings.IS_DEBUG:
            print('set_discord_attachment_file is over!')

    # 初期設定
    async def set_rc(self, guild:discord.Guild):
        # 既に読み込まれている場合は、読み込みしない
        if self.rc_len != 0:
            print('__読み込み不要__')
            return

        # 読み込み
        try:
            # Herokuの時のみ、チャンネルからファイルを取得する
            await self.get_discord_attachment_file(guild)

            print(f'＊＊読み込み＊＊')
            file_path = join(dirname(__file__), 'files' + os.sep + self.FILE)
            dict = {}
            with open(file_path, mode='r') as f:
                dict = json.load(f)
                serialize = dict["pickle"]
                self.reaction_channels = pickle.loads(base64.b64decode(serialize.encode()))
            self.guild_reaction_channels = [rc[1:] for rc in self.reaction_channels if str(guild.id) in map(str, rc)]
            # joinするので文字列に変換し、リストに追加する
            for rc in self.guild_reaction_channels:
                self.guild_rc_txt_lists.append('+'.join(map(str, rc)))
            self.rc_len = len(self.guild_reaction_channels)
        except FileNotFoundError:
            # 読み込みに失敗したらなにもしない
            print
        except json.JSONDecodeError:
            # JSON変換失敗したらなにもしない
            print
        except EOFError:
            # 読み込みに失敗したらなにもしない
            print

    # リアクションチャンネルを保管する
    async def save(self, guild:discord.Guild):
        print('＊＊書き込み＊＊')
        file_path = join(dirname(__file__), 'files' + os.sep + self.FILE)
        serialized = base64.b64encode(pickle.dumps(self.reaction_channels)).decode("utf-8")
        dict = {"pickle": serialized}
        # 書き込み
        try:
            with open(file_path, mode='w') as f:
                json.dump(dict, f)
            # Herokuの時のみ、チャンネルにファイルを添付する
            await self.set_discord_attachment_file(guild)
        except pickle.PickleError:
            # 書き込みに失敗したらなにもしない
            self.rc_err = '保管に失敗しました。'

    # 追加するリアクションチャネルが問題ないかチェック
    def check(self, ctx, reaction:str, channel:str):
        reaction_id = None
        if reaction.count(':') == 2:
            reaction_id = reaction.split(':')[1]
        guild = ctx.guild
        additem = f'{reaction}+{channel}'
        print(f'＊＊追加のチェック＊＊, reaction: {reaction}, channel: {channel}')
        # 絵文字が不正な場合(guildに登録された絵文字なら'yes'のような文字が入っているし、そうでない場合は1文字のはず -> 🐈‍⬛,がありえるので緩和)
        emoji = discord.utils.get(guild.emojis, name=reaction_id)
        if emoji is None and len(reaction) > 4:
            self.rc_err = f'絵文字が不正なので登録できません。(reaction: {reaction})'
            return False

        # ok_handは確認に使っているのでダメ
        if reaction == '👌':
            self.rc_err = f'この絵文字を本Botで使用しているため、登録できません。(reaction: {reaction})'
            return False

        # チャンネルが不正な場合
        get_channel = discord.utils.get(guild.text_channels, name=channel)
        if get_channel is None:
            self.rc_err = 'チャンネルが不正なので登録できません。'
            return False

        # リアクションチャンネルが未登録ならチェックOK
        if self.rc_len == 0:
            return True

        # すでに登録されている場合
        dup_checked_list = list(filter(lambda x: additem in x, self.guild_rc_txt_lists))
        if len(dup_checked_list) > 0:
            self.rc_err = 'すでに登録されています。'
            return False

        return True

    # リアクションチャンネルを追加
    async def add(self, ctx, reaction:str, channel:str):
        print(f'＊＊追加＊＊, reaction: {reaction}, channel: {channel}')
        guild = ctx.guild
        await self.set_rc(guild)

        # チャンネルがID指定の場合はギルドからチャンネル名を取得
        if channel.count('#') == 1:
            channel_id = channel.split('#')[1].split('>')[0]
            print(f'check channel:{channel_id}')
            channel_info = None
            if channel_id.isdecimal():
                channel_info = guild.get_channel(int(channel_id))
            if channel_info is not None:
                channel = channel_info.name

        if self.check(ctx, reaction, channel) is False:
            return self.rc_err
        get_channel = discord.utils.get(guild.text_channels, name=channel)

        addItem = []
        addItem.append(guild.id)
        addItem.append(reaction)
        addItem.append(get_channel.name)
        addItem.append(get_channel.id)

        # 追加
        self.reaction_channels.append(addItem)
        self.guild_reaction_channels.append(addItem[1:])
        self.guild_rc_txt_lists.append('+'.join(map(str, addItem[1:])))
        self.rc_len = len(self.guild_reaction_channels)

        # 保管
        if await self.save(guild) is False:
            return self.rc_err

        return f'リアクションチャンネルの登録に成功しました！\n{reaction} → <#{get_channel.id}>'

    async def list(self, ctx):
        guild = ctx.guild
        await self.set_rc(guild)
        print(f'＊＊リスト＊＊, {self.guild_reaction_channels}')
        text = ''
        for list in self.guild_reaction_channels:
            text = f'{text}  リアクション：{list[0]} → <#{list[2]}>\n'

        if text == '':
            return f'＊現在登録されているリアクションチャンネルはありません！'
        else:
            return f'＊現在登録されているリアクションチャンネルの一覧です！({self.rc_len}種類)\n{text}'

    # 全削除
    async def purge(self, ctx):
        print('＊＊リアクションチャンネラーを全部削除＊＊')
        guild = ctx.guild
        await self.set_rc(guild)
        if settings.IS_DEBUG:
            for test in map(str, self.reaction_channels):
                print(test)
            print('this guild is '+str(guild.id))
        self.reaction_channels = [rc for rc in self.reaction_channels if str(guild.id) not in map(str, rc)]
        self.guild_reaction_channels = []
        self.guild_rc_txt_lists = []
        self.rc_len = 0
        if settings.IS_DEBUG:
            print('**********************************')
            for test in map(str, self.reaction_channels):
                print(test)
        # 保管
        if await self.save(guild) is False:
            return self.rc_err

        return '全てのリアクションチャンネラーの削除に成功しました！'

    # 削除
    async def delete(self, ctx, reaction:str, channel:str):
        print(f'＊＊削除＊＊, reaction: {reaction}, channel: {channel}')
        guild = ctx.guild
        await self.set_rc(guild)

        # チャンネルがID指定の場合はギルドからチャンネル名を取得
        if channel.count('#') == 1:
            channel_id = channel.split('#')[1].split('>')[0]
            print(f'check channel:{channel_id}')
            channel_info = None
            if channel_id.isdecimal():
                channel_info = guild.get_channel(int(channel_id))
            if channel_info is not None:
                channel = channel_info.name

        get_channel = discord.utils.get(guild.text_channels, name=channel)
        deleteItem = []
        deleteItem.append(guild.id)
        deleteItem.append(reaction)
        deleteItem.append(get_channel.name)
        deleteItem.append(get_channel.id)

        # 削除
        self.reaction_channels = [s for s in self.reaction_channels if s != deleteItem]
        self.guild_reaction_channels = [s for s in self.guild_reaction_channels if s != deleteItem[1:]]
        self.guild_rc_txt_lists = [s for s in self.guild_rc_txt_lists if s != '+'.join(map(str, deleteItem[1:]))]
        self.rc_len = len(self.guild_reaction_channels)

        # 保管
        if await self.save(guild) is False:
            return self.rc_err

        return f'リアクションチャンネラーの削除に成功しました！\n{reaction} → <#{get_channel.id}>'