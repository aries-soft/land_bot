#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
Send /start to initiate the conversation.
"""

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Document)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

import logging
import csv
import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from smtplib import SMTP_SSL
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

REPLY_KEYBOARD = [['Номер магазина', 'Причина вызова'],
                  ['Наименование оборудования'],
                  ['Сброс', 'Готово', 'E-Mail']]

MARKUP = ReplyKeyboardMarkup(REPLY_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

data_dict = dict.fromkeys(['Акт №', 'Дата', 'Номер магазина', 'Тип магазина',
                           'Адрес', 'Причина вызова', 'Наименование оборудования'], "")
mag_list = list()
mag_dict = dict()

def facts_to_str():
    facts = list()

    for key, value in data_dict.items():
        facts.append('%s: %s' % (key, value))

    return "\n".join(facts).join(['\n', '\n'])


def start(bot, update):
    update.message.reply_text(
        "Здорова! Этот бот замутит акт для Лэнд-Сервиса "
        "Введите данные о магазине!",
        reply_markup=MARKUP)
    return CHOOSING


def regular_choice(bot, update):
    text = update.message.text
    data_dict['choice'] = text
    update.message.reply_text('Введите %s' % text.lower(),
        reply_markup=ReplyKeyboardMarkup([['Сброс', 'Отмена']], one_time_keyboard=True, resize_keyboard=True))

    return TYPING_REPLY

def received_information(bot, update):
    text = update.message.text
    category = data_dict['choice']
    if text.lower() != 'отмена':
        data_dict[category] = text
    if text.lower() == 'сброс':
        del data_dict[category]
    del data_dict['choice']

    autocomplete_data(bot, update)

    return CHOOSING

def autocomplete_data(bot, update):
    if 'Номер магазина' in data_dict:
        if data_dict['Номер магазина'] in mag_dict:
            num = data_dict['Номер магазина']
            data_dict['Адрес'] = mag_dict[num]['addr']
            data_dict['Тип магазина'] = mag_dict[num]['type']
            data_dict['E-Mail'] = mag_dict[num]['e-mail']
        else:
            if 'Адрес' in data_dict:
                del data_dict['Адрес']
    else:
        if 'Адрес' in data_dict:
            del data_dict['Адрес']

    now = datetime.datetime.now()
    data_dict['Акт №'] = now.strftime("%d%m%y")+"РРА"
    data_dict['Дата'] = now.strftime("%d%m%y")

    update.message.reply_text("Текущие данные:"
                              "%s"
                              "Введите данные или получите pdf"
                              % facts_to_str(),
                              reply_markup=MARKUP)

def reset_data(bot, update):
    data_dict = dict.fromkeys(['Акт №', 'Дата', 'Номер магазина', 'Тип магазина', 'Адрес',
                               'Причина вызова', 'Наименование оборудования'], "")
    update.message.reply_text("Текущие данные:"
                              "%s"
                              "Введите данные или получите pdf"
                              % facts_to_str(), reply_markup=MARKUP) 
    return CHOOSING

def pdf_gen(bot, update, chat_data):
    """main"""
    fonfile = 'fon.png'
    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    pdf_canvas = canvas.Canvas("out.pdf")
    #width, height = A4
    pdf_canvas.drawImage(fonfile, 1.3*cm, 0.8*cm, 18.5*cm, 28*cm)

    pdf_canvas.setFont("Arial", 14)
    pdf_canvas.drawCentredString(18.3*cm, 28.2*cm, data_dict['Акт №'])
    #Дата
    if len(data_dict['Дата']) >= 6:
        pdf_canvas.drawCentredString(17.0*cm, 27.45*cm, data_dict['Дата'][0])
        pdf_canvas.drawCentredString(17.5*cm, 27.45*cm, data_dict['Дата'][1])
        pdf_canvas.drawCentredString(18.0*cm, 27.45*cm, data_dict['Дата'][2])
        pdf_canvas.drawCentredString(18.5*cm, 27.45*cm, data_dict['Дата'][3])
        pdf_canvas.drawCentredString(19.0*cm, 27.45*cm, data_dict['Дата'][4])
        pdf_canvas.drawCentredString(19.5*cm, 27.45*cm, data_dict['Дата'][5])

    pdf_canvas.setFont("Arial", 10)
    pdf_canvas.drawString(4.5*cm, 26.55*cm, data_dict['Номер магазина'] + " " + 
                          data_dict['Тип магазина'])
    pdf_canvas.drawString(13.2*cm, 26.55*cm, data_dict['Адрес'])
    pdf_canvas.drawString(4.5*cm, 25.4*cm, "Романенко Р.А.")
    pdf_canvas.drawString(4.5*cm, 24.4*cm, data_dict['Причина вызова'])
    pdf_canvas.drawString(4.5*cm, 23.7*cm, data_dict['Наименование оборудования']) 
    pdf_canvas.drawString(1.5*cm, 3.0*cm, "Романенко Роман Андреевич")

    pdf_canvas.showPage()
    pdf_canvas.save()
    
    update.message.reply_text("PDF файл получен", reply_markup=MARKUP)
    #bot.send_chat_action(update.message.chat_id, 'upload_document')
    #bot.send_photo(chat_id=update.message.chat_id, photo=open('fon.png', 'rb'))
    #bot.send_document(chat_id=update.message.chat_id, document=open("out.pdf", 'rb'))
    
    return CHOOSING

def send_email(bot, update, chat_data):
    """printfon"""
    frommail = 'aries-soft@mail.ru'
    tomail = data_dict['E-Mail']

    # Compose attachment
    part = MIMEBase('application', "octet-stream")
    part.set_payload(open("out.pdf", "rb").read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="akt.pdf"')

    # Compose message
    msg = MIMEMultipart()
    msg['Subject'] = 'AKT'
    msg['From'] = frommail
    msg['To'] = tomail
    msg.attach(part)

    with open('pass.txt', encoding='utf-8-sig') as mfile:
        for row in mfile:
            PASS=row
    mfile.close()


    s = SMTP_SSL('smtp.mail.ru:465')
    s.login('aries-soft@mail.ru',PASS)
    s.sendmail(frommail, [tomail], msg.as_string())
    s.quit()

    update.message.reply_text("E-Mail отправлен", reply_markup=MARKUP)

    return CHOOSING

def done(bot, update):
    if 'choice' in data_dict:
        del data_dict['choice']

    update.message.reply_text("I learned these facts about you:"
                              "%s"
                              "Until next time!" % facts_to_str())

    data_dict.clear()
    return ConversationHandler.END


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    with open('token.txt', encoding='utf-8-sig') as mfile:
        for row in mfile:
            TOKEN=row
    mfile.close()

    #global mag_list
    with open('magdata.csv', encoding='utf-8-sig') as mfile:
        csvreader = csv.reader(mfile)
        for row in csvreader:
            mag_list.append(row)
    mfile.close()

    #{'3468': {'type': 'Пятерочка', 'addr': 'Александрийская, ул. Швыдковский пер. 2А' },
    for row in mag_list:
        mag_dict[row[0].strip()]={'type':row[1].strip(), 'addr':(row[2]+', '+row[3]).strip(),
        'e-mail':row[4].strip(), 'tel1':row[5].strip(), 'tel2':row[6].strip()}

    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [RegexHandler('^(Номер магазина|Причина вызова|Наименование оборудования)$',
                                    regular_choice),
                       RegexHandler('^(Сброс)$',reset_data),
                       RegexHandler('^(Готово)$',pdf_gen,pass_chat_data=True),
                       RegexHandler('^(E-Mail)$',send_email,pass_chat_data=True)],

            TYPING_CHOICE: [MessageHandler(Filters.text,
                                           regular_choice),],

            TYPING_REPLY: [MessageHandler(Filters.text,
                                          received_information),],
        },

        fallbacks=[RegexHandler('^Done$', done)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
