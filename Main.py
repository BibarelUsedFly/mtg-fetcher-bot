from dotenv import load_dotenv
import os
import discord
from Help import *
import requests
from io import BytesIO
import json
import random

load_dotenv()

TOKEN = os.getenv("TOKEN")
SCRYFALL = 'https://api.scryfall.com/cards/random'

class BotClient(discord.Client):
    async def get_card_img(self, message, req):
        if req.status_code==400:
            await message.channel.send(BADREQ)
        elif req.status_code==404:
            await message.channel.send(MISSING)
        else:
            card = discord.File(BytesIO(req.content), filename='card.png')
            await message.channel.send(file=card)

    async def decklist_add(self, qty, params, deck, limit=100):
        while (qty > 0):
            req = requests.get(SCRYFALL, params=params)
            card = json.loads(req.content.decode('utf8'))
            cardname = card['name']
            if cardname in deck:
                ## Si ya hay límite, requestear otra
                if deck[cardname] < limit:
                    deck[cardname] += 1
                    qty -= 1
            else:
                deck[cardname] = 1
                qty -= 1
        return deck

    async def on_ready(self):
        print('{0}: Ready'.format(self.user))
        await client.change_presence(activity=discord.Activity \
            (type=discord.ActivityType.listening, name='~help'))

    async def on_message(self, message):
        ### SETUP ------------------------------------
        if message.author == client.user:
            return
        txt = message.content.lower().split()
        if len(txt) == 0: 
            return

        #Help -------------------------------------------------------
        if txt[0] == '~help':
            if len(txt) == 1:
                await message.channel.send(HELP)
            else:
                await message.channel.send(NAH)

        ## Get a random integer -----------------------------------------------
        elif txt[0] == '~rand':
            if len(txt) > 2:
                inicio = int(txt[1])
                fin = int(txt[2])
            elif len(txt) == 2:
                inicio = 0
                fin = int(txt[1])
            else:
                inicio = 0
                fin = 100
            await message.channel.send(str(random.randint(inicio, fin)))            

        ## Get a card -----------------------------------------------
        elif txt[0] == '~mtg':
            params = {'format': 'image'}
            if len(txt) > 1:
                addparams = " ".join(txt[1:])
                params['q'] = "-is:alchemy " + addparams
            req = requests.get(SCRYFALL, params=params)
            await self.get_card_img(message, req)

        ## Get a commander card -------------------------------------
        ## Partner pending
        elif txt[0] == '~mtgcommander':
            params = {'format': 'image', 'q': '(is:commander)'}
            if len(txt) > 1:
                addparams = " ".join(txt[1:])
                params['q'] = params['q'] + " and (" + addparams + ")"
            req = requests.get(SCRYFALL, params=params)
            await self.get_card_img(message, req)


        ## Get a random MTG deck ------------------------------------
        elif txt[0] == "~mtgbuild":
            DECKSIZE = 60
            LIMITCOPY = 4
            LANDPER = 0.4
            nl_params = \
                {'format': 'json',
                 'q': '-t:land -is:funny -is:alchemy -t:conspiracy'}
            l_params = \
                {'format': 'json',
                 'q': 't:land -is:funny -is:alchemy -t:conspiracy'}
            deck = {}
            n_lands = int(round(DECKSIZE * LANDPER, 0))
            n_nonlands = DECKSIZE - n_lands
            
            ## Deck colors
            if len(txt) > 1:
                txt[1] = "".join(set(txt[1])) # Sacar duplicados
                addparams = " ".join(txt[1:])
                ## Bad request
                for letra in addparams:
                    if letra not in 'wubrg':
                        await message.channel.send(BADREQ)
                        return
                nl_params['q'] += " id<={}".format(addparams)
                l_params['q'] += " id<={}".format(addparams)
                l_params['q'] += " produces<={}".format(addparams)
            else:
                await message.channel.send('¿Y los colores?')
                return

            ## Get non-lands
            deck = await self.decklist_add(n_nonlands, nl_params, deck)
            
            ## Monocolor
            if len(txt[1]) == 1:
                L_BASICS = 0.85
                n_basics = int(round(n_lands * L_BASICS, 0))
                lbasic_params = l_params.copy()
                lbasic_params['q'] += " t:basic"
                n_nonbasic = n_lands - n_basics
                n_duals = 0

            ## Bicolor
            elif len(txt[1]) == 2:
                L_DUALS = 0.25
                L_BASICS = 0.6
                n_basics = int(round(n_lands * L_BASICS, 0))
                lbasic_params = l_params.copy()
                lbasic_params['q'] += " t:basic"
                n_duals = int(round(n_lands * L_DUALS, 0))
                ldual_params = l_params.copy()
                ldual_params['q'] += " produces={}".format(addparams)
                n_nonbasic = n_lands - n_basics - n_duals

            ## Get basic lands
            deck = await self.decklist_add(n_basics, lbasic_params, deck)

            ## Get nonbasic lands
            deck = await self.decklist_add(
                n_nonbasic, l_params, deck, LIMITCOPY)

            ## Get dual lands
            deck = await self.decklist_add(
                n_duals, ldual_params, deck, LIMITCOPY)

            ## Send decklist
            msg = ''
            for carta, qty in deck.items():
                msg += "{} {}\n".format(qty, carta)
            await message.channel.send(msg)
        

client = BotClient()
client.run(TOKEN)
