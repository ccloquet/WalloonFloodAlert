# coding: utf-8

# to run every hour between 0700 & 2100 using CRON
# for instance using pythonanywhere
# * 7-21 * * * /home/ubuntu/cron/testwater.py >/dev/null 2>&1

import datetime
import sys
now = datetime.datetime.now()
print(now.hour)

#if (now.hour < 6) | (now.hour > 20): #UTC
    sys.exit()

# CONFIG
account_sid = ""
auth_token  = ""
from_nr     = "" #+32...

# Dans Twilio : Configuration de la réponse aux messages envoyés à ce numéro (TwiML bin)
# <Response>
#  <Message>
#    Message de Poppy Alert. Utile? Parlez-en autour de vous.Plus utile? Envoyez NOALERT à ce numéro
#  </Message>
# </Response>

# END CONFIG

#TODO
# all messages before => redact
# alternatively, send with facebook, telegram, etc
# ensuite : toute la gestion, l'interface client, le GDPR, ...
# critère de non envoi pourrait être plus

import requests
import bs4 as BeautifulSoup
from tabulate import tabulate
from operator import itemgetter
import datetime
from twilio.rest import TwilioRestClient

client      = TwilioRestClient(account_sid, auth_token) # ! version 5 !!! -> pip install twilio==5.7.0
newtable    = []

###########################################################
#GET SUBSCRIBERS

#EITHER MANUALLY
#recipients  = [['NUMBER', 'STATION']] # pourrait être pris des SMS envoyés à ce numéro // 

#OR BY CHECKING THE INCOMING MESSAGES
recipients = []
messages = client.messages.list(to_=from_nr, page_size=1000)

subscribers = {}
for message in reversed(messages):
    subscribers[message.from_] = message.body.upper()

for subscriber in subscribers:
    msg = subscribers[subscriber]
    if msg.find("SUBSCRIBE") == 0:
        print(subscriber, msg)
        sta = msg.split(' ')
        if len(sta) > 1:
            recipients.append([subscriber, sta[1]])

print(recipients)
#END GET SUBSCRIBERS
###########################################################

for i in range(0,89):
    r = requests.get('http://voies-hydrauliques.wallonie.be/opencms/opencms/fr/hydro/Actuelle/crue/cruetableau.do?id=' + str(i))
    if r.status_code != 200:
        continue
    html = r.text
    soup = BeautifulSoup.BeautifulSoup(html, "html.parser")

    table = soup.find('table', {"summary":True})
    rows  = table.findAll('tr')
    what = ''
    for row in rows:
        ch    = row.find('th')
        if ch != None:
            ch = ch.find('strong')
            if ch != None:
                what = ch.text
        cells = row.findAll('td')

        if cells == None:
            continue

        newrow = [what]
        for cell in cells:
            if cell == None:
                continue;

            t = cell.text.strip()
            if t == None:
                continue
            if t == '':
                t = cell.find('img')
                if t == None:
                    continue
                else:
                    t = t.attrs['alt']
                if 'la fiche signal' in t:
                    continue
            if t == '':
                continue

            newrow.append(t)
        newtable.append(newrow)

mytable = []
for row in newtable:
    if len(row) < 2:
        continue
    if row in mytable:
        continue

    mytable.append(row)

mytable=sorted(mytable, key=itemgetter(1))

print(tabulate(mytable))

for r in recipients:
    for e in mytable:
        if (e[1] == r[1]) & (e[3] != 'Normale'): # pour test : mettre == 'Normale'
            body="La station " + e[1] + " est en situation " + e[3] + ". Infos via http://voies-hydrauliques.wallonie.be/opencms/opencms/fr/hydro/Actuelle/crue/index.html. Message de Poppy Alert. Utile? Parlez-en autour de vous ou aidez-nous via http://paypal.me/ccloquet. Plus utile? Envoyez NOALERT à ce numéro"
            print (body)

            # si déjà reçu qqch hier ou aujourd'hui -> n'envoie rien
            # le test pourrait être plus intelligent
            today     = datetime.date.today()
            messages = client.messages.list(to=r[0], from_=from_nr, date_sent=today)
            if len(messages) > 0:
                print('*')
                continue
            yesterday = datetime.date.fromordinal(datetime.date.today().toordinal()-1)
            messages = client.messages.list(to=r[0], from_=from_nr, date_sent=yesterday)
            if len(messages) > 0:
                print('*')
                continue
            print('sending SMS to ' + r[0])
            #send SMS
            message = client.messages.create(to=r[0], from_=from_nr, body=body)


