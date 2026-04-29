import random
import re
from flask import Flask, flash, redirect, render_template, request, session, url_for
from faker import Faker
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

fake = Faker()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lab-secret-key'
application = app

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к запрашиваемой странице необходимо пройти процедуру аутентификации.'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    def __init__(self, user_id, login, password):
        self.id = user_id
        self.login = login
        self.password = password

users = {
    'user': User('1', 'user', 'qwerty')
}

@login_manager.user_loader
def load_user(user_id):
    for user in users.values():
        if user.id == user_id:
            return user
    return None

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

@app.route('/visits')
def visits():
    session['visits'] = session.get('visits', 0) + 1
    return render_template('visits.html', title='Счётчик посещений', visits=session['visits'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        login_value = request.form.get('login', '')
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = users.get(login_value)

        if user and user.password == password:
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))

        flash('Неверно введён логин или пароль.', 'danger')

    return render_template('login.html', title='Вход')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html', title='Секретная страница')

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')
