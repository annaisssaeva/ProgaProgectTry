#импортим все нужные модули
import sqlite3
import random
from flask import Flask, url_for, render_template, request, redirect
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
import requests
from bs4 import BeautifulSoup
import re
from fake_useragent import UserAgent


#создаем базу данных
db = SQLAlchemy()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///so.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.app = app
db.init_app(app)

#создаем класс для таблицы юзеров – там будут столбцы с
#айди и возрастом
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    #gender = db.Column(db.Text)
    your_word = db.Column(db.Text)
    age = db.Column(db.Integer)

#в таблице с ответами будет айди юзера и песня которую ему выдадим
class Songs(db.Model):
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    song_name = db.Column(db.Text)



@app.before_first_request
def create_tables():
    db.create_all()

#при переходе на страницу /questions показываем страницу questions.html
@app.route('/questions')
def question_page():
    return render_template(
        'questions.html'
    )

#при переходе на начальную страницу отображаем index.html
@app.route('/index')
def index_page():
   return render_template('index.html')


#при переходе просто на сайт стразу переводим на /index
@app.route('/')
def zero_page():
    return redirect(url_for('index_page'))



#после отправки ответов присваиваем юзеру его ответы в анкете
#про возраст и слово которое он нам даст
@app.route('/process', methods=['get'])
def answer_process():
    if not request.args:
        return redirect(url_for('question_page'))
    id = random.randrange(1000000000)
    your_word = request.args.get('your_word')
    age = request.args.get('age')
    user = User(
        id = id,
        your_word=your_word,
        age=int(age)
    )
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    #теперь проходимся словом по песням в базе данных и находим ту, в которой
    #оно есть

    con = sqlite3.connect('songs.db')
    cur = con.cursor()

    # с помощью запрса находим все айди и берем последний
    # до него мы будем потом проходить по циклу
    num_of_songs = """
    SELECT song_id
    FROM songs
    """
    cur.execute(num_of_songs)
    last_id = str(cur.fetchall()[-1])[1:-2]
    #на случай, если your_word нет в списке ключевых слов
    #задаем переменную заранее
    name = "sorry, there is no song with this word in our database yet:("

    numberr = 1
    while numberr <= int(last_id):
        # запрос на ключевые слова по айди
        keyw_query = f"""
        SELECT keywords 
        FROM songs 
        WHERE song_id = {numberr}
        """
        cur.execute(keyw_query)
        keyw = str(cur.fetchone())[1:-1]
        if your_word in keyw:
            # запрос на название песни по айди
            name_query = f"""
            SELECT name 
            FROM songs 
            WHERE song_id = {numberr}
            """
            cur.execute(name_query)
            name = str(cur.fetchone())[2:-3]
            print(name)
            numberr = 100000000000
        else:
            numberr += 1

    answer = Songs(id=user.id, song_name=name)
    db.session.add(answer)
    db.session.commit()
    idd = user.id
    print(idd)

    if name == "sorry, there is no song with this word in our database yet:(":
        return redirect(url_for('sorry_page'))
    else:
        return redirect(url_for('thanks_page', perem=idd))


@app.route('/sorry')
def sorry_page():
   return render_template('sorry.html')


@app.route('/thanks/<perem>')
def thanks_page(perem):
    song = db.session.query(Songs.song_name).filter_by(id=perem).first()

    # ставим плюсы в пробелах названия, чтобы
    # потом вставить в запрос
    zapros = str("+".join(str(song).split()))
    # с помощью BeautifulSoup получаем код страницы
    session = requests.session()
    ua = UserAgent(verify_ssl=False)
    headers = {'User-Agent': ua.random}
    url = f"https://google.com/search?q={zapros}+video"
    req = session.get(url, headers={'User-Agent': ua.random})
    page = req.text
    soup = BeautifulSoup(page, 'html.parser')
    code = soup.prettify()
    # создаем список для всех ссылок со страницы
    list_of_links = []

    # ищем ссылки на ютуб и кладем в переменную первую из них (в большинстве
    # случаев это ссылка на официальный клип)
    if "www.youtube.com/watch" in str(code):
        m = re.findall('https:\/\/www\.youtube[^<]*', str(code))
        list_of_links.append(m)
    main_link = list_of_links[0][1]
    print(main_link)

    return render_template(
        'thanks.html',
        song = song,
        link = main_link
    )

#на странице статистики выводим средний, минимальный
#и максимальный возраст и в зависимости от того, как люди
#отвечали на последний вопрос про лягушек выводим текст
@app.route('/stats')
def stats():
    all_info = {}
    age_stats = db.session.query(
        func.avg(User.age)
    ).one()

    if round(age_stats[0]) == 1:
        all_info['age_freq'] = "were 13 and younger"
    elif round(age_stats[0]) == 2:
        all_info['age_freq'] = "were from 14 to 20 years old"
    elif round(age_stats[0]) == 3:
        all_info['age_freq'] = "were from 21 to 30 years old"
    elif round(age_stats[0]) == 4:
        all_info['age_freq'] = "were from 31 to 45 years old"
    elif round(age_stats[0]) == 5:
        all_info['age_freq'] = "were 46 and older"

    all_info['total_count'] = User.query.count()

    return render_template('stats.html', all_info=all_info)

if __name__ == '__main__':
    app.run()