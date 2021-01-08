from collections import namedtuple

from .enums import InteractionResponseType, try_enum, InteractionType, ApplicationCommandOptionType
from .member import Member
from .message import Message
from .errors import InvalidArgument

ApplicationCommandOptionChoice = namedtuple('ApplicationCommandOptionChoice', 'name value')

class ApplicationCommandInteractionDataOption:
    def __init__(self, *, name, value=None, options=None):
        self.name = name
        self.value = value
        self.options = [self.__class__(**option) for option in (options or [])]

    def to_dict(self):
        return {'name': self.name, 'value': self.value, 'options': [option.to_dict() for option in self.options]}

class ApplicationCommand:
    def __init__(self, *, state, data, guild=None):
        print(data)
        self._state = state
        self.guild = guild
        self.id = int(data['id'])
        self.application_id = int(data['application_id'])
        self.name = data['name']
        self.description = data['description']

        self.options = [ApplicationCommandOption(**option) for option in data.get('options', [])]

    async def delete(self):
        if not self.guild:
            await self._state.http.delete_application_command(self.application_id, self.id)
        else:
            await self._state.http.delete_guild_application_command(self.application_id, self.id, self.guild.id)

    async def edit(self, **kwargs):
        kwargs.setdefault("name", self.name)
        kwargs.setdefault("description", self.description)
        kwargs.setdefault("options", self.options)

        kwargs["options"] = [option.to_dict() for option in kwargs["options"]]

        if not self.guild:
            new_data = await self._state.http.edit_application_command(self.application_id, self.id, kwargs)
        else:
            new_data = await self._state.http.edit_guild_application_command(self.application_id, self.id, self.guild.id, kwargs)

        self.__init__(state=self._state, data=new_data, guild=self.guild)

class ApplicationCommandOption:
    def __init__(self, *, name, description, type, default=False, required=False, choices=None, options=None):
        self.name = name
        self.description = description
        self.type = try_enum(ApplicationCommandOptionType, type)
        self.default = default
        self.required = required
        self.choices = [ApplicationCommandOptionChoice(**choice) for choice in (choices or [])]
        self.options = [self.__class__(**option) for option in (options or [])]

    def add_option(self, *, name, description, type, default=None, required=None, choices=None):
        option = {'name': name, 'description': description, 'type': type}
        if default is not None:
            option['default'] = default
        if required is not None:
            option['required'] = required
        if choices is None:
            choices = []

        option['choices'] = [ApplicationCommandOptionChoice(**choice) for choice in choices]
        option = self.__class__(**option)
        self.options.append(option)
        return option

    def to_dict(self):
        data = {'name': self.name, 'description': self.description, 'default': self.default, 'required': self.required}
        data['type'] = self.type.value
        data['options'] = [option.to_dict() for option in self.options]
        data['choices'] = [choice._asdict() for choice in self.choices]
        return data

class Interaction:
    def __init__(self, *, state, data):
        self._state = state
        self.id = int(data['id'])
        self.type = try_enum(InteractionType, data['type'])
        self.channel, self.guild = state._get_guild_channel(data)
        self.author = Member(data=data['member'], guild=self.guild, state=state)
        self.token = data['token']
        self.options = [ApplicationCommandInteractionDataOption(**option) for option in data['data'].get('options', [])]
        self.name = data['data']['name']
        self.command_id = int(data['data']['id'])
        self.version = data['version']

    async def send(self, content=None, *, type=None, tts=False, embed=None, embeds=None, allowed_mentions=None, flags=0):
        payload = {}
        if embeds is not None and embed is not None:
            raise InvalidArgument('Cannot mix embed and embeds keyword arguments.')

        if embeds is not None:
            if len(embeds) > 10:
                raise InvalidArgument('embeds has a maximum of 10 elements.')
            payload['embeds'] = [e.to_dict() for e in embeds]

        if embed is not None:
            payload['embeds'] = [embed.to_dict()]

        if content is not None:
            payload['content'] = str(content)

        payload['tts'] = tts

        previous_mentions = getattr(self._state, 'allowed_mentions', None)

        if allowed_mentions:
            if previous_mentions is not None:
                payload['allowed_mentions'] = previous_mentions.merge(allowed_mentions).to_dict()
            else:
                payload['allowed_mentions'] = allowed_mentions.to_dict()
        elif previous_mentions is not None:
            payload['allowed_mentions'] = previous_mentions.to_dict()

        if flags:
            payload['flags'] = flags

        await self._state.http.interaction_callback(self.id, self.token, {'data': payload, 'type': type.value})

    async def acknowledge(self, type=None):
        if type is None:
            await self._state.http.interaction_callback(self.id, self.token, {'type': 5})
        await self._state.http.interaction_callback(self.id, self.token, {'type': type.value})

    async def edit_original(self, **fields):
        try:
            content = fields['content']
        except KeyError:
            pass
        else:
            if content is not None:
                fields['content'] = str(content)

        try:
            embed = fields['embed']
        except KeyError:
            pass
        else:
            if embed is not None:
                fields['embed'] = embed.to_dict()

        try:
            allowed_mentions = fields.pop('allowed_mentions')
        except KeyError:
            pass
        else:
            if allowed_mentions is not None:
                if self._state.allowed_mentions is not None:
                    allowed_mentions = self._state.allowed_mentions.merge(allowed_mentions).to_dict()
                else:
                    allowed_mentions = allowed_mentions.to_dict()
                fields['allowed_mentions'] = allowed_mentions

        if fields:
            await self._state.http.edit_interaction_message(self.id, self.token, fields)

    async def delete_original(self):
        await self._state.http.delete_interaction_callback(self.id, self.token)

    async def send_followup(self, content=None, *, tts=False, embed=None, embeds=None, allowed_mentions=None):
        payload = {}
        if embeds is not None and embed is not None:
            raise InvalidArgument('Cannot mix embed and embeds keyword arguments.')

        if embeds is not None:
            if len(embeds) > 10:
                raise InvalidArgument('embeds has a maximum of 10 elements.')
            payload['embeds'] = [e.to_dict() for e in embeds]

        if embed is not None:
            payload['embeds'] = [embed.to_dict()]

        if content is not None:
            payload['content'] = str(content)

        payload['tts'] = tts

        previous_mentions = getattr(self._state, 'allowed_mentions', None)

        if allowed_mentions:
            if previous_mentions is not None:
                payload['allowed_mentions'] = previous_mentions.merge(allowed_mentions).to_dict()
            else:
                payload['allowed_mentions'] = allowed_mentions.to_dict()
        elif previous_mentions is not None:
            payload['allowed_mentions'] = previous_mentions.to_dict()

        message = await self._state.http.send_followup_message(self.token, payload)
        return Message(state=self._state, data=message, channel=self.channel)
