from flask import Flask, request, Response
import json
import requests
import jieba.posseg as pseg

app = Flask(__name__)

label_map = {
    '0': '闲聊',
    '1': '政务问答',
    '2': '政务常见问题'
}

module_map = {
    '其他': 0,
    '天气': 1
}

module_state = {
     'restart': 0,
     'weather_going': {'时间': 1,
                       '地点': 2
               }
}
ind = module_state['restart']

def get_pos(query):
    words = pseg.cut(query)
    # word_r = []
    flag_r = []
    for word, flag in words:
        # word_r.append(word)
        flag_r.append(flag)
    return flag_r

def get_answer(query, module_num):
    res = {}
    res['query'] = query
    global ind
    try:
        if not module_num:
            kb = requests.get(f'http://192.168.1.28:9639/kbqa/demo?query={query}').json()["data"]["summary"]
            if kb.find('没有') == -1:
                res['intent'] = 'KBQA'
                res['query'] = query
                res['message'] = kb
                res['status'] = 'ok'
                return res
            subway = requests.post('http://192.168.1.29:8765/predictions/crosswoz_nlu', {'data': query}).json()
            res['answer'] = subway
            res['intent'] = 'subway'
            res['status'] = 'ok'
            return res
            intent = requests.post('http://192.168.1.29:6787/intent/', json.dumps({'data': query})).json()[0]
            res['intent'] = label_map[intent]
            if intent == '0':
                res.update(requests.get(f'http://192.168.1.28:6679/api?text={query}').json())
            elif intent == '1':
                res.update(requests.get(f'http://192.168.1.28:4633/api?text={query}').json())
            else:
                res.update(requests.get(f'http://192.168.1.29:1234/api?text={query}').json())
            return res
        else:
            wether = requests.post(url='http://192.168.1.28:5005/webhooks/rest/webhook',
                                   data=json.dumps({"sender": "0001", "message": query})).json()
            if len(wether) == 2:
                res['answer'] = wether[1]['text']
                res['intent'] = 'whether'
                # res['status'] = 'ok'
                res['tag'] = '智源'
                res['score'] = 100
                ind = module_state['restart']
                return res
            else:
                res['answer'] = wether[0]['text']
                res['intent'] = 'whether'
                # res['status'] = 'go on'
                res['tag'] = '智源'
                if res['answer'] == '什么时候？':
                    res['score'] = 100
                    ind = module_state['weather_going']['时间']
                elif res['answer'] == '在哪里？':
                    res['score'] = 100
                    ind = module_state['weather_going']['地点']
                else:
                    res['score'] = 30 # 非天气领域
                    ind = module_state['restart']
                return res
    except Exception as e:
        print(e)

def output_answer(data):
    if not ind:
        if '天气' not in query:
            module_num = module_map['其他']
            answer = get_answer(data, module_num)
        else:
            module_num = module_map['天气']
            answer = get_answer(data, module_num)
    else:
        pos = get_pos(data)
        if ind == 1 and 't' in pos:
            if 'n' in pos or 'a' in pos:
                module_num = module_map['其他']
                answer = get_answer(data, module_num)
            else:
                module_num = module_map['天气']
                answer = get_answer(data, module_num)
        elif ind == 2 and 'ns' in pos:
            if 'n' in pos or 'a' in pos:
                module_num = module_map['其他']
                answer = get_answer(data, module_num)
            else:
                module_num = module_map['天气']
                answer = get_answer(data, module_num)
        else:
            module_num = module_map['其他']
            answer = get_answer(data, module_num)

    return answer

@app.route('/dia/', methods=['POST', 'GET'])
def model():
    input_json = request.get_json(force=True)
    data = input_json['data']
    answer = output_answer(data)
    return Response(json.dumps(answer, ensure_ascii=False),
                    mimetype='application/json; charset=utf-8')

@app.route("/api")
def model_1():
    data = request.args.get('text', '')
    print(data)
    answer = output_answer(data)
    return Response(json.dumps(answer, ensure_ascii=False),
                    mimetype='application/json; charset=utf-8')

if __name__ == '__main__':
    app.run(host ='0.0.0.0',port=6788,threaded=True)
    # query = '新疆的疫情什么状态了'
    # ans = output_answer(query)
    # print(ans)
