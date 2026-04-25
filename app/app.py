import random
import re
from flask import Flask, render_template, request
from faker import Faker

fake = Faker()

app = Flask(__name__)
application = app

images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for i in range(random.randint(1, 3)):
        comment = { 'author': fake.name(), 'text': fake.text() }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': 'Заголовок поста',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

posts_list = sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

def validate_phone(phone):
    allowed_symbols = re.compile(r'^[0-9\s().+\-]*$')

    if not allowed_symbols.match(phone):
        return 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.', None

    digits = re.sub(r'\D', '', phone)
    phone_start = phone.strip()
    required_length = 11 if phone_start.startswith('+7') or phone_start.startswith('8') else 10

    if len(digits) != required_length:
        return 'Недопустимый ввод. Неверное количество цифр.', None

    if required_length == 11:
        digits = digits[1:]

    formatted_phone = f'8-{digits[:3]}-{digits[3:6]}-{digits[6:8]}-{digits[8:10]}'
    return None, formatted_phone

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list)

@app.route('/posts/<int:index>')
def post(index):
    p = posts_list[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/request-info', methods=['GET', 'POST'])
def request_info():
    return render_template(
        'request_info.html',
        title='Данные запроса',
        url_params=request.args.items(multi=True),
        headers=request.headers.items(),
        cookies=request.cookies.items(),
        form_params=request.form.items(multi=True)
    )

@app.route('/phone', methods=['GET', 'POST'])
def phone():
    phone_number = ''
    error = None
    formatted_phone = None

    if request.method == 'POST':
        phone_number = request.form.get('phone', '')
        error, formatted_phone = validate_phone(phone_number)

    return render_template(
        'phone.html',
        title='Проверка телефона',
        phone_number=phone_number,
        error=error,
        formatted_phone=formatted_phone
    )

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')
