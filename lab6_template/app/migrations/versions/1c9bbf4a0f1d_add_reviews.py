"""Add reviews

Revision ID: 1c9bbf4a0f1d
Revises: 8d2f6da574a0
Create Date: 2026-05-23 03:10:00.000000

"""
from datetime import datetime, timedelta

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


# revision identifiers, used by Alembic.
revision = '1c9bbf4a0f1d'
down_revision = '8d2f6da574a0'
branch_labels = None
depends_on = None

TEST_IMAGE_ID = 'test-course-background'
TEST_COURSE_NAME = 'курс тест'
TEST_USER_LOGINS = [f'test_review_user_{i}' for i in range(1, 11)]
TEST_REVIEW_RATINGS = [5, 4, 3, 5, 2, 1, 0, 4, 5, 3]


def data_upgrades():
    """Create a test course with ten reviews."""

    connection = op.get_bind()
    now = datetime(2026, 5, 23, 12, 0, 0)

    categories = sa.sql.table(
        'categories',
        sa.sql.column('id', sa.Integer),
        sa.sql.column('name', sa.String),
    )
    users = sa.sql.table(
        'users',
        sa.sql.column('id', sa.Integer),
        sa.sql.column('first_name', sa.String),
        sa.sql.column('last_name', sa.String),
        sa.sql.column('middle_name', sa.String),
        sa.sql.column('login', sa.String),
        sa.sql.column('password_hash', sa.String),
        sa.sql.column('created_at', sa.DateTime),
    )
    images = sa.sql.table(
        'images',
        sa.sql.column('id', sa.String),
        sa.sql.column('file_name', sa.String),
        sa.sql.column('mime_type', sa.String),
        sa.sql.column('md5_hash', sa.String),
        sa.sql.column('object_id', sa.Integer),
        sa.sql.column('object_type', sa.String),
        sa.sql.column('created_at', sa.DateTime),
    )
    courses = sa.sql.table(
        'courses',
        sa.sql.column('id', sa.Integer),
        sa.sql.column('name', sa.String),
        sa.sql.column('short_desc', sa.Text),
        sa.sql.column('full_desc', sa.Text),
        sa.sql.column('rating_sum', sa.Integer),
        sa.sql.column('rating_num', sa.Integer),
        sa.sql.column('category_id', sa.Integer),
        sa.sql.column('author_id', sa.Integer),
        sa.sql.column('background_image_id', sa.String),
        sa.sql.column('created_at', sa.DateTime),
    )
    reviews = sa.sql.table(
        'reviews',
        sa.sql.column('rating', sa.Integer),
        sa.sql.column('text', sa.Text),
        sa.sql.column('created_at', sa.DateTime),
        sa.sql.column('course_id', sa.Integer),
        sa.sql.column('user_id', sa.Integer),
    )

    category_id = connection.execute(
        sa.select(categories.c.id).where(categories.c.name == 'Программирование')
    ).scalar()

    password_hash = generate_password_hash('qwerty')
    for index, login in enumerate(TEST_USER_LOGINS, start=1):
        user_id = connection.execute(
            sa.select(users.c.id).where(users.c.login == login)
        ).scalar()
        if user_id is None:
            connection.execute(users.insert().values(
                first_name=f'Пользователь {index}',
                last_name='Тестовый',
                middle_name=None,
                login=login,
                password_hash=password_hash,
                created_at=now - timedelta(days=20 - index),
            ))

    author_id = connection.execute(
        sa.select(users.c.id).where(users.c.login == TEST_USER_LOGINS[0])
    ).scalar()

    if connection.execute(sa.select(images.c.id).where(images.c.id == TEST_IMAGE_ID)).scalar() is None:
        connection.execute(images.insert().values(
            id=TEST_IMAGE_ID,
            file_name='test-course.jpg',
            mime_type='image/jpeg',
            md5_hash='test-course-background-md5',
            object_id=None,
            object_type=None,
            created_at=now,
        ))

    course_id = connection.execute(
        sa.select(courses.c.id).where(courses.c.name == TEST_COURSE_NAME)
    ).scalar()
    if course_id is None:
        connection.execute(courses.insert().values(
            name=TEST_COURSE_NAME,
            short_desc='Тестовый курс для проверки отзывов и рейтинга.',
            full_desc=('Этот курс создан миграцией автоматически. '
                       'Он нужен, чтобы сразу проверить отображение последних отзывов, '
                       'страницу всех отзывов, сортировку и пагинацию.'),
            rating_sum=sum(TEST_REVIEW_RATINGS),
            rating_num=len(TEST_REVIEW_RATINGS),
            category_id=category_id,
            author_id=author_id,
            background_image_id=TEST_IMAGE_ID,
            created_at=now,
        ))
        course_id = connection.execute(
            sa.select(courses.c.id).where(courses.c.name == TEST_COURSE_NAME)
        ).scalar()

    review_rows = []
    for index, (login, rating) in enumerate(zip(TEST_USER_LOGINS, TEST_REVIEW_RATINGS), start=1):
        user_id = connection.execute(
            sa.select(users.c.id).where(users.c.login == login)
        ).scalar()
        review_rows.append({
            'rating': rating,
            'text': f'Тестовый отзыв #{index}: оценка {rating}.',
            'created_at': now - timedelta(hours=index * 3),
            'course_id': course_id,
            'user_id': user_id,
        })
    op.bulk_insert(reviews, review_rows)


def data_downgrades():
    """Remove test data created by this migration."""

    connection = op.get_bind()
    users = sa.sql.table('users', sa.sql.column('id', sa.Integer), sa.sql.column('login', sa.String))
    images = sa.sql.table('images', sa.sql.column('id', sa.String))
    courses = sa.sql.table('courses', sa.sql.column('id', sa.Integer), sa.sql.column('name', sa.String))
    reviews = sa.sql.table('reviews', sa.sql.column('course_id', sa.Integer))

    course_id = connection.execute(
        sa.select(courses.c.id).where(courses.c.name == TEST_COURSE_NAME)
    ).scalar()
    if course_id is not None:
        connection.execute(reviews.delete().where(reviews.c.course_id == course_id))
        connection.execute(courses.delete().where(courses.c.id == course_id))

    connection.execute(images.delete().where(images.c.id == TEST_IMAGE_ID))
    connection.execute(users.delete().where(users.c.login.in_(TEST_USER_LOGINS)))


def upgrade():
    op.create_table('reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.CheckConstraint('rating >= 0 AND rating <= 5', name=op.f('ck_reviews_rating_between_0_and_5')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_reviews_course_id_courses')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reviews_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reviews')),
    sa.UniqueConstraint('course_id', 'user_id', name=op.f('uq_reviews_course_id_user_id'))
    )
    data_upgrades()


def downgrade():
    data_downgrades()
    op.drop_table('reviews')
