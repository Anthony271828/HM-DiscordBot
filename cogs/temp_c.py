# noinspection PyUnresolvedReferences
import discord
# noinspection PyUnresolvedReferences
from discord.ext import commands
import re
# noinspection PyUnresolvedReferences
from settings import Embedgenerator, BugReport
# noinspection PyUnresolvedReferences
from settings_files.all_errors import *
from utils import *


# noinspection PyUnusedLocal,PyUnresolvedReferences,PyDunderSlots,PyBroadException
class TempChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def tmpc(self, ctx):
        if ctx.invoked_subcommand is None:
            raise ModuleError()

    @tmpc.command()
    @commands.has_role(ServerIds.HM)
    async def mk(self, ctx, *, arg):
        await accepted_channels(self.bot, ctx)
        member = await ctx.guild.fetch_member(ctx.author.id)
        if member.id in TMP_CHANNELS.tmp_channels:
            raise PrivateChannelsAlreadyExistsError()

        voice_c = await ctx.guild.create_voice_channel(arg,
                                                       category=TMP_CHANNELS,
                                                       reason=f"request by {str(ctx.author)}")

        text_c = await ctx.guild.create_text_channel(arg,
                                                     category=TMP_CHANNELS,
                                                     reason=f"request by {str(ctx.author)}",
                                                     topic=f"Erstellt von: {str(ctx.author)}")
        token = mk_token()

        overwrite = discord.PermissionOverwrite()
        overwrite.mute_members = True
        overwrite.deafen_members = True
        overwrite.move_members = True
        overwrite.connect = True
        overwrite.read_messages = True

        await voice_c.set_permissions(member, overwrite=overwrite, reason="owner")
        await text_c.set_permissions(member, overwrite=overwrite, reason="owner")

        try:
            await member.move_to(voice_c, reason="created this channel.")
        except Exception:
            pass

        try:
            gen = Embedgenerator("tmpc-func")
            embed = gen.generate()
            embed.add_field(name="Kommilitonen einladen",
                            value=f"Mit ```!tmpc join {token}``` "
                                  f"können deine Kommilitonen ebenfalls dem (Voice-)Chat beitreten.",
                            inline=False)

            await text_c.send(content=f"<@!{ctx.author.id}>",
                              embed=embed)
        except Exception:
            pass

        TMP_CHANNELS.update(member, text_c, voice_c, token)

    @tmpc.command()
    async def join(self, ctx, arg):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        await accepted_channels(self.bot, ctx)
        my_guild = await self.bot.fetch_guild(ServerIds.GUILD_ID)
        member = await my_guild.fetch_member(ctx.author.id)

        if arg in TMP_CHANNELS.token:
            text_c, voice_c = TMP_CHANNELS.token[arg]

            await TMP_CHANNELS.join(ctx.author, voice_c, text_c)

        else:
            raise TempChannelNotFound()

    @tmpc.command()
    async def token(self, ctx, command: str, *, args=None):
        text, voice, token, invites = await TMP_CHANNELS.get_ids(ctx.author)

        if command.startswith("gen"):
            token = mk_token()
            embed = invite_embed(ctx.author, "Abgelaufen")

            loop = invites.copy()  # Avoid RuntimeError: dictionary changed size during iteration
            for x in loop:
                await TMP_CHANNELS.delete_invite(ctx.author.id, invites[x].channel, x, ctx)

        TMP_CHANNELS.update(ctx.author, text, voice, token)

        if command.startswith("place"):
            embed = invite_embed(ctx.author, f"```!tmpc join {token}```")
            message = await ctx.send(embed=embed)
            await TMP_CHANNELS.save_invite(ctx.author, message)
            await message.add_reaction(emoji="🔓")

        if command.startswith("send") and args:
            await accepted_channels(self.bot, ctx)
            embed = invite_embed(ctx.author, f"```!tmpc join {token}```")

            matches = re.finditer(r"[0-9]+", args)
            for match in matches:
                start, end = match.span()
                user_id = args[start:end]
                user = await discord.Client.fetch_user(self.bot, user_id)
                send_error = False
                error_user = set()

                try:
                    message = await user.send(embed=embed)
                    await TMP_CHANNELS.save_invite(ctx.author, message)
                    await message.add_reaction(emoji="🔓")
                except Exception:
                    error_user.add(str(user))
                    send_error = True

                if send_error:
                    raise CouldNotSendMessage(f"Einladung konnte nicht an: {error_user} gesendet werden."
                                              f"M\u00f6glicherweise liegt dies an den Einstellungen der User")

    @tmpc.command()
    @commands.has_role(ServerRoles.MODERATOR_ROLE_NAME)
    async def nomod(self, ctx):
        await accepted_channels(self.bot, ctx)
        text_c, voice_c, *_ = TMP_CHANNELS.tmp_channels[ctx.author.id]
        if ctx.author.id in TMP_CHANNELS.tmp_channels:
            overwrite = discord.PermissionOverwrite()
            mod = role = discord.utils.get(ctx.guild.roles, name=ServerRoles.MODERATOR_ROLE_NAME)
            await voice_c.set_permissions(mod,
                                          overwrite=None,
                                          reason="access by token")

            await text_c.set_permissions(mod,
                                         overwrite=None,
                                         reason="access by token")
            pass
        else:
            raise TempChannelNotFound()

    @tmpc.command()
    @commands.has_role(ServerIds.HM)
    async def rem(self, ctx):
        if ctx.author.id in TMP_CHANNELS.tmp_channels:
            await accepted_channels(self.bot, ctx)
            member = ctx.author.id
            text_c, voice_c, token, *_ = TMP_CHANNELS.tmp_channels[member]
            await TMP_CHANNELS.rem_channel(member, text_c, voice_c, token, ctx)
        else:
            raise TempChannelNotFound()

    @tmpc.error
    @mk.error
    @join.error
    @token.error
    @nomod.error
    @rem.error
    async def temp_errorhandler(self, ctx, error):
        if isinstance(error, TempChannels):
            await ctx.send(f"<@!{ctx.author.id}>\n"
                           f"Es wurde kein Channel gefunden, der dir geh\u00f6rt.")

        elif isinstance(error, CouldNotSendMessage):
            await ctx.send(error)

        elif isinstance(error, PrivateChannelsAlreadyExistsError):
            await ctx.send(f"<@!{ctx.author.id}>\n"
                           f"Du hast bereits einen Privaten Channel erstellt.\n"
                           f"Mit `!tmpc rem` kannst du diesen L\u00f6schen.")

        elif isinstance(error, ModuleError):
            embed = Embedgenerator("tmpc")
            await ctx.send(content=f"<@!{ctx.author.id}>\n"
                                   f"Dieser Befehl wurde nicht gefunden.",
                           embed=embed.generate())
            embed = Embedgenerator("tmpc-func")
            await ctx.send(embed=embed.generate())

        elif isinstance(error, WrongChatError):
            await ctx.message.delete()
            await ctx.send(f"<@!{ctx.author.id}>\n"
                           f"Dieser Befehl darf in diesem Chat nicht verwendet werden.\n"
                           f"Nutzebitte den dafür vorgesehenen Chat <#{ServerIds.BOT_COMMANDS_CHANNEL}>.",
                           delete_after=60)

        else:
            error = BugReport(self.bot, ctx, error)
            error.user_details()
            await error.reply()
            raise error


def setup(bot):
    bot.add_cog(TempChannels(bot))
