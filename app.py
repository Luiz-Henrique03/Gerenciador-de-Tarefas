from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ctm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)


class User(db.Model):
    """User schema"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Projects(db.Model):
    """Projects schema"""
    project_id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(20))
    active = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  

    def __init__(self, project, user_id, active=False):
        self.project_name = project
        self.user_id = user_id
        self.active = active

    def __repr__(self):
        return '<Project {}>'.format(self.project_name)



class Tasks(db.Model):
    """Tasks schema"""
    task_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  
    title = db.Column(db.String(100), nullable=False)  
    description = db.Column(db.Text)  
    status = db.Column(db.String(20), default='Pending')  

    project = relationship('Projects', backref='tasks')
    user = relationship('User')

    def __init__(self, project_id, title, description, user_id, status='Pending'):
        self.project_id = project_id
        self.title = title
        self.description = description
        self.user_id = user_id
        self.status = status

    def __repr__(self):
        return '<Task {}>'.format(self.title)


with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Login successful!')
            return redirect(url_for('task'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']


        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            error_message = 'O usuário já existe.'
            return render_template('register.html', error=error_message)
        
        new_user = User(username, password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout and redirect to login page"""
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))
    

@app.route('/task', methods=['GET', 'POST'])
def task():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        status = request.form['status']
        project_name = request.form['project']
        user_id = request.form['user_id']

        project = Projects.query.filter_by(project_name=project_name, user_id=session['user_id']).first()
        if not project:
            project = Projects(project_name=project_name, user_id=session['user_id'])
            db.session.add(project)
            db.session.commit()

        task = Tasks(project_id=project.project_id, title=title, description=description, user_id=user_id, status=status)
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!')
        return redirect(url_for('task'))

    status_filter = request.args.get('status')
    project_id_filter = request.args.get('project_id')

    if project_id_filter:
        tasks = Tasks.query.filter_by(project_id=project_id_filter).all()
    else:
        if status_filter:
            tasks = Tasks.query.filter_by(status=status_filter).all()
        else:
            tasks = Tasks.query.all()

    projects = Projects.query.all()
    users = User.query.all()

    return render_template('task.html', tasks=tasks, projects=projects, users=users)


@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    """Delete a project and its tasks"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    project = Projects.query.filter_by(project_id=project_id, user_id=session['user_id']).first()
    if not project:
        return redirect(url_for('task'))

    Tasks.query.filter_by(project_id=project_id).delete()
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/select_project', methods=['POST'])
def select_project():
    """Selects an active project"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    project_id = request.form.get('selected_project')
    if project_id:
        Projects.query.filter_by(user_id=session['user_id']).update({Projects.active: False})
        active_project = Projects.query.get(project_id)
        if active_project:
            active_project.active = True
            db.session.commit()

    return redirect(url_for('task'))


@app.route('/add', methods=['POST'])
def add_task():
    """Adds a new task"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    project_name = request.form['project']
    status = request.form['status']
    user_id = request.form['user_id'] 

    if not title or not description:
        flash('Title and description are required!')
        return redirect(url_for('task'))

    if not project_name:
        flash('You must provide a project name!')
        return redirect(url_for('task'))

    project_obj = Projects.query.filter_by(project_name=project_name).first()
    if not project_obj:
        project_obj = Projects(project_name, session['user_id'], True)
        db.session.add(project_obj)
        db.session.commit()

    project_id = project_obj.project_id

    Projects.query.filter_by(user_id=session['user_id']).update({Projects.active: False})
    project_obj.active = True
    db.session.commit()

    new_task = Tasks(project_id, title, description, user_id, status)
    db.session.add(new_task)
    db.session.commit()

    flash('Task added successfully!')
    return redirect(url_for('task'))


@app.route('/close/<int:task_id>')
def close_task(task_id):
    """Closes a task"""
    task = Tasks.query.get(task_id)

    if not task:
        return redirect(url_for('task'))

    task.status = 'Completed' if task.status != 'Completed' else 'Pending'
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    """Deletes a task"""
    task = Tasks.query.get(task_id)

    if not task:
        return redirect(url_for('task'))

    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/clear/<int:project_id>')
def clear_all(project_id):
    """Removes all tasks from a project and deletes the project"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    Tasks.query.filter_by(project_id=project_id).delete()
    Projects.query.filter_by(project_id=project_id, user_id=session['user_id']).delete()
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/remove/<int:project_id>')
def remove_all(project_id):
    """Removes all tasks from a project"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    Tasks.query.filter_by(project_id=project_id).delete()
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/edit_task', methods=['POST'])
def edit_task():
    """Edits the task description"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task_id = request.form['task_id']
    title = request.form['title']
    description = request.form['description']

    task = Tasks.query.get(task_id)
    if not task:
        flash('Task not found.')
        return redirect(url_for('task'))
    

    task.title = title
    task.description = description
    db.session.commit()
    flash('Task updated successfully!')
    return redirect(url_for('task'))



@app.route('/view_projects')
def view_projects():
    """Lists all projects for the user"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    projects = Projects.query.all()
    
    return render_template('view_projects.html', projects=projects)


@app.route('/view_tasks')
def view_tasks():
    """Lists all tasks for the user"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    tasks = Tasks.query.all()

    return render_template('view_tasks.html', tasks=tasks)


@app.route('/view_users')
def view_users():
    """Lists all users"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('view_users.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)