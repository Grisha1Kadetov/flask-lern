import os
import random
import re
from datetime import datetime

from faker import Faker
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker, joinedload
from werkzeug.security import check_password_hash, generate_password_hash

fake = Faker()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lab-secret-key'
application = app

DATABASE_URL = 'postgresql+psycopg2://flask_lern:flask_lern@localhost:5432/flask_lern'
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к запрашиваемой странице необходимо пройти процедуру аутентификации.'
login_manager.login_message_category = 'warning'


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)


class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    login = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    last_name = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    role = relationship('Role')

    @property
    def full_name(self):
        return ' '.join(part for part in [self.last_name, self.first_name, self.middle_name] if part)


@login_manager.user_loader
def load_user(user_id):
    db = SessionLocal()
    return db.query(User).get(int(user_id))


@app.teardown_appcontext
def shutdown_session(exception=None):
    SessionLocal.remove()


@app.before_first_request
def prepare_database():
    init_db()


def init_db():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    try:
        admin_role = db.query(Role).filter_by(name='Администратор').first()
        if admin_role is None:
            admin_role = Role(
                name='Администратор',
                description='Пользователь с полным доступом.'
            )
            db.add(admin_role)

        user_role = db.query(Role).filter_by(name='Пользователь').first()
        if user_role is None:
            user_role = Role(
                name='Пользователь',
                description='Обычная роль.'
            )
            db.add(user_role)

        if db.query(User).filter_by(login='admin').first() is None:
            db.add(User(
                login='admin',
                password_hash=generate_password_hash('qwerty'),
                last_name='Иванов',
                first_name='Иван',
                middle_name='Иванович',
                role=admin_role
            ))

        if db.query(User).filter_by(login='user').first() is None:
            db.add(User(
                login='user',
                password_hash=generate_password_hash('qwerty'),
                last_name='Петров',
                first_name='Пётр',
                middle_name='Петрович',
                role=user_role
            ))

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
              '2d2ab7df-cdbc-48a8-a936-35bba702def5',
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
              'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for i in range(random.randint(1, 3)):
        comment = {'author': fake.name(), 'text': fake.text()}
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


def validate_login(login):
    if not login:
        return 'Поле не может быть пустым.'
    if len(login) < 5:
        return 'Логин должен быть не менее 5 символов.'
    if not re.fullmatch(r'[A-Za-z0-9]+', login):
        return 'Логин должен состоять только из латинских букв и цифр.'
    return None


def is_allowed_password_letter(char):
    lower_char = char.lower()
    return 'a' <= lower_char <= 'z' or 'а' <= lower_char <= 'я' or lower_char == 'ё'


def validate_password(password):
    allowed_specials = set('~!?@#$%^&*_-+()[]{}></\\|"\'.,:;')

    if not password:
        return 'Поле не может быть пустым.'
    if len(password) < 8:
        return 'Пароль должен быть не менее 8 символов.'
    if len(password) > 128:
        return 'Пароль должен быть не более 128 символов.'
    if any(char.isspace() for char in password):
        return 'Пароль не должен содержать пробелы.'
    if not any(char.isupper() for char in password if char.isalpha()):
        return 'Пароль должен содержать как минимум одну заглавную букву.'
    if not any(char.islower() for char in password if char.isalpha()):
        return 'Пароль должен содержать как минимум одну строчную букву.'
    if not any(char in '0123456789' for char in password):
        return 'Пароль должен содержать как минимум одну цифру.'

    for char in password:
        if char in '0123456789' or char in allowed_specials or is_allowed_password_letter(char):
            continue
        return 'Пароль содержит недопустимые символы.'

    return None


def validate_user_form(form_data, include_login_password=True):
    errors = {}

    if include_login_password:
        login_error = validate_login(form_data.get('login', '').strip())
        password_error = validate_password(form_data.get('password', ''))

        if login_error:
            errors['login'] = login_error
        if password_error:
            errors['password'] = password_error

    if not form_data.get('last_name', '').strip():
        errors['last_name'] = 'Поле не может быть пустым.'
    if not form_data.get('first_name', '').strip():
        errors['first_name'] = 'Поле не может быть пустым.'

    return errors


def get_roles():
    db = SessionLocal()
    return db.query(Role).order_by(Role.name).all()


def get_user_or_404(user_id):
    db = SessionLocal()
    user = db.query(User).options(joinedload(User.role)).get(user_id)
    if user is None:
        abort(404)
    return user


def fill_user_from_form(user, form_data, include_login_password=True):
    if include_login_password:
        user.login = form_data.get('login', '').strip()
        user.password_hash = generate_password_hash(form_data.get('password', ''))

    user.last_name = form_data.get('last_name', '').strip()
    user.first_name = form_data.get('first_name', '').strip()
    user.middle_name = form_data.get('middle_name', '').strip() or None
    role_id = form_data.get('role_id')
    user.role_id = int(role_id) if role_id else None


@app.route('/')
def index():
    db = SessionLocal()
    users = db.query(User).options(joinedload(User.role)).order_by(User.id).all()
    return render_template('index.html', title='Пользователи', users=users)


@app.route('/users/<int:user_id>')
def user_view(user_id):
    user = get_user_or_404(user_id)
    return render_template('user_view.html', title='Просмотр пользователя', user=user)


@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def user_create():
    form_data = request.form.to_dict() if request.method == 'POST' else {}
    errors = {}

    if request.method == 'POST':
        errors = validate_user_form(form_data)

        if not errors:
            db = SessionLocal()
            user = User()
            fill_user_from_form(user, form_data)
            db.add(user)

            try:
                db.commit()
                flash('Пользователь успешно создан.', 'success')
                return redirect(url_for('index'))
            except IntegrityError:
                db.rollback()
                errors['login'] = 'Пользователь с таким логином уже существует.'
                flash('Не удалось создать пользователя. Исправьте ошибки в форме.', 'danger')
            except SQLAlchemyError:
                db.rollback()
                flash('При сохранении пользователя произошла ошибка.', 'danger')
        else:
            flash('Не удалось создать пользователя. Исправьте ошибки в форме.', 'danger')

    return render_template(
        'user_create.html',
        title='Создание пользователя',
        form_data=form_data,
        errors=errors,
        roles=get_roles()
    )


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = get_user_or_404(user_id)
    form_data = {
        'last_name': user.last_name or '',
        'first_name': user.first_name or '',
        'middle_name': user.middle_name or '',
        'role_id': str(user.role_id or '')
    }
    errors = {}

    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_user_form(form_data, include_login_password=False)

        if not errors:
            db = SessionLocal()
            user = db.query(User).get(user_id)
            fill_user_from_form(user, form_data, include_login_password=False)

            try:
                db.commit()
                flash('Пользователь успешно обновлён.', 'success')
                return redirect(url_for('index'))
            except SQLAlchemyError:
                db.rollback()
                flash('При обновлении пользователя произошла ошибка.', 'danger')
        else:
            flash('Не удалось обновить пользователя. Исправьте ошибки в форме.', 'danger')

    return render_template(
        'user_edit.html',
        title='Редактирование пользователя',
        user=user,
        form_data=form_data,
        errors=errors,
        roles=get_roles()
    )


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    db = SessionLocal()
    user = db.query(User).get(user_id)

    if user is None:
        flash('Пользователь не найден.', 'danger')
        return redirect(url_for('index'))

    delete_current_user = user.id == current_user.id

    try:
        db.delete(user)
        db.commit()
        if delete_current_user:
            logout_user()
            flash('Ваша учётная запись успешно удалена. Выполнен выход из системы.', 'success')
        else:
            flash('Пользователь успешно удалён.', 'success')
    except SQLAlchemyError:
        db.rollback()
        flash('При удалении пользователя произошла ошибка.', 'danger')

    return redirect(url_for('index'))


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
        db = SessionLocal()
        user = db.query(User).filter_by(login=login_value).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page and next_page.startswith('/') else url_for('index'))

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


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}

    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        repeat_password = request.form.get('repeat_password', '')

        if not check_password_hash(current_user.password_hash, old_password):
            errors['old_password'] = 'Старый пароль введён неверно.'

        password_error = validate_password(new_password)
        if password_error:
            errors['new_password'] = password_error

        if new_password != repeat_password:
            errors['repeat_password'] = 'Новые пароли не совпадают.'

        if not errors:
            db = SessionLocal()
            user = db.query(User).get(current_user.id)
            user.password_hash = generate_password_hash(new_password)

            try:
                db.commit()
                flash('Пароль успешно изменён.', 'success')
                return redirect(url_for('index'))
            except SQLAlchemyError:
                db.rollback()
                flash('При изменении пароля произошла ошибка.', 'danger')
        else:
            flash('Не удалось изменить пароль. Исправьте ошибки в форме.', 'danger')

    return render_template('change_password.html', title='Изменить пароль', errors=errors)


@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')
