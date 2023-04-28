# LINEBotで研究時間を管理（勤怠管理bot的なもの）
LINEBotのMessagingAPIを使って研究開始と研究終了を記録し，一日の研究時間とこれまでの累計時間を記録する．
## 動作するときのイメージ
- 常時ラズパイ上でpythonプログラムが動作している
- この時Flaskを使ってWebフレームワークが動作している
- LINEBotで特定のメッセージを受け取ったときにcsvに打刻する
- LINEBotからのイベント受け取りはWebhookにより指定したWebサーバーに送信する
- ラズパイはローカルサーバー上で動作しているのでngrokを使って外部サーバーから受け取っている
- 指定されたWebサーバーからのイベントでpythonを制御して色々する


### LINEBot×Python×Raspberry Pi×ngrokを使って実装を行う
![Screenshot_20230407-195847](https://user-images.githubusercontent.com/130141399/230598056-f77d095f-1845-434e-90e2-8289858d7b01.png)

## LINEBotの作成
### ビジネスアカウントを作成する
[LINE Developers](https://developers.line.biz/ja/services/messaging-api/)からログインを押し画像の画面が表示されたらビジネスアカウントを作成する
![スクリーンショット 2023-04-07 182441](https://user-images.githubusercontent.com/130141399/230583693-8baeb486-9372-418f-9d76-e6fbb0668512.png)
### 新規チャンネルの作成
新規でMessaging APIのチャンネルを新規作成する
![スクリーンショット 2023-04-07 185051](https://user-images.githubusercontent.com/130141399/230587893-362e5352-c44f-4a03-a34c-60be49c27417.png)  
この先は指示に従って作成してください
### 必要情報の確認　（この後認証のために使用する）
#### Basic settingの項目から Channel secretの情報取得（黄色で塗りつぶした部分をコピーしておく）
![スクリーンショット 2023-04-07 190423](https://user-images.githubusercontent.com/130141399/230590256-a0fb51cc-a4fd-4c5a-bd82-90bfd5647865.png)
##### MessagingAPIの項目から　Channel access tokenの情報を取得（黄色で塗りつぶした部分をコピーしておく）
![スクリーンショット 2023-04-07 190740](https://user-images.githubusercontent.com/130141399/230590813-c03c9b08-683e-4703-858d-df475ad6ed6f.png)

##  Pythonでコードを書く
### PythonSDKを参考に実際に書いてみる！
[line-bot-sdk-python](https://github.com/line/line-bot-sdk-python)のgithubを参考にさせていただきました．  
そのままコピペしてそこに追加していく形で作成  

#### 今回はCSVファイルに情報を書き加えていくことにする

### 新規アクセスしたユーザーにはファイルを新規作成する
関数内の処理内容としてはパス内にLineのユーザーIDを含んだファイルが存在するか確認し，ない場合は新規作成・ある場合は何も行わない
```python
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
```

### 研究を開始したときの処理関数
開始処理を行ったときの時刻をdatetime.nowで取得し，対象のセル位置に打刻する  
連続で開始処理が行われると正常に動かないので連続打刻防止の条件分岐をつけている  

```python
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
        df.iloc[-1, 1] = '0'
        #df = df.append({'日付':date,'開始時刻':punch_in,'終了時刻':'0','今日の研究時間':'0','累計研究時間':'0'},ignore_index=True) #なぜかdf.append使えなかった；；
        df.to_csv(user_id + '.csv',index= False,header=False)
```

### 研究を終了したときの処理関数
終了処理を行ったときの時刻をdatetime.nowで取得し，対象のセル位置に打刻する  
開始時刻と終了時刻から１日の研究時間の算出，前回の累積時間から新たな合計研究時間を算出し，対象のセル位置に打刻を行う  

```python
#終了時の処理
def punch_out():
    global end_time,Research_time,total_time
    df = pd.read_csv(user_id + '.csv',header = None)
    timestamp = datetime.now().replace(second=0,microsecond=0)
    end_time = timestamp.strftime('%H:%M') #終了時刻
    
    '''今日の研究時間と累計研究時間の計算'''
    time1 = df.iloc[-1, 1] #開始時刻をdfから取り出し(毎回保存しないと複数人に対応できなさそうだったので)
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
```

### LINEBotに関する設定部分
この部分に先ほどコピーしたIDなどを入力する  

```python
#ここからラインボットの設定関係
app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = '#自分のCHANNEL_ACCESS_TOKEN'
YOUR_CHANNEL_SECRET = '#自分のCHANNEL_SECRET'

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)
```

### 指定のメッセージを受け取ったときの処理
ここではメッセージを受け取った際にプロフィール情報を取得している
画像のように研究開始！と研究終了！のメッセージに対して記録や返信を行うように設定している

```python
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
```

## Raspberry Piの設定
### ngrokを使用してローカルURLに外部からローカルサーバーに転送してもらう
#### [ngrok](https://ngrok.com/)にアクセスしサインイン(使ったことない人は登録をする)を行う
インターネットをポート開放して外部アクセスする方法もあるが，今回はngrokを使ってローカルサーバーを外部公開する形をとっている

#### Raspberry Piにngrokをインストールする
ラズパイのLXTerminal上で以下のコマンドを使ってzipファイルをダウンロードする
```
wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip
```
インストールしたzipファイルをunzipを使いlocal/bin/のディレクトリ下に解凍する
```
sudo unzip ngrok-stable-linux-arm.zip -d /usr/local/bin/
```
黄色で塗りつぶした部分をコピーし以下のコマンドをラズパイのターミナル上で入力する
![スクリーンショット 2023-04-10 180014](https://user-images.githubusercontent.com/130141399/230869931-a0d067cd-d186-4c23-815d-08a7f1653c81.png)
```
ngrok authtoken コピーした部分
```
ポート5000でポート公開をする
```
ngrok http 5000
```  

*ここはngrokでポート開放するたびにURLが変わってしまうのでポート開放を止めるとLINEBot側の設定をし直す必要があるので注意!!  
公開するとStatusがonlineと表示される．  
黄色で塗りつぶした部分をLINEBotに紐づけするためコピーしておく
![ngrok](https://user-images.githubusercontent.com/130141399/230872542-c68b7693-cd00-40ef-a482-3621639084ab.png)

## LINEBot側のWebhook settings項目を設定する
Webhook URLの部分にURLをペーストする
![ngrok](https://user-images.githubusercontent.com/130141399/230873369-f093badd-d547-48ae-8926-3b2fef8d6ca5.png)  
*ただペーストするだけではなくngrok.io/callbackにする必要があります

### ここでLINEBotが動くかテストする
dousatest.pyをラズパイ上でrunしておく
*LINEbotの設定項目を変更する(チャンネルトークンとチャンネルシークレットの設定)  

/callbackがついてないURLをWeb検索すると
これはテストです．と表示されれば問題なく動いている

## ここまで問題なければ
kintaibot.pyをラズパイ上で動かしておき，紐づけしたLINEBotにメッセージを入力してCSVファイルが問題なく書き込まれればOK!

















