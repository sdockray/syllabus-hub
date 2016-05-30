# -*- coding: utf-8 -*-
import os
import unicodedata

from flask import Flask, render_template, url_for, request, redirect, flash, g
from flaskext.markdown import Markdown
from flask.ext.login import login_user, logout_user, current_user, login_required, LoginManager, UserMixin
from flask_wtf import Form
from wtforms import StringField, PasswordField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp
import gitlab
import markdown2

# set up and config
app = Flask(__name__)
app.config.from_pyfile('../app.conf', silent=True)
app.config.from_envvar('SYLLABUS_APP_SETTINGS', silent=True)
app.secret_key = app.config['SECRET_KEY']
# initialize extensions
Markdown(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Allows templates access to current user through g.user
@app.before_request
def before_request():
    g.user = current_user


# utility for encoding problems
def dcode(s):
    return unicodedata.normalize('NFKD', s.decode("utf-8")).encode('ascii', 'ignore')

# Flashes form errors
def flash_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (
                getattr(form, field).label.text,
                error
            ))

"""
Forms
"""
class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(Form):
    name = StringField('Display Name', [Length(min=4, max=25)])
    username = StringField('Unique Username', 
        [Length(min=4, max=25),
        Regexp(r'^[\w]+$')
    ])
    email = StringField('Email Address', [Length(min=6, max=50)])
    password = PasswordField('Password', [
        DataRequired(),
        EqualTo('confirm', message='Passwords must match'),
        Length(min=8)
    ])
    confirm = PasswordField('Repeat Password')

class EditForm(Form):
    content = StringField(u'Text', widget=TextArea())

class CreateForm(Form):
    title = StringField('Title', [Length(min=3)])
    content = StringField(u'Text', widget=TextArea())


"""
Non-project Gitlab API interaction
"""
class Git(object):
    def __init__(self, *args, **kwargs):
        if 'token' in kwargs and kwargs['token']:
            self.gl = gitlab.Gitlab(app.config['GIT_SERVER'], token=kwargs['token'])
        elif 'user' in kwargs and kwargs['user'] and kwargs['user'].is_authenticated:
            self.gl = gitlab.Gitlab(app.config['GIT_SERVER'], token=kwargs['user'].id)
        else:
            self.gl = gitlab.Gitlab(app.config['GIT_SERVER'], token=app.config['GIT_PRIVATE_TOKEN'])            

    def user_login(self, email, password):
        try:
            self.gl.login(email, password)
            return self.gl.currentuser()
        except:
            return False

    def user_create(self, name, username, email, password):
        print name, username, password, email
        try:
            return self.gl.createuser(name, username, password, email)
        except:
            return False

    def current_user(self):
        u = self.gl.currentuser()
        if not u or not 'private_token' in u:
            return False
        return u

    def user_projects(self):
        u = self.gl.currentuser()
        print u
        return [p for p in self.gl.getall(self.gl.getprojectsowned)]

    def all_projects(self, ignore_forks=False):
        if ignore_forks:
            return [p for p in self.gl.getall(self.gl.getprojectsall) if 'forked_from_project' not in p]
        else:
            return [p for p in self.gl.getall(self.gl.getprojectsall)]

    def create_project_with_content(self, title, content):
        new_p = self.gl.createproject(title, description=title, public=True)
        if new_p:
            self.gl.createfile(new_p['id'], 'README.md', 'master', content, 'creating syllabus')
        return new_p

"""
Interfaces with Gitlab API for a project
"""
class Project(Git):
    def __init__(self, project_id, user=False):
        if user and user.is_authenticated:
            super(Project, self).__init__(token=user.id)
        else:
            super(Project, self).__init__()
        self.project = self.gl.getproject(project_id)

    def get_content(self, file_name='README.md', branch='master'):
        return self.gl.getrawfile(self.project['id'], branch, file_name)

    def get_title(self):
        return self.project['name_with_namespace']

    def get_forks_count(self):
        return self.project['forks_count']

    def update(self, content, file_name='README.md', branch='master'):
        self.gl.updatefile(self.project['id'], file_name, branch, content, 'saved via web')

    def fork(self):
        if 'id' in self.project:
            # I have to do direct curl because the API call seems buggy
            cmd = 'curl -X POST -H "PRIVATE-TOKEN: %s" "%s/api/v3/projects/fork/%s"' % (self.current_user()['private_token'], app.config['GIT_SERVER'], self.project['id'])
            os.system(cmd)
            return True # just assume
            #return self.gl.createfork(self.project['id'])
        return False

    def can_edit(self):
        u = self.current_user()
        if not u or not 'username' in u or not 'owner' in self.project:
            return False
        if u['username']==self.project['owner']['username']:
            return True
        else:
            return False

    def can_fork(self):
        u = self.current_user()
        if not u or not 'username' in u or not 'owner' in self.project:
            return False
        if self.can_edit():
            return False
        import pprint
        for p in self.gl.getall(self.gl.getprojectsowned):
            if 'forked_from_project' in p and p['forked_from_project']['id']==self.project['id']:
                return False                
        return True


"""
User/ login manager stuff
"""
class User(UserMixin):
    def __init__(self, *args, **kwargs):
        super(User, self).__init__()
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])
        self.user_id = self.id
        self.id = self.private_token

@login_manager.user_loader
def user_loader(id):
    git = Git(token=id)
    u = git.current_user()
    if not u:
        return User()
    user = User(**u)
    return user


"""
ROUTING
"""

@app.route('/')
def projects_list():
    git = Git()
    return render_template('projects.html',
        title = 'syll...',
        projects = git.all_projects()
    )

@app.route('/home')
@login_required
def projects_user():
    git = Git(token=current_user.id)
    return render_template('projects.html',
        title = '%s /' % current_user.name,
        projects = git.user_projects()
    )


@app.route('/<namespace>/<project_name>')
def view_project(namespace, project_name):
    p = Project("%s/%s" % (namespace, project_name), user=current_user)
    return render_template('view.html',
        title = p.get_title(),
        project = p.project,
        content = dcode(p.get_content()),
        edit_url = url_for('edit_project', namespace=namespace, project_name=project_name) if p.can_edit() else False,
        fork_url = url_for('fork_project', namespace=namespace, project_name=project_name) if p.can_fork() else False
    )

@app.route('/<namespace>/<project_name>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(namespace, project_name):
    p = Project("%s/%s" % (namespace, project_name), user=current_user)
    if not p.can_edit():
        return "Something went wrong. You can't edit this syllabus."
    if 'content' in request.form:
        p.update(request.form['content'])
        return redirect(url_for('view_project',  namespace=namespace, project_name=project_name))
    return render_template('edit.html',
        title = p.get_title(),
        save_url = url_for('edit_project', namespace=namespace, project_name=project_name),
        form = EditForm(content=dcode(p.get_content())))

@app.route('/make', methods=['GET', 'POST'])
@login_required
def create_project():
    if 'content' in request.form:
        # create project
        git = Git(token=current_user.id)
        new_p = git.create_project_with_content(request.form['title'], request.form['content'])
        if new_p:
            path = new_p['path_with_namespace'].split('/')
            return redirect(url_for('view_project', namespace=path[0], project_name=path[1]))
        else:
            flash('Sorry but something went wrong and the syllabus could not be saved.')
        return redirect(url_for('create_project'))
    return render_template('create.html',
        title = 'New syllabus',
        save_url = url_for('create_project'),
        form = CreateForm())

@app.route('/<namespace>/<project_name>/clone', methods=['GET', 'POST'])
@login_required
def fork_project(namespace, project_name):
    p = Project("%s/%s" % (namespace, project_name), user=current_user)
    if not p.can_fork():
        return "Something went wrong. You can't clone this syllabus."
    if request.method == 'POST':
        new_p = p.fork()
        if new_p:
            return redirect(url_for('projects_user'))
    return render_template('fork.html',
        title = p.get_title(),
        project_name = project_name,
        url = url_for('view_project', namespace=namespace, project_name=project_name),
        fork_url = url_for('fork_project', namespace=namespace, project_name=project_name)
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        git = Git()
        u = git.user_login(request.form['email'], request.form['password'])
        if u:
            user = User(**u)
            login_user(user)
            return redirect(request.args.get('next') or url_for('projects_user'))
    return render_template('login.html', 
        title = 'Login',
        form = form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        git = Git()
        success = git.user_create(request.form['name'], request.form['username'], request.form['email'], request.form['password'])
        if success:
            u = git.user_login(request.form['email'], request.form['password'])
            if u:
                user = User(**u)
                login_user(user)
                return redirect(request.args.get('next') or url_for('projects_user'))
        else:
            flash("The account couldn't be created. It might be because the email or username are already being used.")
    else:
        flash_errors(form)
    return render_template('register.html', 
        title = 'Register',
        form = form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'Logged out'




if __name__ == '__main__':
    app.debug = True
    app.run()
    