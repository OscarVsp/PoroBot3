import disnake

def new_embed(title = disnake.Embed.Empty, description = disnake.Embed.Empty, color = disnake.Embed.Empty, author : dict = None, fields : dict = None, thumbnail = None, image : str = None, footer : str = None, url = disnake.Embed.Empty):
    """

    """

    #use *arhs and **kwargs !!
    embed : disnake.Embed = disnake.Embed(title = title, description = description, color = color, url = url)

    if fields != None:
        if type(fields) == list:
            for field in fields:
                if 'inline' in field.keys():
                    embed.add_field(name=field['name'], value=field['value'], inline=field['inline'])
                else:
                    embed.add_field(name=field['name'], value=field['value'], inline=False)
        else:
            raise TypeError(f'Argument "fields" should be "list" but {type(fields)} has been provided.')

    if author != None:
        embed.set_author(
            name = author.get('name'),
            icon_url = author.get('icon')
        )

    if thumbnail != None:
        embed.set_thumbnail(url=thumbnail)

    if image != None:
        embed.set_image(url=image)

    if footer != None:
        embed.set_footer(text=footer)
    
    return embed
#todo fields use kay and items directly