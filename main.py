from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import (LineBotApi, WebhookHandler)
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (MessageEvent, TextMessage, TextSendMessage,
                            TemplateSendMessage, ImageSendMessage,
                            AudioMessage, ButtonsTemplate,
                            MessageTemplateAction, PostbackEvent,
                            PostbackTemplateAction)

import os
import uuid
import re
import random
import json

from src.models import OpenAIModel
from src.memory import Memory
from src.logger import logger
from src.storage import Storage
from src.utils import get_role_and_content

load_dotenv('.env')

with open("Questions.json", encoding='utf8') as file:
  content = file.read()
  questions_dic = json.loads(content)

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
storage = Storage('db.json')

memory = Memory(system_message=os.getenv('SYSTEM_MESSAGE'),
                memory_message_count=2)
model_management = {}
api_keys = {}


@app.route("/callback", methods=['POST'])
def callback():
  signature = request.headers['X-Line-Signature']
  body = request.get_data(as_text=True)
  app.logger.info("Request body: " + body)
  try:
    handler.handle(body, signature)
  except InvalidSignatureError:
    print(
      "Invalid signature. Please check your channel access token/channel secret."
    )
    abort(400)
  return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
  user_id = event.source.user_id
  text = event.message.text.strip()
  logger.info(f'{user_id}: {text}')

  msg = []
  actions = []
  questions = []

  if text.startswith('「題目」'):
    for i in range(len(questions)):
      questions.append(questions_dic["q" + str(i + 1)])

    global ran_q
    ran_q = random.choice(questions)

    for option in ['A', 'B', 'C', 'D']:
      action = PostbackTemplateAction(
        label=f"({option}) {ran_q['options'][option]}",
        text=f"({option}) {ran_q['options'][option]}",
        data=f"{option}&{ran_q['options'][option]}")
      actions.append(action)
    template = ButtonsTemplate(title='題目', text=ran_q['q'], actions=actions)
    message = TemplateSendMessage(alt_text='題目：' + str(ran_q['q']) + '\n選項：' +
                                  str(ran_q['options']),
                                  template=template)
    msg.append(message)


#調用答案
#調用答案
  elif text.startswith('(A) '):  #換成一個變數，調出上一題的選項答案，以及詳解
    if 'A' == ran_q['a']:
      msg = TextSendMessage(text="答對了！" + str(ran_q['explain']))
      for i, q in enumerate(questions):
        if q == ran_q:
          del questions[q]  # 從題目列表中移除已回答的題目
          break
    else:
      msg = TextSendMessage(text="答錯了！" + str(ran_q['explain']))

  elif text.startswith('(B) '):  #換成一個變數，調出上一題的選項答案，以及詳解
    if 'B' == ran_q['a']:
      msg = TextSendMessage(text="答對了！" + str(ran_q['explain']))
      for i, q in enumerate(questions):
        if q == ran_q:
          del questions[q]  # 從題目列表中移除已回答的題目
          break
    else:
      msg = TextSendMessage(text="答錯了！" + str(ran_q['explain']))

  elif text.startswith('(C) '):  #換成一個變數，調出上一題的選項答案，以及詳解
    if 'C' == ran_q['a']:
      msg = TextSendMessage(text="答對了！" + str(ran_q['explain']))
      if ran_q in questions:
        questions.remove(ran_q)  # 從題目列表中移除已回答的題目
    else:
      msg = TextSendMessage(text="答錯了！" + str(ran_q['explain']))

  elif text.startswith('(D) '):  #換成一個變數，調出上一題的選項答案，以及詳解
    if 'D' == ran_q['a']:
      msg = TextSendMessage(text="答對了！" + str(ran_q['explain']))
      if ran_q in questions:
        questions.remove(ran_q)  # 從題目列表中移除已回答的題目
    else:
      msg = TextSendMessage(text="答錯了！" + str(ran_q['explain']))

      #調用答案

  else:
    #判讀文字前綴
    try:
      if text.startswith('「註冊」'):
        #強制正確
        #api_key = text[3:].strip()
        api_key = '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'
        #強制正確
        model = OpenAIModel(api_key=api_key)
        is_successful, _, _ = model.check_token_valid()
        if not is_successful:
          raise ValueError('Invalid API token')
        model_management[user_id] = model
        api_keys[user_id] = api_key
        storage.save(api_keys)
        msg = TextSendMessage(text='Token 有效，註冊成功')

      elif text.startswith('「說明」'):
        msg = TextSendMessage(text="""
              「說明」
              👉 呼叫使用說明
              
              「清除」
              👉 當前每一次都會紀錄最後兩筆歷史紀錄，這個指令能夠清除歷史訊息
              
              「圖像」 + Prompt
              👉 會調用 DALL∙E 2 Model，以文字生成圖像(但是需要使用英文)。
                  例如：「圖像 flying pigs
              
              語音輸入
              👉 會調用 Whisper 模型，先將語音轉換成文字，再調用 ChatGPT 以文字回覆
              
              其他文字輸入
              👉 調用 ChatGPT 以文字回覆""")

      elif text.startswith('「系統訊息」'):
        memory.change_system_message(user_id, text[5:].strip())
        msg = TextSendMessage(text='輸入成功')

      elif text.startswith('「清除」'):
        memory.remove(user_id)
        msg = TextSendMessage(text='歷史訊息清除成功')

      elif text.startswith('「圖像」'):

        #強制註冊
        #api_key = text[3:].strip()
        api_key = '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'
        #強制正確
        model = OpenAIModel(api_key=api_key)
        is_successful, _, _ = model.check_token_valid()
        if not is_successful:
          raise ValueError('Invalid API token')
        model_management[user_id] = model
        api_keys[user_id] = api_key
        storage.save(api_keys)
        #msg = TextSendMessage(text='Token 有效，註冊成功')
        #強制註冊

        prompt = text[3:].strip()
        memory.append(user_id, 'user', prompt)
        is_successful, response, error_message = model_management[
          user_id].image_generations(prompt)
        if not is_successful:
          raise Exception(error_message)
        url = response['data'][0]['url']
        msg = ImageSendMessage(original_content_url=url, preview_image_url=url)
        memory.append(user_id, 'assistant', url)
      #判斷指令
      elif text.startswith('「'):
        msg = TextSendMessage(text='請輸入正確指令')
      #判斷指令

      #呼叫OpenAI
      else:
        #強制註冊
        #api_key = text[3:].strip()
        api_key = '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'
        #強制正確
        model = OpenAIModel(api_key=api_key)
        is_successful, _, _ = model.check_token_valid()
        if not is_successful:
          raise ValueError('Invalid API token')
        model_management[user_id] = model
        api_keys[user_id] = api_key
        storage.save(api_keys)
        #msg = TextSendMessage(text='Token 有效，註冊成功')
        #強制註冊

        memory.append(user_id, 'user', text)
        is_successful, response, error_message = model_management[
          user_id].chat_completions(memory.get(user_id),
                                    os.getenv('OPENAI_MODEL_ENGINE'))
        if not is_successful:
          raise Exception(error_message)
        role, response = get_role_and_content(response)
        msg = TextSendMessage(text=response)
        #test
        #print (msg.decode('unicode_escape'))
        #test
        memory.append(user_id, role, response)
      #呼叫OpenAI

    #msg訊息格式錯誤回傳
    except ValueError:
      msg = TextSendMessage(text='Token 無效，請重新註冊，格式為 「註冊」 sk-xxxxx')
    except Exception as e:
      memory.remove(user_id)
      if str(e).startswith('Incorrect API key provided'):
        msg = TextSendMessage(text='OpenAI API Token 有誤，請重新註冊。')
      elif str(e).startswith(
          'That model is currently overloaded with other requests.'):
        msg = TextSendMessage(text='已超過負荷，請稍後再試')
      else:
        msg = TextSendMessage(text=str(e))
    #msg訊息格式錯誤回傳

  #送出給LINE
  line_bot_api.reply_message(event.reply_token, msg)

  # 讀取bib檔，並將每一行轉換成一個字串
  with open('logs', 'r') as f:
    lines = f.readlines()

  # 使用正則表達式來提取uID和msg
  pattern = re.compile(r'->\s(U[^\s]+):\s(.+)')
  data = []
  for line in lines:
    match = pattern.search(line)
    if match:
      uID, msg = match.group(1), match.group(2)
      data.append((uID, msg))

  # 顯示提取出的結果
  for d in data:
    print('uID:', d[0], 'msg:', d[1])

  #送出給LINE


@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
  user_id = event.source.user_id
  audio_content = line_bot_api.get_message_content(event.message.id)
  input_audio_path = f'{str(uuid.uuid4())}.m4a'
  with open(input_audio_path, 'wb') as fd:
    for chunk in audio_content.iter_content():
      fd.write(chunk)

  try:
    if not model_management.get(user_id):
      raise ValueError('Invalid API token')
    else:
      is_successful, response, error_message = model_management[
        user_id].audio_transcriptions(input_audio_path, 'whisper-1')
      if not is_successful:
        raise Exception(error_message)
      memory.append(user_id, 'user', response['text'])
      is_successful, response, error_message = model_management[
        user_id].chat_completions(memory.get(user_id), 'gpt-3.5-turbo')
      if not is_successful:
        raise Exception(error_message)
      role, response = get_role_and_content(response)
      memory.append(user_id, role, response)
      msg = TextSendMessage(text=response)
  except ValueError:
    msg = TextSendMessage(text='請先註冊你的 API Token，格式為 「註冊」 [API TOKEN]')
  except Exception as e:
    memory.remove(user_id)
    if str(e).startswith('Incorrect API key provided'):
      msg = TextSendMessage(text='OpenAI API Token 有誤，請重新註冊。')
    else:
      msg = TextSendMessage(text=str(e))
  os.remove(input_audio_path)
  line_bot_api.reply_message(event.reply_token, msg)


@app.route("/", methods=['GET'])
def index():
  with open(os.path.join('index.html'), 'r', encoding='utf-8') as index:
    html_index = index.read()
  return (html_index)


@app.route("/stuall/", methods=['GET'])
def stuall():
  with open(os.path.join('stuall.html'), 'r', encoding='utf-8') as stuall:
    html_stuall = stuall.read()
  return (html_stuall)


@app.route("/stuone/", methods=['GET'])
def stuone():
  with open(os.path.join('stuone.html'), 'r', encoding='utf-8') as stuone:
    html_stuone = stuone.read()
  return (html_stuone)


@app.route("/contact/", methods=['GET'])
def contact():
  with open(os.path.join('contact.html'), 'r', encoding='utf-8') as contact:
    html_contact = contact.read()
  return (html_contact)


if __name__ == "__main__":
  try:
    data = storage.load()
    for user_id in data.keys():
      model_management[user_id] = OpenAIModel(api_key=data[user_id])
  except FileNotFoundError:
    pass
  app.run(host='0.0.0.0', port=8080)
