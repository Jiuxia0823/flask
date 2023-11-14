import os
import sys
import click

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()
from flask_migrate import Migrate, upgrade
from app import create_app, db
from app.models import User, Role, Follow, Post, Permission, Comment

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment)

@app.cli.command()
@click.option('--coverage/--no-coverage', default=False,
              help='在代码覆盖范围内运行测试.')
@click.argument('test_names', nargs=-1)
def test(coverage, test_names):
    """运行单元测试."""
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)
    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('报道总结:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

@app.cli.command()
@click.option('--length', default=25,
              help='要包含在分析器报告中的函数数量。')
@click.option('--profile-dir', default=None,
              help='分析器数据文件保存的目录.')
def profile(length, profile_dir):
    """在代码分析器下启动应用程序。"""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run(debug=False)

@app.cli.command
def deploy():
    """运行部署任务."""
    # 把数据库迁移到最新修订版本
    upgrade()
    # 创建或更新用户角色
    Role.insert_roles()
    # 确保所有用户都关注了他们自己
    User.add_self_follows()