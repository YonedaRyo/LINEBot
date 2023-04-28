from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import csv
import os
import pandas as pd
import numpy as np
from datetime import datetime 

#ファイルの存在確認（任意のファイルが存在しなければ作成を行う！）
def file_create():
    '''ファイルが存在する場合'''
    if os.path.exists("./" + user_id + ".csv"):
        pass
    else:
        with open(user_id + '.csv','w') as csv_file:
            fieldnames = ['日付','開始時刻','終了時刻','今日の研究時間','累計研究時間']
            writer = csv.DictWriter(csv_file, fieldnames = fieldnames)
            writer.writeheader()
            

#開始時の処理
def punch_in():
    global start_time
    df = pd.read_csv(user_id + '.csv',header = None)
    timestamp = datetime.now().replace(second=0,microsecond=0)
    date = timestamp.strftime('%Y/%m/%d') #日付
    start_time = timestamp.strftime('%H:%M') #開始時刻
    
    '''連続で研究開始が打刻されたときの例外処理的なもの'''
    if df.iloc[-1, 2] == '0' or df.iloc[-1, 2] =='終了時刻':
        pass
    else:  
        new_row = {'日付':0,'開始時刻':0,'終了時刻':0,'今日の研究時間':0,'累計研究時間':0}
        df.loc[len(df)] = new_row
        df.iloc[-1, 0] = date
        df.iloc[-1, 1] = start_time
        df.iloc[-1, 2] = '0'
        #df = df.append({'日付':date,'開始時刻':punch_in,'終了時刻':'0','今日の研究時間':'0','累計研究時間':'0'},ignore_index=True) #なぜかdf.append使えなかった；；
        df.to_csv(user_id + '.csv',index= False,header=False)

#終了時の処理
def punch_out():
    global end_time,Research_time,total_time
    df = pd.read_csv(user_id + '.csv',header = None)
    timestamp = datetime.now().replace(second=0,microsecond=0)
    end_time = timestamp.strftime('%H:%M') #終了時刻
    
    '''今日の研究時間と累計研究時間の計算'''
    time1 = df.iloc[-1, 1] #開始時刻をdfから取り出し(一度保存しないと複数人に対応できなさそうだったので)
    print(time1)
    Research_time = ((datetime.strptime(end_time,'%H:%M')) - (datetime.strptime(time1,'%H:%M'))) #研究時間
    #timedeltaオブジェクトから時間・分を取得する
    hours, remainder = divmod(Research_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    minutes = minutes / 60
    Research_time = f"{hours + minutes:.2f}"

    last_index = len(df) - 1 #最終行のインデックス取得
    last_time = df.iloc[last_index - 1,4] #前回の累計時間
    if  last_time == '累計研究時間': #1回目の例外処理
        total_time = float(Research_time)
        total_time = f"{total_time:.2f}"
    else:
        total_time = float(Research_time) + float(last_time)
        total_time = f"{total_time:.2f}"
            
    df.iloc[-1, 2] = end_time
    df.iloc[-1, 3] = Research_time
    df.iloc[-1, 4] = total_time
    df.to_csv(user_id + '.csv',index= False,header=False)

    

#ここからラインボットの設定関係
app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = '#自分のCHANNEL_ACCESS_TOKEN'
YOUR_CHANNEL_SECRET = '#自分のCHANNEL_SECRET'

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_woeld():
    return "研究時間管理botが動いています"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event): 
    global user_disp_name,user_id
    
    profile = line_bot_api.get_profile(event.source.user_id)
    user_id = event.source.user_id #ユーザID
    user_disp_name = profile.display_name #アカウント名
    
    if event.message.text =='研究開始！':
        file_create() #ファイルの存在確認
        punch_in() #開始時の処理
        '''csvから開始時刻を呼び出してメッセージを送る'''
        #df = pd.read_csv(user_id + '.csv',header = None)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text = '{}さん今日も頑張りましょう！\n研究開始時刻 : {}'.format(user_disp_name,start_time)))
            
    elif event.message.text =='研究終了！':
        file_create() #ファイルの存在確認
        punch_out() #終了時の処理
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text = '{}さん今日一日お疲れ様でした！\n研究終了時刻 : {}です。\n今回の研究時間 : {}時間\n累計研究時間 : {}時間'.format(user_disp_name,end_time,Research_time,total_time)))
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text = '私は研究時間を管理するBotです。'))


if __name__ == "__main__":
    app.run()
