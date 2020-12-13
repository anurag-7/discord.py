from collections import namedtuple

from .enums import try_enum, InteractionType, InteractionType
from .member import Member
from .http import Route

ResponseOption = namedtuple('Option', 'name value')
ApplicationCommandOptionChoice = namedtuple('ApplicationCommandOptionChoice', 'name value')

class ApplicationCommand:
    def __init__(self, *, state, data, guild_id=None):
        self._state = state
        self.guild_id = guild_id
        self.id = int(data['id'])
        self.application_id = int(data['application_id'])
        self.name = data['name']
        self.description = data['description']

        self.options = [ApplicationCommandOption(**option) for option in data['options']]

    async def delete(self):
        if not guild:
            return await self._state.delete_application_command(self.application_id, self.id)
        
        await self._state.delete_guild_application_command(self.application_id, self.id, self.guild.id)
    
    async def edit(self, guild=None, **kwargs):
        pass

class ApplicationCommandOption(namedtuple('ApplicationCommandOption', 'name description type default required choices options')):
    def add_option(self, *, name, description, type, default=None, required=None, choices=None):
        option = {'name': name, 'description': description, 'type': type}
        if default is not None:
            option['default'] = default
        if required is not None:
            option['required'] = required
        if choices is None:
            choices = []

        option['choices'] = [self.__class__(**choice) for choice in choices]  
        option = self.__class__(**option)
        self.options.append(option)
        return option

    def to_dict(self):
        data = self._asdict()
        data['type'] = data['type'].value
        data['options'] = [option.to_dict() for option in data['options']]
        data['choices'] = [choice._as_dict() for choice in data['choices']]
        return data

class Interaction:
    def __init__(self, *, state, data):
        print(data)
        self._state = state
        self.id = int(data['id'])
        self.type = try_enum(InteractionType, data['type'])
        self.channel, self.guild = state._get_guild_channel(data)
        self.member = Member(data=data['member'], guild=self.guild, state=state)
        self.token = data['token']
        self.options = [ResponseOption(option['name'], option['value']) for option in data['data'].get('options', [])]
        self.name = data['data']['name']
        self.version = data['version']

    async def send(self, content=None, *, type, tts=False, embed=None, embeds=None, allowed_mentions=None, flags=0):
        """
        Sends a message using the webhook.
        The content must be a type that can convert to a string through ``str(content)``.
        If the ``embed`` parameter is provided, it must be of type :class:`Embed` and
        it must be a rich embed type. You cannot mix the ``embed`` parameter with the
        ``embeds`` parameter, which must be a :class:`list` of :class:`Embed` objects to send.
        Parameters
        ------------
        content: :class:`str`
            The content of the message to send.
        tts: :class:`bool`
                    Indicates if the message should be sent using text-to-speech.
        embed: :class:`Embed`
            The rich embed for the content to send. This cannot be mixed with
            ``embeds`` parameter.
        embeds: List[:class:`Embed`]
            A list of embeds to send with the content. Maximum of 10. This cannot
            be mixed with the ``embed`` parameter.
        allowed_mentions: :class:`AllowedMentions`
            Controls the mentions being processed in this message.
        type: :class:`InteractionResponseType`
        Raises
        --------
        HTTPException
            Sending the message failed.
        NotFound
            This webhook was not found.
        Forbidden
            The authorization token for the webhook is incorrect.
        InvalidArgument
            You specified both ``embed`` and ``embeds`` or the length of
            ``embeds`` was invalid or there was no token associated with
            this webhook.
        """

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

        message = await self._state.http.interaction_callback(self.id, self.token, {'data': payload, 'type': type.value})

    async def edit_original(self, **kwargs):
        pass

    async def delete_original(self):
        pass

    async def send_followup(self, **kwargs):
        pass

    async def delete_followup(self):
        pass

    async def edit_followup(self, **kwargs):
        pass
