from flask import Flask, render_template, jsonify, request,session,redirect
import requests
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from flask_session import Session
import pathlib
from cachecontrol import CacheControl
import cachecontrol
import google.auth

from flask import abort
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google_auth_oauthlib.flow import Flow


from urllib.parse import quote_plus
from bson import ObjectId
from flask.json.provider import JSONProvider

import json
import sys

app = Flask(__name__)
app.secret_key = "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"

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
  
GOOGLE_CLIENT_ID = "685606626855-5adj5rf3jdmru2dlt884tajf6r9qsnob.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")
flow= Flow.from_client_secrets_file(client_secrets_file=client_secrets_file,
                                    scopes=["https://www.googleapis.com/auth/userinfo.profile","https://www.googleapis.com/auth/userinfo.email",
                                            "openid"],
                                    redirect_uri="http://filog.shop/callback")

#client = MongoClient('mongodb://piu:tkdl7171@13.209.41.157', 27017)
client = MongoClient('localhost', 27017)
db = client.jungle_mini
users_collection = db.users
post_collection = db.post
bcrypt = Bcrypt(app)

# ObjectId jsonify시 처리
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


class CustomJSONProvider(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

app.json = CustomJSONProvider(app)




def login_is_required(function):
    def wrapper(*args, **kwawrgs):
        if "google_id" not in session:
            return abort(401)
        else:
            return function()
    return wrapper


@app.route("/google_login")
def google_login():
    autorization_url , state = flow.authorization_url()
    session["state"] = state
    return redirect(autorization_url)
 
@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response= request.url)

    if not session["state"] == request.args["state"]:
        abort(500)
    
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    #print(cached_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token= credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    print(id_info)
    session["email"] = id_info.get("email")
    session["name"] = id_info.get("name")
    print(session["email"])
    go_email = users_collection.find_one({'e-mail': session["email"]})
    if go_email:
        return redirect("/list")
    else:
        users_collection.insert_one({'e-mail': session["email"], 'name':session["name"],'password': "1234" ,'my-posts':[]})
    return redirect("/list")
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/protected_area")
@login_is_required
def protected_area():
    return "proteced!"


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    print(email,password)
    user = users_collection.find_one({'e-mail': email})
    
    if user:
        hashed_password = user['password']
        session["email"] = email
        if bcrypt.check_password_hash(hashed_password, password):
            session["name"] = user["name"]
            return jsonify({'result': 'success', 'user_email': email})
    
    return jsonify({'result': 'fail', 'message': '로그인 실패'})

@app.route("/")
def index():
  # check if the users exist or not
    if not session.get("email"):
        # if not there in the session then redirect to the login page
        return render_template("login.html")
        #return redirect("/login")
    print(session['email'])
    return render_template('index.html')


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        email = data['email']
        password = data['password']
        name=data['name']

        # 비밀번호 해싱
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = {
            'name': name,
            'e-mail': email,
            'password': hashed_password,
            'my-posts': []
        }

        existing_user = users_collection.find_one({'e-mail': email})
    
        if existing_user:
            print("저장실패")
            return jsonify({'result':'fail', 'message': '이미 존재하는 이메일입니다.'})

        users_collection.insert_one(new_user)
        print("저장완료")
        return jsonify({'result':'success','message': '회원가입이 성공적으로 완료되었습니다.'})
    
    return render_template('register.html')

@app.route('/list')
def userList():
     # 세션에서 사용자 이름 가져오기
     user_name = session.get("name")
     print(user_name)
     # 사용자 이름이 있을 경우 환영 메시지 생성
     if user_name:
         greeting_message = f"{user_name} 님 안녕하세요!"
     else:
         greeting_message = "로그인이 필요합니다."

     return render_template('index.html', greeting_message=greeting_message)

 # API로 라우팅 작성
 
 # 홈 화면 html 렌더링
#@app.route('/')
#def home():
#   return render_template('index.html')

# 게시글 작성 페이지
@app.route('/upload')
def upload():
    return render_template('upload.html')
    
# DB에서 카테고리별 게시글 필터링
@app.route('/jungbun/list', methods=['GET'])
def filterPost():
    category = request.args.get('category')
    print('카테고리 데이터')
    print(category)
    posts= list(post_collection.find({'category': category}))
    print("/jungbun/list' - get API network done")

    user_email = session['email']
    name = users_collection.find_one({'e-mail': user_email})['name']
    return jsonify({'result': 'success', 'posts': posts, 'user' : name})

# 내 참가 목록 확인
@app.route('/jungbun/my-activity', methods=['GET'])
def show_myActivity():
    
    user_email = session['email']
    name = users_collection.find_one({'e-mail': user_email})['name']
    posts = users_collection.find_one({'e-mail': user_email})['my-posts']
    print(posts)
    print("/jungbun/my-activity' - get API network done")
    return jsonify({'result': 'success', 'posts': posts, 'user' : name})

# 게시글 DB에 올리기
@app.route('/jungbun/write-post', methods=['POST'])
def write_post():
    
    print("/jungbun/write-post API Called")
    
    post = {
    'category': request.form['category'],
    'title': request.form['title'],
    'date': request.form['date'],
    'time': request.form['time'],
    'writer': request.form['writer'],
    'place': request.form['place'],
    'max_people_num': request.form['max_people_num'],
    'participant_num': '1',
    'participants': [request.form['writer']],
    'status': '참가하기'
    }

    post_collection.insert_one(post)

    # 유저 db에 추가하기
    # 추후에 session으로 바꾸기
    user_email = session["email"]
    posts = users_collection.find_one({'e-mail': user_email})['my-posts']
    posts.append(post)
    users_collection.update_one({'e-mail': user_email}, {'$set': {'my-posts': posts}})

    return jsonify({'result':'success'})

# 특정 게시글에 참가하기 누르기
@app.route('/jungbun/participate', methods=['POST'])
def participate():
    
    print("/jungbun/participate Called")
    # 로그인된 유저 이름 찾기
    user_email = session['email']
    data = users_collection.find_one({'e-mail': user_email})
    user_name = data['name']
    print(user_name)
    post_id = request.form.get('post_id')
    post = post_collection.find_one({'_id': ObjectId(post_id)})
    print(post)
    temp_num = int(post['participant_num'])
    max_num = int(post['max_people_num'])
    new_participant_num = temp_num + 1
    
    original_participants = post['participants']

       # 참가자목록에 유저가 있으면 그냥 return
    if user_name in original_participants:
        print("이미 참가자 목록에 있어요")
        return jsonify({'result': 'success'})
    
    original_participants.append(user_name)
    
    if new_participant_num == max_num:
        post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'status': '모집완료'}})
    
    a = str(new_participant_num)

    post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'participant_num': a}})
    post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'participants': original_participants}})

    # 참가를 확정한 게시글 (post)를 데이터에 넣고 유저 컬렉션의 my-post 필드를 업데이트
    my_post = data['my-posts']
    my_post.append(post)
    users_collection.update_one({'e-mail': user_email}, {'$set': {'my-posts': my_post}})

    return jsonify({'result': 'success'})

@app.route('/jungbun/deletePost', methods=['POST'])
def delete_post():
    # 클라이언트에서 전달한 post_id 가져오기
    post_id = request.form.get('post_id')
    print("넘어온 postid는 다음과 같다")
    post_id_str = str(post_id)
    want_delete_post = post_collection.find_one({'_id': ObjectId(post_id)})

    joined_users = want_delete_post['participants']
    print(joined_users)
    for username in joined_users:
        user = users_collection.find_one({'name' :username})
        print(post_id_str)
        for post in user['my-posts']:
            print(str(post.get('_id')))
            if str(post.get('_id')) == post_id_str:
                print(user['my-posts'])
                user['my-posts'].remove(post)
                print("removed!")
                print(user['my-posts'])
                users_collection.update_one({'name': username}, {'$set': {'my-posts': user['my-posts']}})

    post_collection.delete_one({'_id': ObjectId(post_id)})
    

    # post_id를 사용하여 게시물 삭제 로직을 구현합니다.
    # 여기에서는 간단한 예제로 성공으로 가정합니다.
    # 실제로는 데이터베이스에서 해당 게시물을 삭제하고 성공 또는 실패 여부를 반환해야 합니다.

    # 삭제 성공 시
    response = {'result': 'success'}
    
    # 삭제 실패 시
    # response = {'result': 'failure'}

    return jsonify(response)


# 특정 게시글에 참가하기 취소
@app.route('/jungbun/cancel-participation', methods=['POST'])
def cancel_participation():
    print("/jungbun/cancel-participation")
    # 로그인된 유저 이름 찾기
    user_email = session['email']
    data = users_collection.find_one({'e-mail': user_email})
    user_name = data['name']
    
    post_id = request.form.get('post_id')
    post = post_collection.find_one({'_id': ObjectId(post_id)})

    temp_num = int(post['participant_num'])
    status = post['status']
    new_participant_num = temp_num - 1
    
    original_participants = post['participants']
    original_participants.remove(user_name)
    # 모집완료시, 모집중으로 상태변경
    if status == '모집완료':
        post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'status': '모집중'}})
        
        
    # 0명이 된 경우, 게시글 db에서 삭제하기
    if new_participant_num == 0:
        post_collection.delete_one({'_id': ObjectId(post_id)})

    new_num = str(new_participant_num)
    post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'participant_num': new_num}})
    post_collection.update_one({'_id': ObjectId(post_id)}, {'$set': {'participants': original_participants}})

    # 참가를 취소한 게시글 (post)를 데이터에 빼고 유저 컬렉션의 my-post 필드를 업데이트
    my_post = data['my-posts']
    
# 문자열로 변환
    post_id_str = str(post_id)

    for post in my_post:
        if str(post.get('_id')) == post_id_str:
            print("same!")
            my_post.remove(post)
            break

    print("삭제 후 my_post")
    print(my_post)
    users_collection.update_one({'e-mail': user_email}, {'$set': {'my-posts': my_post}})

    return jsonify({'result': 'success'})



if __name__ == "__main__":
    app.run('0.0.0.0', port=5001, debug=True)
