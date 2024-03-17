from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# Função para conectar ao banco de dados
def conectar_bd():
    conn = sqlite3.connect('biblioteca.db')
    conn.row_factory = sqlite3.Row
    return conn

# Verifica e cria a tabela 'emprestimos' se ela não existir
def verificar_tabela_emprestimos():
    conn = conectar_bd()
    conn.execute('''CREATE TABLE IF NOT EXISTS emprestimos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    livro_id INTEGER NOT NULL,
                    aluno TEXT NOT NULL,
                    horario_emprestimo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Adicionando a coluna horario_emprestimo
                    FOREIGN KEY(livro_id) REFERENCES livros(id)
                )''')
    conn.commit()
    conn.close()

# Chama a função para verificar a tabela de empréstimos
verificar_tabela_emprestimos()

# Rota para a página inicial
@app.route('/')
def index():
    conn = conectar_bd()
    cursor = conn.execute('SELECT * FROM livros ORDER BY titulo, autor')  # Ordenar por título e autor para agrupar os livros
    livros = cursor.fetchall()
    conn.close()
    return render_template('index.html', livros=livros)

# Rota para adicionar um novo livro
@app.route('/adicionar_livro', methods=['POST'])
def adicionar_livro():
    data = request.form
    titulo = data["titulo"]
    autor = data["autor"]
    exemplares = int(data["exemplares"])

    conn = conectar_bd()
    conn.execute('INSERT INTO livros (titulo, autor, exemplares_disponiveis, emprestado) VALUES (?, ?, ?, ?)', (titulo, autor, exemplares, False))  # Adicionando a coluna "emprestado" com valor padrão False
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Livro adicionado com sucesso"})

# Rota para remover um livro
@app.route('/remover_livro', methods=['POST'])
def remover_livro():
    livro_id = int(request.form["id"])

    conn = conectar_bd()
    conn.execute('DELETE FROM livros WHERE id = ?', (livro_id,))
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Livro removido com sucesso"})

# Rota para emprestar um livro
@app.route('/emprestar_livro', methods=['POST'])
def emprestar_livro():
    data = request.form
    pesquisa = data["pesquisa"]
    quantidade = int(data["quantidade"])
    aluno = data["aluno"]

    # Realizar a busca por título ou autor no banco de dados
    conn = conectar_bd()
    cursor = conn.execute('SELECT * FROM livros WHERE titulo LIKE ? OR autor LIKE ?', ('%' + pesquisa + '%', '%' + pesquisa + '%'))
    livros_encontrados = cursor.fetchall()

    # Verificar se foram encontrados livros correspondentes à pesquisa
    if not livros_encontrados:
        conn.close()
        return jsonify({"erro": "Nenhum livro encontrado"}), 404

    # Verificar se há exemplares disponíveis para empréstimo
    for livro in livros_encontrados:
        exemplares_disponiveis = livro["exemplares_disponiveis"]
        if exemplares_disponiveis < quantidade:
            conn.close()
            return jsonify({"erro": f"Exemplares insuficientes disponíveis para empréstimo do livro {livro['titulo']}, por favor, selecione uma quantidade menor"}), 400

        # Atualizar a quantidade de exemplares disponíveis após o empréstimo
        exemplares_restantes = exemplares_disponiveis - quantidade
        conn.execute('UPDATE livros SET exemplares_disponiveis = ? WHERE id = ?', (exemplares_restantes, livro["id"]))

        # Registra o empréstimo na tabela de empréstimos
        for _ in range(quantidade):
            conn.execute('INSERT INTO emprestimos (livro_id, aluno) VALUES (?, ?)', (livro["id"], aluno))

    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Livro(s) emprestado(s) com sucesso"})

# Rota para alterar o status de empréstimo de um livro
@app.route('/alterar_status_emprestimo', methods=['POST'])
def alterar_status_emprestimo():
    data = request.form
    livro_id = int(data["id"])
    emprestado = bool(data["emprestado"])

    conn = conectar_bd()
    conn.execute('UPDATE livros SET emprestado = ? WHERE id = ?', (emprestado, livro_id))  # Atualizar o estado de empréstimo do livro
    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Status de empréstimo atualizado com sucesso"})

# Rota para obter os livros emprestados
@app.route('/livros_emprestados_json')
def livros_emprestados_json():
    conn = conectar_bd()
    cursor = conn.execute('SELECT livros.titulo, livros.autor, emprestimos.aluno, emprestimos.horario_emprestimo, COUNT(*) as quantidade FROM emprestimos INNER JOIN livros ON emprestimos.livro_id = livros.id GROUP BY livro_id, aluno, horario_emprestimo ORDER BY emprestimos.horario_emprestimo')
    emprestimos = cursor.fetchall()
    conn.close()

    # Formatar os resultados como lista de dicionários
    livros_emprestados = []
    for emprestimo in emprestimos:
        livro_emprestado = {
            'titulo': emprestimo['titulo'],
            'autor': emprestimo['autor'],
            'aluno': emprestimo['aluno'],
            'horario_emprestimo': emprestimo['horario_emprestimo'],
            'quantidade': emprestimo['quantidade']
        }
        livros_emprestados.append(livro_emprestado)

    return jsonify(livros_emprestados)

    conn = conectar_bd()
    cursor = conn.execute('SELECT livros.titulo, livros.autor, emprestimos.aluno, emprestimos.horario_emprestimo, COUNT(*) as quantidade FROM emprestimos INNER JOIN livros ON emprestimos.livro_id = livros.id GROUP BY livro_id, aluno, horario_emprestimo ORDER BY emprestimos.horario_emprestimo')
    emprestimos = cursor.fetchall()
    conn.close()

    # Formatar os resultados como lista de dicionários
    livros_emprestados = []
    for emprestimo in emprestimos:
        livro_emprestado = {
            'titulo': emprestimo['titulo'],
            'autor': emprestimo['autor'],
            'aluno': emprestimo['aluno'],
            'horario_emprestimo': emprestimo['horario_emprestimo'],
            'quantidade': emprestimo['quantidade']
        }
        livros_emprestados.append(livro_emprestado)

    return jsonify(livros_emprestados)

# Rota para devolver um livro
@app.route('/devolver_livro', methods=['POST'])
def devolver_livro():
    titulo = request.form["titulo"]
    aluno = request.form["aluno"]

    # Realizar a busca pelo título do livro no banco de dados
    conn = conectar_bd()
    cursor = conn.execute('SELECT * FROM livros WHERE titulo = ?', (titulo,))
    livro = cursor.fetchone()

    if not livro:
        conn.close()
        return jsonify({"erro": "Livro não encontrado"}), 404

    # Realizar a busca pelo livro emprestado pelo aluno
    cursor = conn.execute('SELECT * FROM emprestimos WHERE livro_id = ? AND aluno = ?', (livro["id"], aluno))
    emprestimo = cursor.fetchone()

    if not emprestimo:
        conn.close()
        return jsonify({"erro": "Livro não emprestado para esse aluno"}), 404

    # Atualizar a quantidade de exemplares disponíveis após a devolução
    exemplares_disponiveis = livro["exemplares_disponiveis"] + 1
    conn.execute('UPDATE livros SET exemplares_disponiveis = ? WHERE id = ?', (exemplares_disponiveis, livro["id"]))

    # Remover a entrada de empréstimo correspondente à devolução
    conn.execute('DELETE FROM emprestimos WHERE id = ?', (emprestimo["id"],))

    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Livro devolvido com sucesso"})

# Rota para devolver todos os exemplares de um livro
@app.route('/devolver_todos', methods=['POST'])
def devolver_todos():
    titulo = request.form["titulo"]
    aluno = request.form["aluno"]

    # Realizar a busca pelo título do livro no banco de dados
    conn = conectar_bd()
    cursor = conn.execute('SELECT * FROM livros WHERE titulo = ?', (titulo,))
    livro = cursor.fetchone()

    if not livro:
        conn.close()
        return jsonify({"erro": "Livro não encontrado"}), 404

    # Realizar a busca pelos exemplares do livro emprestados pelo aluno
    cursor = conn.execute('SELECT * FROM emprestimos WHERE livro_id = ? AND aluno = ?', (livro["id"], aluno))
    emprestimos = cursor.fetchall()

    if not emprestimos:
        conn.close()
        return jsonify({"erro": "Livro não emprestado para esse aluno"}), 404

    # Atualizar a quantidade de exemplares disponíveis após a devolução
    exemplares_disponiveis = livro["exemplares_disponiveis"] + len(emprestimos)
    conn.execute('UPDATE livros SET exemplares_disponiveis = ? WHERE id = ?', (exemplares_disponiveis, livro["id"]))

    # Remover as entradas de empréstimo correspondentes à devolução de todos os exemplares
    for emprestimo in emprestimos:
        conn.execute('DELETE FROM emprestimos WHERE id = ?', (emprestimo["id"],))

    conn.commit()
    conn.close()

    return jsonify({"mensagem": "Todos os exemplares do livro devolvidos com sucesso"})

if __name__ == '__main__':
    app.run(debug=True)
