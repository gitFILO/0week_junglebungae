from pymongo import MongoClient

from flask import Flask, render_template, jsonify, request

from bs4 import BeautifulSoup

app = Flask(__name__)

client = MongoClient('mongodb://piu:tkdl7171@13.209.41.157', 27017)
db = client.dbkrafton0
lists_collection = db.lists


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/list', methods=['GET'])
def show_posts():
    posts = list(db.post.find({}, {'_id': False}).sort('time', -1))
    return jsonify({'result': 'success', 'post_list': posts})

@app.route('/post', methods=['POST'])
def post_post():
    type_receive= request.form['type_give']
    title_receive = request.form['title_give']
    dateArr_receive=request.form['dateArr_give']
    time_receive= request.form['time_give']
    place_receive=request.form['place_give']
    numberofpeople_receive= request.form['numberofpeople_give']
    numbereofpeoplenow_receive=request.form['numberofpeoplenow_give']
    post={'type':type_receive, 'title':title_receive, 'date':dateArr_receive, 'time':time_receive, 'place':place_receive, 'numberofpeople':numberofpeople_receive, 'numberofpeoplenow':numbereofpeoplenow_receive, 'writer':""}

    lists_collection.insert_one(post)

    #writer -> 유저디비 -> 지금 로그인한 사람이 참가하는 게시글 리스트에 post의 id를 저장

    return jsonify({'result':'success'})





@app.route('/api/join', methods=['POST'])
def join_post():
    title_receive = request.form['title_give']

    post = db.post.find_one({'title': title_receive})
    new_NumberofPeople = post['NumberofPeople'] + 1

    db.post.update_one({'title': title_receive}, {'$set': {'NumberOfPeople': new_NumberofPeople}})

    return jsonify({'result': 'success'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)