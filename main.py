import os
import discord
from discord.ext import commands
import requests
import json
from datetime import datetime
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', '1420430545799745721'))
WOOCOMMERCE_URL = os.getenv('WOOCOMMERCE_URL', 'https://academiadecienciasdelejercicio.com')
WOOCOMMERCE_KEY = os.getenv('WOOCOMMERCE_KEY')
WOOCOMMERCE_SECRET = os.getenv('WOOCOMMERCE_SECRET')

# Role mapping based on product tags/categories
ROLE_MAPPING = {
      'single-course': 'Single Curse',
      'formacion-por-fases': 'Formación por Fases',
      'mentoria': 'Mentoría',
      'club-ace': 'Club ACE',
      'diplomatura': 'Diplomatura'
}

# Free role for all members
FREE_ROLE = 'Free'

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
      print(f'{bot.user} has connected to Discord!')
      await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='for new purchases'))

@bot.event
async def on_member_join(member):
      """When a member joins, assign Free role"""
      guild = bot.get_guild(GUILD_ID)
      if guild:
                free_role = discord.utils.get(guild.roles, name=FREE_ROLE)
                if free_role:
                              await member.add_roles(free_role)
                              # Send welcome DM
                              try:
                                                embed = discord.Embed(
                                                                      title='¡Bienvenido a Academia de Ciencias del Ejercicio!',
                                                                      description='Tienes acceso al rol **Free**. Para acceder a más contenido, compra un producto en nuestra tienda.',
                                                                      color=discord.Color.green()
                                                )
                                                await member.send(embed=embed)
                                            except:
                pass

  @bot.command(name='claim')
async def claim_role(ctx, order_id: str):
      """
          Manually claim role based on WooCommerce order ID
              Usage: /claim [order_id]
                  """
      guild = bot.get_guild(GUILD_ID)
      if not guild:
                await ctx.respond('❌ Guild not found', ephemeral=True)
                return

      # Verify order in WooCommerce
      try:
                auth = (WOOCOMMERCE_KEY, WOOCOMMERCE_SECRET)
                response = requests.get(
                    f'{WOOCOMMERCE_URL}/wp-json/wc/v3/orders/{order_id}',
                    auth=auth,
                    timeout=10
                )

        if response.status_code != 200:
                      await ctx.respond(f'❌ Order #{order_id} not found', ephemeral=True)
                      return

        order_data = response.json()
        customer_email = order_data.get('billing', {}).get('email')

        # Get product info from order
        products = order_data.get('line_items', [])
        roles_to_assign = set()

        for product in products:
                      product_id = product.get('product_id')
                      # Get product details to check tags
                      product_response = requests.get(
                          f'{WOOCOMMERCE_URL}/wp-json/wc/v3/products/{product_id}',
                          auth=auth,
                          timeout=10
                      )

            if product_response.status_code == 200:
                              product_data = product_response.json()
                              tags = product_data.get('tags', [])

                for tag in tags:
                                      tag_name = tag.get('name', '').lower().replace(' ', '-')
                                      if tag_name in ROLE_MAPPING:
                                                                roles_to_assign.add(ROLE_MAPPING[tag_name])

                          if not roles_to_assign:
                                        await ctx.respond('❌ No valid roles found for this order', ephemeral=True)
                                        return

        # Assign roles to user
        member = ctx.author
        assigned = []

        for role_name in roles_to_assign:
                      role = discord.utils.get(guild.roles, name=role_name)
                      if role:
                                        await member.add_roles(role)
                                        assigned.append(role_name)

                  embed = discord.Embed(
                                title='✅ Roles Assigned',
                                description=f'You have been assigned: {", ".join(assigned)}',
                                color=discord.Color.green()
                  )
        await ctx.respond(embed=embed, ephemeral=True)

except Exception as e:
        print(f'Error in claim_role: {e}')
        await ctx.respond(f'❌ Error processing order: {str(e)}', ephemeral=True)

@bot.event
async def on_message(message):
      """Handle messages"""
      if message.author == bot.user:
                return

      await bot.process_commands(message)

@bot.command(name='myRoles')
async def my_roles(ctx):
      """Show your current roles"""
      roles = [role.name for role in ctx.author.roles if role.name != '@everyone']

    if not roles:
              await ctx.respond('You have no roles assigned', ephemeral=True)
              return

    embed = discord.Embed(
              title='Your Roles',
              description='\n'.join([f'• {role}' for role in roles]),
              color=discord.Color.blue()
    )
    await ctx.respond(embed=embed, ephemeral=True)

async def main():
      async with bot:
                await bot.start(DISCORD_TOKEN)

  if __name__ == '__main__':
        asyncio.run(main())
