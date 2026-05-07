import csv
from io import StringIO

from flask import Blueprint, Response, render_template, request
from flask_login import current_user
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload

from app import SessionLocal, User, VisitLog, can, check_rights, is_admin

reports_bp = Blueprint('reports', __name__, url_prefix='/visit-logs')


def visitor_name(user):
    return user.full_name if user else 'Неаутентифицированный пользователь'


def visit_logs_query():
    db = SessionLocal()
    query = db.query(VisitLog).options(joinedload(VisitLog.user)).order_by(VisitLog.created_at.desc())

    if not is_admin():
        query = query.filter(VisitLog.user_id == current_user.id)

    return query


def page_report_rows():
    db = SessionLocal()
    return (
        db.query(VisitLog.path, func.count(VisitLog.id).label('visits_count'))
        .group_by(VisitLog.path)
        .order_by(desc('visits_count'))
        .all()
    )


def user_report_rows():
    db = SessionLocal()
    rows = (
        db.query(VisitLog.user_id, func.count(VisitLog.id).label('visits_count'))
        .group_by(VisitLog.user_id)
        .order_by(desc('visits_count'))
        .all()
    )
    user_ids = [row.user_id for row in rows if row.user_id is not None]
    users = {}

    if user_ids:
        users = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()}

    return [(visitor_name(users.get(row.user_id)), row.visits_count) for row in rows]


def csv_response(filename, headers, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@reports_bp.route('/')
@check_rights('view_visit_logs')
def visit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    query = visit_logs_query()
    total = query.count()
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = min(max(page, 1), total_pages)
    logs = query.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        'reports/visit_logs.html',
        title='Журнал посещений',
        logs=logs,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        can_view_reports=can('view_visit_reports')
    )


@reports_bp.route('/pages')
@check_rights('view_visit_reports')
def pages_report():
    return render_template(
        'reports/pages_report.html',
        title='Отчёт по страницам',
        rows=page_report_rows()
    )


@reports_bp.route('/pages/export.csv')
@check_rights('view_visit_reports')
def pages_report_csv():
    rows = [(path, visits_count) for path, visits_count in page_report_rows()]
    return csv_response('pages_report.csv', ['Страница', 'Количество посещений'], rows)


@reports_bp.route('/users')
@check_rights('view_visit_reports')
def users_report():
    return render_template(
        'reports/users_report.html',
        title='Отчёт по пользователям',
        rows=user_report_rows()
    )


@reports_bp.route('/users/export.csv')
@check_rights('view_visit_reports')
def users_report_csv():
    return csv_response('users_report.csv', ['Пользователь', 'Количество посещений'], user_report_rows())
