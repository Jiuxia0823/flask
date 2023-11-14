from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from ..email import send_email
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm

# 处理程序过滤未确认的账户
@auth.before_app_request
def before_request():
    # 满足用户已登录
    if current_user.is_authenticated:
        # 更新已登录用户的最后访问时间
        current_user.ping()
        # 用户还未创建、请求的URL不在身份验证蓝本中
        # 不是对静态文件的请求
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))
# 用户确认后重定向到主页
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')
# 登陆
@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or not next.startswith('/'):
                next = url_for('main.index')
            return redirect(next)
        flash('无效的邮箱或密码')
    return render_template('auth/login.html', form=form)
# 退出用户
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已注销')
    return redirect(url_for('main.index'))
# 渲染注册用户页面
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(),
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, '确认账户',
                   'auth/email/confirm', user=user, token=token)
        flash('确认邮件已通过电子邮件发送给您')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)
# 确认账户
@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('您已经确认了您的账户。谢谢!')
    else:
        flash('确认链接无效或已过期。')
    return redirect(url_for('main.index'))
# 确认邮件
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, '确认您的帐户',
               'auth/email/confirm', user=current_user, token=token)
    flash('新的确认邮件已通过电子邮件发送给您.')
    return redirect(url_for('main.index'))
# 渲染修改密码页面
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('您的密码已更新')
            return redirect(url_for('main.index'))
        else:
            flash('无效的密码')
    return render_template("auth/change_password.html", form=form)
# 渲染重置密码页面
@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token)
        flash('已向您发送了一封重置密码的电子邮件')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
# 渲染验证验证邮件链接
@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('您的密码已更新')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)
# 渲染修改邮箱表单
@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, '确认您的电子邮件地址',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('我们已经给您发了一封邮件，告诉您确认了您的新邮箱地址。')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)
# 渲染修改邮箱后
@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('您的邮箱地址已经更新了')
    else:
        flash('无效的请求')
    return redirect(url_for('main.index'))