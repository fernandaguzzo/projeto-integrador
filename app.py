from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biblioteca.db'
app.config['SECRET_KEY'] = 'segredo123'
app.config['UPLOAD_FOLDER'] = 'static/capas'
db = SQLAlchemy(app)

# Modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'admin' ou 'usuario'

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    capa = db.Column(db.String(100))
    disponivel = db.Column(db.Boolean, default=True)

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    data_emprestimo = db.Column(db.DateTime, default=datetime.now)
    data_devolucao = db.Column(db.DateTime)
    livro = db.relationship('Livro', backref='emprestimos')
    usuario = db.relationship('Usuario', backref='emprestimos')

# Decorador para login requerido
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login primeiro', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])  # ← Note o nome 'login' aqui
def login():  # ← E aqui
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_type'] = user.tipo
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))  # ← Verifique também este nome
        else:
            flash('Usuário ou senha incorretos', 'danger')
    return render_template('login.html')  # ← E este template existe

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session['user_type'] == 'admin':
        return admin()
    return user()

# Área do administrador
@app.route('/admin')
@login_required
def admin():
    if session['user_type'] != 'admin':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('dashboard'))
    
    livros = Livro.query.all()
    emprestimos = Emprestimo.query.filter_by(data_devolucao=None).all()
    return render_template('admin.html', livros=livros, emprestimos=emprestimos)

@app.route('/adicionar-livro', methods=['GET', 'POST'])
@login_required
def adicionar_livro():
    if session['user_type'] != 'admin':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        
        # Upload da capa
        capa = None
        if 'capa' in request.files:
            arquivo = request.files['capa']
            if arquivo.filename != '':
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                filename = secure_filename(arquivo.filename)
                arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                capa = filename
        
        novo_livro = Livro(titulo=titulo, autor=autor, capa=capa)
        db.session.add(novo_livro)
        db.session.commit()
        flash('Livro adicionado com sucesso!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('adicionar_livro.html')

@app.route('/user')
@login_required
def user():
    livros = Livro.query.filter_by(disponivel=True).all()
    meus_emprestimos = Emprestimo.query.filter_by(
        usuario_id=session['user_id']
    ).filter(Emprestimo.data_devolucao == None).all()
    
    # Adiciona datetime.now ao contexto do template
    return render_template('user.html', 
                         livros=livros, 
                         emprestimos=meus_emprestimos,
                         datetime=datetime)

@app.route('/emprestar/<int:livro_id>')
@login_required
def emprestar(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    
    if not livro.disponivel:
        flash('Livro não disponível', 'danger')
        return redirect(url_for('user'))
    
    # Calcula data de devolução (7 dias depois)
    data_devolucao = datetime.now() + timedelta(days=7)
    
    novo_emprestimo = Emprestimo(
        livro_id=livro.id,
        usuario_id=session['user_id'],
        data_devolucao=data_devolucao
    )
    
    livro.disponivel = False
    db.session.add(novo_emprestimo)
    db.session.commit()
    
    flash(f'Livro emprestado! Devolva até {data_devolucao.strftime("%d/%m/%Y")}', 'success')
    return redirect(url_for('user'))

@app.route('/devolver/<int:emprestimo_id>')
@login_required
def devolver(emprestimo_id):
    emprestimo = Emprestimo.query.get_or_404(emprestimo_id)
    
    if emprestimo.usuario_id != session['user_id']:
        flash('Ação não permitida', 'danger')
        return redirect(url_for('user'))
    
    emprestimo.livro.disponivel = True
    emprestimo.data_devolucao = datetime.now()
    db.session.commit()
    
    flash('Livro devolvido com sucesso!', 'success')
    return redirect(url_for('user'))

# Inicialização
def criar_admin():
    if not Usuario.query.filter_by(username='admin').first():
        senha_hash = generate_password_hash('admin123')
        admin = Usuario(username='admin', password=senha_hash, tipo='admin')
        db.session.add(admin)
        db.session.commit()

with app.test_request_context():
    print(url_for('login'))  

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        criar_admin()
    app.run(debug=True)