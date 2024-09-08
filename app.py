from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Substitua pela sua chave secreta
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Associando o projeto ao usuário

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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Relaciona a tarefa com o usuário logado
    title = db.Column(db.String(100), nullable=False)  # Novo campo para o título
    description = db.Column(db.Text)  # Novo campo para a descrição
    status = db.Column(db.String(20), default='Pendente')  # Status atualizado com "Pendente" como valor padrão

    # Relacionamentos
    project = relationship('Projects', backref='tasks')
    user = relationship('User')

    def __init__(self, project_id, title, description, user_id, status='Pendente'):
        self.project_id = project_id
        self.title = title
        self.description = description
        self.user_id = user_id
        self.status = status

    def __repr__(self):
        return '<Task {}>'.format(self.title)




# Inicializa o banco de dados
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
    """Página de registro de usuário"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

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
        # Adicionar nova tarefa
        title = request.form['title']
        description = request.form['description']
        status = request.form['status']
        project_name = request.form['project']
        user_id = request.form['user_id']

        # Buscar ou criar projeto
        project = Projects.query.filter_by(project_name=project_name, user_id=session['user_id']).first()
        if not project:
            project = Projects(project_name=project_name, user_id=session['user_id'])
            db.session.add(project)
            db.session.commit()

        # Adicionar tarefa
        task = Tasks(project_id=project.project_id, title=title, description=description, user_id=user_id, status=status)
        db.session.add(task)
        db.session.commit()
        flash('Tarefa adicionada com sucesso!')
        return redirect(url_for('task'))

    status_filter = request.args.get('status')
    project_id_filter = request.args.get('project_id')

    if project_id_filter:
        # Buscar tarefas pelo ID do projeto
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
    """Seleciona um projeto ativo"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    project_id = request.form.get('selected_project')
    if project_id:
        # Atualiza o projeto ativo
        Projects.query.filter_by(user_id=session['user_id']).update({Projects.active: False})
        active_project = Projects.query.get(project_id)
        if active_project:
            active_project.active = True
            db.session.commit()

    return redirect(url_for('task'))



@app.route('/add', methods=['POST'])
def add_task():
    """Adiciona uma nova tarefa"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    title = request.form['title']
    description = request.form['description']
    project_name = request.form['project']
    status = request.form['status']
    user_id = request.form['user_id']  # Obtém o ID do usuário do formulário

    if not title or not description:
        flash('Título e descrição são obrigatórios!')
        return redirect(url_for('task'))

    if not project_name:
        flash('Você deve fornecer um nome de projeto!')
        return redirect(url_for('task'))

    # Verifica se o projeto já existe
    project_obj = Projects.query.filter_by(project_name=project_name).first()
    if not project_obj:
        # Se o projeto não existir, cria um novo projeto
        project_obj = Projects(project_name, session['user_id'], True)
        db.session.add(project_obj)
        db.session.commit()

    project_id = project_obj.project_id

    # Atualiza o status dos projetos ativos
    Projects.query.filter_by(user_id=session['user_id']).update({Projects.active: False})
    project_obj.active = True
    db.session.commit()

    # Cria e adiciona a nova tarefa
    new_task = Tasks(project_id, title, description, user_id, status)
    db.session.add(new_task)
    db.session.commit()

    flash('Tarefa adicionada com sucesso!')
    return redirect(url_for('task'))



@app.route('/close/<int:task_id>')
def close_task(task_id):
    """Fecha uma tarefa"""
    task = Tasks.query.get(task_id)

    if not task:
        return redirect(url_for('task'))

    task.status = 'Concluída' if task.status != 'Concluída' else 'Pendente'
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    """Exclui uma tarefa"""
    task = Tasks.query.get(task_id)

    if not task:
        return redirect(url_for('task'))

    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/clear/<int:project_id>')
def clear_all(project_id):
    """Remove todas as tarefas de um projeto e exclui o projeto"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    Tasks.query.filter_by(project_id=project_id).delete()
    Projects.query.filter_by(project_id=project_id, user_id=session['user_id']).delete()
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/remove/<int:project_id>')
def remove_all(project_id):
    """Remove todas as tarefas de um projeto"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    Tasks.query.filter_by(project_id=project_id).delete()
    db.session.commit()
    return redirect(url_for('task'))

@app.route('/edit_task', methods=['POST'])
def edit_task():
    """Edita a descrição da tarefa"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task_id = request.form['task_id']
    title = request.form['title']
    description = request.form['description']

    task = Tasks.query.get(task_id)
    if not task or task.user_id != session['user_id']:
        flash('Tarefa não encontrada ou você não tem permissão para editá-la.')
        return redirect(url_for('task'))

    task.title = title
    task.description = description
    db.session.commit()
    flash('Tarefa atualizada com sucesso!')
    return redirect(url_for('task'))


if __name__ == '__main__':
    app.run(debug=True)
