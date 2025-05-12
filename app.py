from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
db = SQLAlchemy(app)

# Modelos do Banco de Dados
class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    disponivel = db.Column(db.Boolean, default=True)
    
class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'), nullable=False)
    data_emprestimo = db.Column(db.DateTime, default=datetime.utcnow)
    data_devolucao = db.Column(db.DateTime)
    usuario = db.Column(db.String(100), nullable=False)
    devolvido = db.Column(db.Boolean, default=False)
    livro = db.relationship('Livro', backref=db.backref('emprestimos', lazy=True))

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        titulo = request.form['titulo']
        autor = request.form['autor']
        isbn = request.form['isbn']
        
        novo_livro = Livro(titulo=titulo, autor=autor, isbn=isbn)
        db.session.add(novo_livro)
        db.session.commit()
        flash('Livro adicionado com sucesso!', 'success')
        return redirect(url_for('admin'))
    
    livros = Livro.query.all()
    return render_template('admin.html', livros=livros)

@app.route('/user')
def user():
    livros = Livro.query.filter_by(disponivel=True).all()
    return render_template('user.html', livros=livros)

@app.route('/emprestar', methods=['POST'])
def emprestar():
    data = request.get_json()
    livro_id = data['livro_id']
    usuario = data['usuario']
    
    livro = Livro.query.get(livro_id)
    if livro and livro.disponivel:
        livro.disponivel = False
        data_devolucao = datetime.utcnow() + timedelta(days=14)
        novo_emprestimo = Emprestimo(
            livro_id=livro_id,
            usuario=usuario,
            data_devolucao=data_devolucao
        )
        db.session.add(novo_emprestimo)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/devolver/<int:livro_id>')
def devolver(livro_id):
    livro = Livro.query.get(livro_id)
    if livro:
        livro.disponivel = True
        emprestimo = Emprestimo.query.filter_by(livro_id=livro_id, devolvido=False).first()
        if emprestimo:
            emprestimo.devolvido = True
            emprestimo.data_devolucao = datetime.utcnow()
        db.session.commit()
        flash('Livro devolvido com sucesso!', 'success')
    return redirect(url_for('admin'))

@app.route('/livros')
def livros():
    livros = Livro.query.all()
    return render_template('livros.html', livros=livros)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)