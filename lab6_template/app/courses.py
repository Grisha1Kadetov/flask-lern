from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from models import db, Course, Category, Review, User
from tools import CoursesFilter, ImageSaver

bp = Blueprint('courses', __name__, url_prefix='/courses')

COURSE_PARAMS = [
    'author_id', 'name', 'category_id', 'short_desc', 'full_desc'
]

REVIEW_RATINGS = {
    5: 'отлично',
    4: 'хорошо',
    3: 'удовлетворительно',
    2: 'неудовлетворительно',
    1: 'плохо',
    0: 'ужасно',
}

REVIEW_SORTS = {
    'newest': 'По новизне',
    'positive': 'Сначала положительные',
    'negative': 'Сначала отрицательные',
}

def params():
    return { p: request.form.get(p) or None for p in COURSE_PARAMS }

def search_params():
    return {
        'name': request.args.get('name'),
        'category_ids': [x for x in request.args.getlist('category_ids') if x],
    }

def review_params():
    return {
        'rating': request.form.get('rating'),
        'text': request.form.get('text', '').strip(),
    }

def current_user_review(course_id):
    if not current_user.is_authenticated:
        return None
    return db.session.execute(
        db.select(Review).filter_by(course_id=course_id, user_id=current_user.id)
    ).scalar()

def ordered_reviews_query(course_id, sort):
    query = db.select(Review).filter_by(course_id=course_id)
    if sort == 'positive':
        return query.order_by(Review.rating.desc(), Review.created_at.desc())
    if sort == 'negative':
        return query.order_by(Review.rating.asc(), Review.created_at.desc())
    return query.order_by(Review.created_at.desc())

@bp.route('/')
def index():
    courses = CoursesFilter(**search_params()).perform()
    pagination = db.paginate(courses)
    courses = pagination.items
    categories = db.session.execute(db.select(Category)).scalars()
    return render_template('courses/index.html',
                           courses=courses,
                           categories=categories,
                           pagination=pagination,
                           search_params=search_params())

@bp.route('/new')
@login_required
def new():
    course = Course()
    categories = db.session.execute(db.select(Category)).scalars()
    users = db.session.execute(db.select(User)).scalars()
    return render_template('courses/new.html',
                           categories=categories,
                           users=users,
                           course=course)

@bp.route('/create', methods=['POST'])
@login_required
def create():
    f = request.files.get('background_img')
    img = None
    course = Course()
    try:
        if f and f.filename:
            img = ImageSaver(f).save()

        image_id = img.id if img else None
        course = Course(**params(), background_image_id=image_id)
        db.session.add(course)
        db.session.commit()
    except IntegrityError as err:
        flash(f'Возникла ошибка при записи данных в БД. Проверьте корректность введённых данных. ({err})', 'danger')
        db.session.rollback()
        categories = db.session.execute(db.select(Category)).scalars()
        users = db.session.execute(db.select(User)).scalars()
        return render_template('courses/new.html',
                            categories=categories,
                            users=users,
                            course=course)

    flash(f'Курс {course.name} был успешно добавлен!', 'success')

    return redirect(url_for('courses.index'))

@bp.route('/<int:course_id>')
def show(course_id):
    course = db.get_or_404(Course, course_id)
    latest_reviews = db.session.execute(
        ordered_reviews_query(course.id, 'newest').limit(5)
    ).scalars().all()
    return render_template('courses/show.html',
                           course=course,
                           latest_reviews=latest_reviews,
                           user_review=current_user_review(course.id),
                           review_ratings=REVIEW_RATINGS)

@bp.route('/<int:course_id>/reviews')
def reviews(course_id):
    course = db.get_or_404(Course, course_id)
    sort = request.args.get('sort', 'newest')
    if sort not in REVIEW_SORTS:
        sort = 'newest'
    pagination = db.paginate(ordered_reviews_query(course.id, sort), per_page=5)
    return render_template('courses/reviews.html',
                           course=course,
                           reviews=pagination.items,
                           pagination=pagination,
                           sort=sort,
                           review_sorts=REVIEW_SORTS,
                           review_ratings=REVIEW_RATINGS,
                           user_review=current_user_review(course.id))

@bp.route('/<int:course_id>/reviews/create', methods=['POST'])
@login_required
def create_review(course_id):
    course = db.get_or_404(Course, course_id)
    user_review = current_user_review(course.id)
    if user_review is not None:
        flash('Вы уже оставили отзыв к этому курсу.', 'warning')
        return redirect(request.referrer or url_for('courses.show', course_id=course.id))

    params = review_params()
    try:
        rating = int(params['rating'])
    except (TypeError, ValueError):
        rating = None

    if rating not in REVIEW_RATINGS or not params['text']:
        flash('Укажите оценку и текст отзыва.', 'danger')
        return redirect(request.referrer or url_for('courses.show', course_id=course.id))

    review = Review(
        rating=rating,
        text=params['text'],
        course_id=course.id,
        user_id=current_user.id,
    )
    course.rating_sum += rating
    course.rating_num += 1
    db.session.add(review)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Не удалось сохранить отзыв. Проверьте, что отзыв ещё не был создан.', 'danger')
    else:
        flash('Отзыв успешно добавлен.', 'success')

    return redirect(request.referrer or url_for('courses.show', course_id=course.id))
